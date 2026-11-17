from flask import Blueprint, jsonify

# Blueprint for reservation-related endpoints
reservations_bp = Blueprint(
    "reservations",
    __name__,
    url_prefix="/api/v1/reservations"
)


# GET /api/v1/reservations
@reservations_bp.get("")
def get_reservations():
    return jsonify({
        "message": "Reservation endpoint is working!",
        "reservations": []
    }), 200
