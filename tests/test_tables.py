
from unittest.mock import MagicMock


import pytest
from flask_jwt_extended import create_access_token
from mysql.connector import IntegrityError

from app import create_app



@pytest.fixture
def app():
    # Use Flask's test client without starting the server
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def staff_headers(app):
    # Make a staff token for testing protected routes
    with app.app_context():
        token = create_access_token(
            identity="1",
            additional_claims={"role": "staff"}
        )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def customer_headers(app):
    with app.app_context():
        token = create_access_token(
            identity="2",
            additional_claims={"role": "customer"}
        )
    return {"Authorization": f"Bearer {token}"}






@pytest.fixture
def fake_db(monkeypatch):
    # Replace the real MySQL connection with a mock
    db = MagicMock()
    cursor = MagicMock()

    db.cursor.return_value = cursor

    monkeypatch.setattr("app.tables.get_db", lambda: db)
    return db, cursor


def test_list_tables(client, fake_db):
    db, cursor = fake_db

    cursor.fetchone.return_value = {"total": 6}
    cursor.fetchall.return_value = [
        {"id": 1, "table_number": 1, "capacity": 2, "is_active": 1},
        {"id": 2, "table_number": 2, "capacity": 2, "is_active": 1}
    ]

    response = client.get("/api/v1/tables?page=1&per_page=2")
    assert response.status_code == 200
    assert len(response.json["data"]) == 2
    assert response.json["total"] == 6
    assert response.json["per_page"] == 2
    db.close.assert_called_once()


@pytest.mark.parametrize("query", [
    "?page=0",
    "?per_page=0",
    "?page=abc",
    "?per_page=101"])

def test_invalid_pagination(client, query):
    response = client.get(f"/api/v1/tables{query}")

    assert response.status_code == 400


def test_get_table(client, fake_db):
    db, cursor = fake_db

    cursor.fetchone.return_value = {
        "id": 3,
        "table_number": 3,
        "capacity": 4,
        "is_active": 1
    }

    response = client.get("/api/v1/tables/3")

    assert response.status_code == 200
    assert response.json["capacity"] == 4


def test_get_missing_table(client, fake_db):
    db, cursor = fake_db
    cursor.fetchone.return_value = None

    response = client.get("/api/v1/tables/999")

    assert response.status_code == 404


def test_create_table(client, staff_headers, fake_db):
    db, cursor = fake_db
    cursor.lastrowid = 7

    response = client.post(
        "/api/v1/tables",
        headers=staff_headers,
        json={"table_number": 7, "capacity": 4}
    )

    assert response.status_code == 201
    assert response.json["id"] == 7
    assert response.json["capacity"] == 4
    db.commit.assert_called_once()


def test_create_without_login(client):
    response = client.post(
        "/api/v1/tables",
        json={"table_number": 7, "capacity": 4}
    )

    assert response.status_code == 401


def test_create_as_customer(client, customer_headers):
    response = client.post(
        "/api/v1/tables",
        headers=customer_headers,
        json={"table_number": 7, "capacity": 4}
    )
    assert response.status_code == 403




@pytest.mark.parametrize("body", [
    {"table_number": 7, "capacity": 0},
    {"table_number": -1, "capacity": 4},
    {"table_number": 7},
    {"table_number": True, "capacity": 4},
    {"table_number": 7, "capacity": "four"}
])
def test_invalid_create(client, staff_headers, body):
    response = client.post(
        "/api/v1/tables",
        headers=staff_headers,
        json=body
    )

    assert response.status_code == 400


def test_duplicate_table(client, staff_headers, fake_db):
    db, cursor = fake_db
    cursor.execute.side_effect = IntegrityError(
        msg="Duplicate table number"
    )

    response = client.post(
        "/api/v1/tables",
        headers=staff_headers,
        json={"table_number": 1, "capacity": 4}
    )

    assert response.status_code == 409
    db.rollback.assert_called_once()


def test_update_table(client, staff_headers, fake_db):
    db, cursor = fake_db
    cursor.rowcount = 1

    response = client.put(
        "/api/v1/tables/7",
        headers=staff_headers,
        json={"table_number": 7, "capacity": 6}
    )

    assert response.status_code == 200
    assert response.json["capacity"] == 6
    db.commit.assert_called_once()

def test_update_missing_table(client, staff_headers, fake_db):
    db, cursor = fake_db
    cursor.rowcount = 0

    response = client.put(
        "/api/v1/tables/999",
        headers=staff_headers,
        json={"table_number": 999, "capacity": 4}
    )

    assert response.status_code == 404
    db.rollback.assert_called_once()


def test_delete_table(client, staff_headers, fake_db):
    db, cursor = fake_db
    cursor.rowcount = 1

    response = client.delete(
        "/api/v1/tables/7",
        headers=staff_headers
    )

    assert response.status_code == 204
    db.commit.assert_called_once()

    # Confirm this is a soft delete, not SQL DELETE
    sql = cursor.execute.call_args.args[0]
    assert "SET is_active = 0" in sql


def test_delete_missing_table(client, staff_headers, fake_db):
    db, cursor = fake_db
    cursor.rowcount = 0

    response = client.delete(
        "/api/v1/tables/999",
        headers=staff_headers
    )
    assert response.status_code == 404
    db.rollback.assert_called_once()



@pytest.mark.parametrize("method,path,body", [
    ("put", "/api/v1/tables/7", {"table_number": 7, "capacity": 6}),
    ("delete", "/api/v1/tables/7", None)
])
def test_customer_cannot_modify_tables(
    client, customer_headers, method, path, body
):
    response = getattr(client, method)(
        path,
        headers=customer_headers,
        json=body
    )

    assert response.status_code == 403
