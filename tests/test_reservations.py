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

