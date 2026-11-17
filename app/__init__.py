# Note this is just a starter to test features.
# The person responsible for shared setup can handle the rest

from flask import Flask
from app.reservations import reservations_bp


def create_app():
    app = Flask(__name__)

    # Register reservation routes
    app.register_blueprint(reservations_bp)

    return app
