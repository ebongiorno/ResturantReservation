from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt
from mysql.connector import Error, IntegrityError

from app.db import get_db


tables_bp = Blueprint("tables", __name__, url_prefix="/api/v1/tables")



#pagination
@tables_bp.route("", methods=["GET"])   
def list_tables():
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 10))
    except ValueError:
        return jsonify(error="page and per_page must be integers"), 400

    if page < 1 or per_page < 1 or per_page > 100:
        return jsonify(error="Invalid pagination values"), 400

    offset = (page - 1) * per_page

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
            (per_page, offset)
        )

        tables = cursor.fetchall()

        return jsonify(
            data=tables,
            page=page,
            per_page=per_page,
            total=total
        ), 200

    finally:
        db.close()