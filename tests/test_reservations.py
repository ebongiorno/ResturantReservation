# Test creating a valid reservation
def test_create_reservation(client, auth_headers, reservation_data):

    response = client.post(
        "/api/v1/reservations",
        json=reservation_data,
        headers=auth_headers
    )

    assert response.status_code == 201
    assert response.json["status"] == "confirmed"
    assert response.json["party_size"] == 4


# Test that the same table cannot be booked twice
def test_duplicate_reservation(client, auth_headers, reservation_data):

    # First reservation should succeed
    first = client.post(
        "/api/v1/reservations",
        json=reservation_data,
        headers=auth_headers
    )

    # Second reservation uses the exact same information
    second = client.post(
        "/api/v1/reservations",
        json=reservation_data,
        headers=auth_headers
    )

    assert first.status_code == 201
    assert second.status_code == 409


# Test that party size cannot be negative
def test_negative_party_size(client, auth_headers, reservation_data):

    # Change the valid party size to an invalid value
    reservation_data["party_size"] = -1

    response = client.post(
        "/api/v1/reservations",
        json=reservation_data,
        headers=auth_headers
    )

    assert response.status_code == 400
    assert response.json["error"]["code"] == "invalid_input"


# Test that party size cannot exceed table capacity
def test_table_capacity(client, auth_headers, reservation_data):

    # Table 1 has a capacity of 2
    reservation_data["table_id"] = 1
    reservation_data["party_size"] = 4

    response = client.post(
        "/api/v1/reservations",
        json=reservation_data,
        headers=auth_headers
    )

    assert response.status_code == 400
    assert response.json["error"]["code"] == "invalid_input"


# Test that a nonexistent table returns 404
def test_invalid_table(client, auth_headers, reservation_data):

    # Use a table ID that does not exist
    reservation_data["table_id"] = 999999

    response = client.post(
        "/api/v1/reservations",
        json=reservation_data,
        headers=auth_headers
    )

    assert response.status_code == 404
    assert response.json["error"]["code"] == "not_found"


# Test that reservations require authentication
def test_missing_token(client, reservation_data):

    response = client.post(
        "/api/v1/reservations",
        json=reservation_data
    )

    assert response.status_code == 401


# Test that staff cannot create customer reservations
def test_staff_cannot_book(client, staff_headers, reservation_data):

    response = client.post(
        "/api/v1/reservations",
        json=reservation_data,
        headers=staff_headers
    )

    assert response.status_code == 403
    assert response.json["error"]["code"] == "forbidden"


# Test that reservations cannot be made for past dates
def test_past_reservation_date(client, auth_headers, reservation_data):

    # Change the date to one in the past
    reservation_data["reservation_date"] = "2020-01-01"

    response = client.post(
        "/api/v1/reservations",
        json=reservation_data,
        headers=auth_headers
    )

    assert response.status_code == 400
    assert response.json["error"]["code"] == "invalid_input"
