
import re
from datetime import date

import mysql.connector
from mysql.connector import errorcode
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
def get_reservations():
    return jsonify({"reservations": []}), 200

# POST /api/v1/reservations
@reservations_bp.post("")
@jwt_required()
def create_reservation():

    # 1. Read and validate JSON
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return api_error(
            "invalid_input", "Expected a JSON object", 400
        )

    required = (
        "table_id", "slot_id", "reservation_date", "party_size"
    )
    missing = [field for field in required if field not in data]

    if missing:
        return api_error(
            "invalid_input",
            f"Missing fields: {', '.join(missing)}",
            400
        )

    for field in ("table_id", "slot_id", "party_size"):
        if not valid_positive_integer(data[field]):
            return api_error(
                "invalid_input",
                f"{field} must be a positive integer",
                400
            )

    # 2. Validate reservation date
    date_string = data["reservation_date"]

    if (
        not isinstance(date_string, str)
        or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_string)
    ):
        return api_error(
            "invalid_input",
            "reservation_date must use YYYY-MM-DD",
            400
        )

    try:
        reservation_date = date.fromisoformat(date_string)
    except ValueError:
        return api_error(
            "invalid_input", "Invalid reservation date", 400
        )

    if reservation_date < date.today():
        return api_error(
            "invalid_input", "Cannot book a past date", 400
        )

    # 3. Identify the authenticated user
    try:
        user_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return api_error(
            "unauthorized", "Invalid token identity", 401
        )

    conn = None
    cursor = None

    try:
        conn = get_db()
        conn.start_transaction()
        cursor = conn.cursor(dictionary=True)

        # 4. Check user and role
        cursor.execute(
            "SELECT role FROM users WHERE id = %s",
            (user_id,)
        )
        user = cursor.fetchone()

        if user is None:
            return api_error(
                "unauthorized", "User no longer exists", 401
            )

        if user["role"] != "customer":
            return api_error(
                "forbidden",
                "Only customers can create reservations",
                403
            )

        # 5. Check table and capacity
        cursor.execute(
            """
            SELECT id, capacity, is_active
            FROM restaurant_tables
            WHERE id = %s
            FOR UPDATE
            """,
            (data["table_id"],)
        )
        table = cursor.fetchone()

        if table is None:
            return api_error("not_found", "Table not found", 404)

        if not table["is_active"]:
            return api_error(
                "invalid_input", "Table is inactive", 400
            )

        if data["party_size"] > table["capacity"]:
            return api_error(
                "invalid_input",
                "Party size exceeds table capacity",
                400
            )

        # 6. Check time slot
        cursor.execute(
            "SELECT id FROM time_slots WHERE id = %s",
            (data["slot_id"],)
        )

        if cursor.fetchone() is None:
            return api_error(
                "not_found", "Time slot not found", 404
            )

        # 7. Insert reservation
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
                reservation_date,
                data["party_size"]
            )
        )

        reservation_id = cursor.lastrowid
        conn.commit()

        # 8. Return confirmation
        return jsonify({
            "id": reservation_id,
            "user_id": user_id,
            "table_id": data["table_id"],
            "slot_id": data["slot_id"],
            "reservation_date": reservation_date.isoformat(),
            "party_size": data["party_size"],
            "status": "confirmed"
        }), 201

    except mysql.connector.IntegrityError as exc:
        if conn is not None:
            conn.rollback()

        if exc.errno == errorcode.ER_DUP_ENTRY:
            return api_error(
                "conflict",
                "Table already reserved for this date and slot",
                409
            )

        current_app.logger.exception(
            "Reservation integrity error"
        )
        return api_error(
            "database_error", "Could not create reservation", 500
        )

    except mysql.connector.Error:
        if conn is not None:
            conn.rollback()

        current_app.logger.exception(
            "Reservation database error"
        )
        return api_error(
            "database_error", "Could not create reservation", 500
        )

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            if conn.in_transaction:
                conn.rollback()
            conn.close()