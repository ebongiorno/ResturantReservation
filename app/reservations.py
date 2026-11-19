
import re
from datetime import date

from mysql.connector import Error, IntegrityError, errorcode
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from .db import get_db

# Blueprint for reservation-related endpoints
reservations_bp = Blueprint(
    "reservations",
    __name__,
    url_prefix="/api/v1/reservations"
)

# Consistent JSON error responses
def error(message, status):
    return jsonify({
        "error": {
            "code": {
                400: "invalid_input",
                401: "unauthorized",
                403: "forbidden",
                404: "not_found",
                409: "conflict",
                500: "database_error"
            }[status],
            "message": message
        }
    }), status

def valid_positive_integer(value):
    return type(value) is int and value > 0


# GET /api/v1/reservations
@reservations_bp.get("")
@jwt_required()
def get_reservations():

    user_id = int(get_jwt_identity())

    # Check pagination parameters
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 10))
    except (ValueError, TypeError):
        return error("Invalid pagination parameters", 400)

    if page < 1 or not 1 <= per_page <= 100:
        return error("Invalid pagination parameters", 400)

    offset = (page - 1) * per_page

    conn = None
    cursor = None

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # 1. Find the logged-in user's role
        cursor.execute(
            "SELECT role FROM users WHERE id = %s",
            (user_id,)
        )
        user = cursor.fetchone()

        if user is None:
            return error("User not found", 401)

        # 2. Staff can see all reservations
        if user["role"] == "staff":
            cursor.execute(
                """
                SELECT id, user_id, table_id, slot_id,
                       reservation_date, party_size, status
                FROM reservations
                ORDER BY reservation_date DESC, id DESC
                LIMIT %s OFFSET %s
                """,
                (per_page, offset)
            )

        # 3. Customers can only see their own
        else:
            cursor.execute(
                """
                SELECT id, user_id, table_id, slot_id,
                       reservation_date, party_size, status
                FROM reservations
                WHERE user_id = %s
                ORDER BY reservation_date DESC, id DESC
                LIMIT %s OFFSET %s
                """,
                (user_id, per_page, offset)
            )

        reservations = cursor.fetchall()

        # 4. Format dates as YYYY-MM-DD
        for reservation in reservations:
            reservation["reservation_date"] = (
                reservation["reservation_date"].isoformat()
            )

        return jsonify({
            "reservations": reservations,
            "page": page,
            "per_page": per_page
        }), 200

    except Error:
        current_app.logger.exception("Error retrieving reservations")
        return error("Database error", 500)

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

# POST /api/v1/reservations
@reservations_bp.post("")
@jwt_required()
def create_reservation():

    # 1. Check the request data
    data = request.get_json(silent=True)
    required = ["table_id", "slot_id", "reservation_date", "party_size"]

    if not isinstance(data, dict) or any(k not in data for k in required):
        return error("Missing or invalid JSON fields", 400)

    for field in ["table_id", "slot_id", "party_size"]:
        if type(data[field]) is not int or data[field] <= 0:
            return error(f"Invalid {field}", 400)

    try:
        booking_date = date.fromisoformat(data["reservation_date"])
        if booking_date.isoformat() != data["reservation_date"]:
            return error("Use YYYY-MM-DD for the date", 400)
        if booking_date < date.today():
            return error("Cannot book a past date", 400)
    except (ValueError, TypeError):
        return error("Invalid reservation date", 400)

    # 2. Get the logged-in customer
    try:
        user_id = int(get_jwt_identity())
    except (ValueError, TypeError):
        return error("Invalid user identity", 401)

    conn = None
    cursor = None

    try:
        conn = get_db()
        conn.start_transaction()
        cursor = conn.cursor(dictionary=True)

        # 3. Verify user is a customer
        cursor.execute(
            "SELECT role FROM users WHERE id = %s",
            (user_id,)
        )
        user = cursor.fetchone()

        if user is None:
            return error("User not found", 401)
        if user["role"] != "customer":
            return error("Only customers can book tables", 403)

        # 4. Check table and party size
        cursor.execute(
            """
            SELECT capacity, is_active
            FROM restaurant_tables
            WHERE id = %s
            FOR UPDATE
            """,
            (data["table_id"],)
        )
        table = cursor.fetchone()

        if table is None:
            return error("Table not found", 404)
        if not table["is_active"]:
            return error("Table is inactive", 400)
        if data["party_size"] > table["capacity"]:
            return error("Party exceeds table capacity", 400)

        # 5. Check the time slot
        cursor.execute(
            "SELECT id FROM time_slots WHERE id = %s",
            (data["slot_id"],)
        )
        if cursor.fetchone() is None:
            return error("Time slot not found", 404)

        # 6. Create the reservation
        cursor.execute(
            """
            INSERT INTO reservations
            (user_id, table_id, slot_id,
             reservation_date, party_size, status)
            VALUES (%s, %s, %s, %s, %s, 'confirmed')
            """,
            (
                user_id,
                data["table_id"],
                data["slot_id"],
                booking_date,
                data["party_size"]
            )
        )

        reservation_id = cursor.lastrowid
        conn.commit()

        # 7. Return confirmation
        return jsonify({
            "id": reservation_id,
            "user_id": user_id,
            "table_id": data["table_id"],
            "slot_id": data["slot_id"],
            "reservation_date": booking_date.isoformat(),
            "party_size": data["party_size"],
            "status": "confirmed"
        }), 201

    except IntegrityError as exc:
        if exc.errno == errorcode.ER_DUP_ENTRY:
            return error("Table already reserved", 409)
        current_app.logger.exception("Reservation integrity error")
        return error("Could not create reservation", 500)

    except Error:
        current_app.logger.exception("Reservation database error")
        return error("Database error", 500)

    finally:
        # Roll back unfinished work and close the connection
        if conn is not None:
            if conn.in_transaction:
                conn.rollback()
            if cursor is not None:
                cursor.close()
            conn.close()

