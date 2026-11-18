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
