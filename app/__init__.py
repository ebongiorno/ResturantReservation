# Note this is just a starter to test features.
# The person responsible for shared setup can handle the rest

from flask import Flask
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
import os

from app.reservations import reservations_bp
from app.tables import tables_bp


def create_app():
    app = Flask(__name__)
    
    load_dotenv()

    app.config["JWT_SECRET_KEY"] = os.environ["JWT_SECRET_KEY"]
    JWTManager(app)

    # Register reservation routes
    app.register_blueprint(reservations_bp)

    # Register table routes
    app.register_blueprint(tables_bp)

    return app
