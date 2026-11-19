from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

# =========================================
# POST endpoint tests
# =========================================
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


# Test that a nonexistent time slot returns 404
def test_invalid_time_slot(client, auth_headers, reservation_data):

    # Use a time slot ID that does not exist
    reservation_data["slot_id"] = 999999

    response = client.post(
        "/api/v1/reservations",
        json=reservation_data,
        headers=auth_headers
    )

    assert response.status_code == 404
    assert response.json["error"]["code"] == "not_found"


# Test that missing required fields return 400
def test_missing_required_field(client, auth_headers, reservation_data):

    # Remove party_size from the request
    del reservation_data["party_size"]

    response = client.post(
        "/api/v1/reservations",
        json=reservation_data,
        headers=auth_headers
    )

    assert response.status_code == 400
    assert response.json["error"]["code"] == "invalid_input"


# Test two requests competing for the same table
def test_concurrent_reservations(app, token, reservation_data):

    barrier = Barrier(2)

    # Each thread sends its own POST request
    def book_table():
        with app.test_client() as client:
            barrier.wait()

            response = client.post(
                "/api/v1/reservations",
                json=reservation_data,
                headers={"Authorization": f"Bearer {token}"}
            )

            return response.status_code

    # Run two booking requests concurrently
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(book_table)
        second = executor.submit(book_table)

        results = [first.result(), second.result()]

    assert sorted(results) == [201, 409]


# =========================================
# GET endpoint tests
# =========================================

# Test that customers can retrieve their reservations
def test_get_reservations(client, auth_headers, reservation_data):

    # Create a reservation first
    created = client.post(
        "/api/v1/reservations",
        json=reservation_data,
        headers=auth_headers
    )

    assert created.status_code == 201

    # Retrieve the customer's reservations
    response = client.get(
        "/api/v1/reservations",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert any(
        reservation["id"] == created.json["id"]
        for reservation in response.json["reservations"]
    )


# Test that a customer can retrieve a specific reservation
def test_get_reservation_by_id(client, auth_headers, reservation_data):

    # Create a reservation first
    created = client.post(
        "/api/v1/reservations",
        json=reservation_data,
        headers=auth_headers
    )

    assert created.status_code == 201

    # Get the ID of the new reservation
    reservation_id = created.json["id"]

    # Retrieve that specific reservation
    response = client.get(
        f"/api/v1/reservations/{reservation_id}",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json["id"] == reservation_id
    assert response.json["party_size"] == 4
    assert response.json["status"] == "confirmed"


# Test retrieving a reservation that doesn't exist
def test_get_invalid_reservation(client, auth_headers):

    response = client.get(
        "/api/v1/reservations/999999",
        headers=auth_headers
    )

    assert response.status_code == 404
    assert response.json["error"]["code"] == "not_found"


# Test that customers cannot view another customer's reservation
def test_get_other_customer_reservation(
    client, auth_headers, other_customer_headers, reservation_data
):

    # Customer A creates a reservation
    created = client.post(
        "/api/v1/reservations",
        json=reservation_data,
        headers=auth_headers
    )

    assert created.status_code == 201

    reservation_id = created.json["id"]

    # Customer B tries to retrieve Customer A's reservation
    response = client.get(
        f"/api/v1/reservations/{reservation_id}",
        headers=other_customer_headers
    )

    assert response.status_code == 403
    assert response.json["error"]["code"] == "forbidden"


# Test that staff can view a customer's reservation
def test_staff_get_reservation(
    client, staff_headers, other_customer_headers, reservation_data
):

    # Customer creates a reservation
    created = client.post(
        "/api/v1/reservations",
        json=reservation_data,
        headers=other_customer_headers
    )

    assert created.status_code == 201

    reservation_id = created.json["id"]

    # Staff retrieves the customer's reservation
    response = client.get(
        f"/api/v1/reservations/{reservation_id}",
        headers=staff_headers
    )

    assert response.status_code == 200
    assert response.json["id"] == reservation_id


# Test that customers only see their own reservations
def test_get_only_own_reservations(
    client, auth_headers, other_customer_headers, reservation_data
):

    # Customer A creates a reservation
    first = client.post(
        "/api/v1/reservations",
        json=reservation_data,
        headers=auth_headers
    )

    # Customer B creates a different reservation
    other_data = reservation_data.copy()
    other_data["slot_id"] = 1

    second = client.post(
        "/api/v1/reservations",
        json=other_data,
        headers=other_customer_headers
    )

    assert first.status_code == 201
    assert second.status_code == 201

    # Customer A retrieves their reservation list
    response = client.get(
        "/api/v1/reservations",
        headers=auth_headers
    )

    assert response.status_code == 200

    reservations = response.json["reservations"]
    reservation_ids = [r["id"] for r in reservations]

    # Customer A sees their own reservation
    assert first.json["id"] in reservation_ids

    # Customer A cannot see Customer B's reservation
    assert second.json["id"] not in reservation_ids


# Test that staff can retrieve customer reservations
def test_staff_get_all_reservations(
    client, staff_headers, other_customer_headers, reservation_data
):

    # Create a reservation as a customer
    created = client.post(
        "/api/v1/reservations",
        json=reservation_data,
        headers=other_customer_headers
    )

    assert created.status_code == 201

    # Staff retrieves the reservation list
    response = client.get(
        "/api/v1/reservations",
        headers=staff_headers
    )

    assert response.status_code == 200

    reservations = response.json["reservations"]
    reservation_ids = [r["id"] for r in reservations]

    # Staff can see the customer's reservation
    assert created.json["id"] in reservation_ids


# Test that reservation pagination works
def test_reservation_pagination(
    client, auth_headers, reservation_data
):

    # Create three reservations in different time slots
    created_ids = []

    for slot_id in [1, 2, 3]:
        data = reservation_data.copy()
        data["slot_id"] = slot_id

        response = client.post(
            "/api/v1/reservations",
            json=data,
            headers=auth_headers
        )

        assert response.status_code == 201
        created_ids.append(response.json["id"])

    # Get page 1 with two reservations per page
    first_page = client.get(
        "/api/v1/reservations?page=1&per_page=2",
        headers=auth_headers
    )

    # Get page 2
    second_page = client.get(
        "/api/v1/reservations?page=2&per_page=2",
        headers=auth_headers
    )

    assert first_page.status_code == 200
    assert second_page.status_code == 200

    assert len(first_page.json["reservations"]) == 2
    assert len(second_page.json["reservations"]) == 1

    # Make sure all three reservations were returned
    all_ids = [
        r["id"] for r in first_page.json["reservations"]
    ] + [
        r["id"] for r in second_page.json["reservations"]
    ]

    assert set(all_ids) == set(created_ids)


# Test that invalid pagination parameters return 400
def test_invalid_pagination(client, auth_headers):

    response = client.get(
        "/api/v1/reservations?page=-1&per_page=10",
        headers=auth_headers
    )

    assert response.status_code == 400
    assert response.json["error"]["code"] == "invalid_input"
