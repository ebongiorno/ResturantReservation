
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt
from mysql.connector import IntegrityError

from app.db import get_db

tables_bp = Blueprint("tables", __name__, url_prefix="/api/v1/tables")


def staff_only():
    # Note: Role should be stored in the JWT by an authentication mod
    return get_jwt().get("role") == "staff"


def valid_number(value):
    return type(value) is int and value > 0


# GET /api/v1/tables
#pagination
@tables_bp.route("", methods=["GET"])
def list_tables():
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 10))
    except (ValueError, TypeError):
        return jsonify(error="Invalid pagination values"), 400

    if page < 1 or per_page < 1 or per_page > 100:
        return jsonify(error="Invalid pagination values"), 400


    db = get_db()


    try:
        cursor = db.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) AS total FROM restaurant_tables")
        total = cursor.fetchone()["total"]

        cursor.execute(
            """
            SELECT id, table_number, capacity, is_active
            FROM restaurant_tables
            ORDER BY table_number
            LIMIT %s OFFSET %s
            """,
            (per_page, (page - 1) * per_page)
            )

        return jsonify(data=cursor.fetchall(), page = page, per_page = per_page, total = total), 200

    finally:
        db.close()


# GET /api/v1/tables/<id>
#This gets one table.
@tables_bp.route("/<int:table_id>", methods=["GET"])
def get_table(table_id):
    db = get_db()

    try:
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, table_number, capacity, is_active
            FROM restaurant_tables
            WHERE id = %s
            """,
            (table_id,)
        )

        table = cursor.fetchone()

        if table is None:
            return jsonify(error="Table not found"), 404

        return jsonify(table), 200

    finally:
        db.close()


# POST /api/v1/tables
# This makes a table (staff permissions only)
@tables_bp.route("", methods=["POST"])
@jwt_required()
def create_table():
    if not staff_only():
        return jsonify(error="Staff access required"), 403

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(error="JSON object required"), 400

    table_number = data.get("table_number")
    capacity = data.get("capacity")

    if not valid_number(table_number) or not valid_number(capacity):
        return jsonify(error="table_number and capacity must be positive integers"), 400

    db = get_db()

    try:
        cursor = db.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO restaurant_tables (table_number, capacity)
                VALUES (%s, %s)
                """,
                (table_number, capacity)
            )
            db.commit()

        except IntegrityError:
            db.rollback()
            return jsonify(error="Table number already exists"), 409

        return jsonify(
            id=cursor.lastrowid,
            table_number=table_number,
            capacity=capacity,
            is_active=1
        ), 201

    finally:
        db.close()


# PUT /api/v1/tables/<id>
# This updates a table (staff permissions only)
@tables_bp.route("/<int:table_id>", methods=["PUT"])
@jwt_required()
def update_table(table_id):
    if not staff_only():
        return jsonify(error="Staff access required"), 403

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(error="JSON object required"), 400

    table_number = data.get("table_number")
    capacity = data.get("capacity")

    if not valid_number(table_number) or not valid_number(capacity):
        return jsonify(error="table_number and capacity must be positive integers"), 400

    db = get_db()

    try:
        cursor = db.cursor()

        try:
            cursor.execute(
                """
                UPDATE restaurant_tables
                SET table_number = %s, capacity = %s
                WHERE id = %s
                """,
                (table_number, capacity, table_id)
            )

            if cursor.rowcount == 0:
                db.rollback()
                return jsonify(error="Table not found"), 404

            db.commit()

        except IntegrityError:
            db.rollback()
            return jsonify(error="Table number already exists or invalid data"), 409

        return jsonify(
            id=table_id,
            table_number=table_number,
            capacity=capacity
        ), 200

    finally:
        db.close()


# DELETE /api/v1/tables/<id>
# This removes a table (staff permissions only)
@tables_bp.route("/<int:table_id>", methods=["DELETE"])
@jwt_required()
def delete_table(table_id):
    if not staff_only():
        return jsonify(error="Staff access required"), 403

    db = get_db()

    try:
        cursor = db.cursor()

        cursor.execute(
            """
            UPDATE restaurant_tables
            SET is_active = 0
            WHERE id = %s AND is_active = 1
            """,
            (table_id,)
        )

        if cursor.rowcount == 0:
            db.rollback()
            return jsonify(error="Active table not found"), 404

        db.commit()

        return "", 204

    finally:
        db.close()
