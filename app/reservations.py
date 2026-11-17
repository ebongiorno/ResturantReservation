
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
def api_error(code, message, status):
    return jsonify({
        "error": {
            "code": code,
            "message": message
        }
    }), status

def valid_positive_integer(value):
    return type(value) is int and value > 0

# GET /api/v1/reservations
@reservations_bp.get("")
def get_reservations():
    return jsonify({"reservations": []}), 200


