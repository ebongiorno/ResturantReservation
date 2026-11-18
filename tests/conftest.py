import uuid
from datetime import date, timedelta

import pytest
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app
from app.db import get_db


TEST_DB = "restaurant_test_db"


@pytest.fixture
def app(monkeypatch):
    # Use the test database, not the normal database
    monkeypatch.setenv("DB_NAME", TEST_DB)
    monkeypatch.setenv("JWT_SECRET_KEY", "pytest-only-secret")

    app = create_app()
    app.config["TESTING"] = True

    return app

@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def token(app):
    conn = get_db()

    # Safety check before writing anything
    if conn.database != TEST_DB:
        conn.close()
        raise RuntimeError("Not connected to test database!")

    cursor = conn.cursor()
    user_id = None

    try:
        # Create a customer with a unique email
        email = f"test-{uuid.uuid4().hex}@example.invalid"

        cursor.execute(
            """
            INSERT INTO users
                (name, email, password_hash, role)
            VALUES (%s, %s, %s, 'customer')
            """,
            (
                "Test Customer",
                email,
                generate_password_hash("test-password")
            )
        )

        user_id = cursor.lastrowid
        conn.commit()

        # Generate a JWT for this customer
        with app.app_context():
            jwt = create_access_token(identity=str(user_id))

        yield jwt

    finally:
        # Clean up records created by this customer
        if user_id is not None:
            cursor.execute(
                "DELETE FROM reservations WHERE user_id = %s",
                (user_id,)
            )
            cursor.execute(
                "DELETE FROM waitlist_entries WHERE user_id = %s",
                (user_id,)
            )
            cursor.execute(
                "DELETE FROM users WHERE id = %s",
                (user_id,)
            )
            conn.commit()

        cursor.close()
        conn.close()

@pytest.fixture
def auth_headers(token):
    return {
        "Authorization": f"Bearer {token}"
    }

@pytest.fixture
def reservation_data():
    return {
        "table_id": 3,
        "slot_id": 2,
        "reservation_date": (
            date.today() + timedelta(days=30)
        ).isoformat(),
        "party_size": 4
    }