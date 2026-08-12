def test_create_player_route(client):
    response = client.post(
        "/players",
        json={
            "full_name": "John Smith",
            "display_name": "J. Smith",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["full_name"] == "John Smith"
    assert data["display_name"] == "J. Smith"
    assert data["id"] is not None
    assert data["created_at"] is not None
    assert data["updated_at"] is not None


def test_create_player_route_allows_duplicate_names(client):
    first_response = client.post(
        "/players",
        json={
            "full_name": "John Smith",
        },
    )

    second_response = client.post(
        "/players",
        json={
            "full_name": "John Smith",
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert first_response.json()["id"] != second_response.json()["id"]


def test_create_player_route_returns_422_for_invalid_input(client):
    response = client.post(
        "/players",
        json={
            "full_name": "   ",
        },
    )

    assert response.status_code == 422


def test_list_players_route_returns_players_in_id_order(client):
    first_response = client.post(
        "/players",
        json={
            "full_name": "First Player",
        },
    )

    second_response = client.post(
        "/players",
        json={
            "full_name": "Second Player",
        },
    )

    response = client.get("/players")

    assert response.status_code == 200

    data = response.json()

    assert [player["id"] for player in data] == [
        first_response.json()["id"],
        second_response.json()["id"],
    ]


def test_get_player_route_returns_existing_player(client):
    create_response = client.post(
        "/players",
        json={
            "full_name": "John Smith",
            "display_name": "J. Smith",
        },
    )

    player_id = create_response.json()["id"]

    response = client.get(f"/players/{player_id}")

    assert response.status_code == 200
    assert response.json()["id"] == player_id
    assert response.json()["full_name"] == "John Smith"
    assert response.json()["display_name"] == "J. Smith"


def test_get_player_route_returns_404_for_missing_id(client):
    response = client.get("/players/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Player with ID 999999 was not found."
    )


def test_update_player_route_partial_update(client):
    create_response = client.post(
        "/players",
        json={
            "full_name": "John Smith",
            "display_name": "J. Smith",
        },
    )

    player_id = create_response.json()["id"]

    response = client.patch(
        f"/players/{player_id}",
        json={
            "display_name": "Johnny",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["full_name"] == "John Smith"
    assert data["display_name"] == "Johnny"


def test_update_player_route_can_clear_display_name(client):
    create_response = client.post(
        "/players",
        json={
            "full_name": "John Smith",
            "display_name": "J. Smith",
        },
    )

    player_id = create_response.json()["id"]

    response = client.patch(
        f"/players/{player_id}",
        json={
            "display_name": None,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["full_name"] == "John Smith"
    assert data["display_name"] is None


def test_update_player_route_returns_404_for_missing_id(client):
    response = client.patch(
        "/players/999999",
        json={
            "display_name": "J. Smith",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Player with ID 999999 was not found."
    )


def test_update_player_route_returns_422_for_none_full_name(client):
    create_response = client.post(
        "/players",
        json={
            "full_name": "John Smith",
        },
    )

    player_id = create_response.json()["id"]

    response = client.patch(
        f"/players/{player_id}",
        json={
            "full_name": None,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Player full_name cannot be None"
    )