from app.models.team import Team

def test_create_season_route(authenticated_client, db_session):
    team = Team(
        name="Jordan Christian Preparatory",
        abbreviation="JCP",
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    response = authenticated_client.post(
        "/seasons",
        json={
            "team_id": team.id,
            "name": "2026-27",
            "start_date": "2026-10-01",
            "end_date": "2027-03-31",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["team_id"] == team.id
    assert data["name"] == "2026-27"
    assert data["start_date"] == "2026-10-01"
    assert data["end_date"] == "2027-03-31"
    assert data["status"] == "SETUP"
    assert data["id"] is not None

def test_create_season_route_returns_409_for_duplicate_name(authenticated_client, db_session):
    team = Team(name="Jordan Christian Preparatory", abbreviation="JCP")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    season_data = {
        "team_id": team.id,
        "name": "2026-27",
    }

    first_response = authenticated_client.post("/seasons", json=season_data)
    second_response = authenticated_client.post("/seasons", json=season_data)

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == (
        "A seasons with this name already exists for this team."
    )


def test_create_season_route_returns_422_for_invalid_input(authenticated_client, db_session):
    team = Team(name="Jordan Christian Preparatory", abbreviation="JCP")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    response = authenticated_client.post(
        "/seasons",
        json={
            "team_id": team.id,
            "name": "   ",
        },
    )

    assert response.status_code == 422


def test_list_seasons_route_returns_seasons_in_id_order(authenticated_client, db_session):
    team = Team(name="Jordan Christian Preparatory", abbreviation="JCP")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    first_response = authenticated_client.post(
        "/seasons",
        json={
            "team_id": team.id,
            "name": "2025-26",
        },
    )

    second_response = authenticated_client.post(
        "/seasons",
        json={
            "team_id": team.id,
            "name": "2026-27",
        },
    )

    response = authenticated_client.get("/seasons")

    assert response.status_code == 200

    data = response.json()

    assert [season["id"] for season in data] == [
        first_response.json()["id"],
        second_response.json()["id"],
    ]


def test_get_season_route_returns_existing_season(authenticated_client, db_session):
    team = Team(name="Jordan Christian Preparatory", abbreviation="JCP")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    create_response = authenticated_client.post(
        "/seasons",
        json={
            "team_id": team.id,
            "name": "2026-27",
        },
    )

    season_id = create_response.json()["id"]

    response = authenticated_client.get(f"/seasons/{season_id}")

    assert response.status_code == 200
    assert response.json()["id"] == season_id
    assert response.json()["name"] == "2026-27"


def test_get_season_route_returns_404_for_missing_id(authenticated_client):
    response = authenticated_client.get("/seasons/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Season with ID 999999 was not found."
    )


def test_update_season_route_partial_update(authenticated_client, db_session):
    team = Team(name="Jordan Christian Preparatory", abbreviation="JCP")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    create_response = authenticated_client.post(
        "/seasons",
        json={
            "team_id": team.id,
            "name": "2026-27",
            "start_date": "2026-10-01",
            "end_date": "2027-03-31",
        },
    )

    season_id = create_response.json()["id"]

    response = authenticated_client.patch(
        f"/seasons/{season_id}",
        json={
            "status": "ACTIVE",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ACTIVE"
    assert data["name"] == "2026-27"
    assert data["start_date"] == "2026-10-01"
    assert data["end_date"] == "2027-03-31"
    assert data["team_id"] == team.id


def test_update_season_route_returns_404_for_missing_id(authenticated_client):
    response = authenticated_client.patch(
        "/seasons/999999",
        json={
            "status": "ACTIVE",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Season with ID 999999 was not found."
    )


def test_update_season_route_returns_409_for_duplicate_name(
    authenticated_client,
    db_session,
):
    team = Team(name="Jordan Christian Preparatory", abbreviation="JCP")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    authenticated_client.post(
        "/seasons",
        json={
            "team_id": team.id,
            "name": "2025-26",
        },
    )

    second_response = authenticated_client.post(
        "/seasons",
        json={
            "team_id": team.id,
            "name": "2026-27",
        },
    )

    second_season_id = second_response.json()["id"]

    response = authenticated_client.patch(
        f"/seasons/{second_season_id}",
        json={
            "name": "2025-26",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "A seasons with this name already exists for this team."
    )


def test_update_season_route_returns_422_for_invalid_final_date_range(
    authenticated_client,
    db_session,
):
    team = Team(name="Jordan Christian Preparatory", abbreviation="JCP")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    create_response = authenticated_client.post(
        "/seasons",
        json={
            "team_id": team.id,
            "name": "2026-27",
            "start_date": "2026-10-01",
            "end_date": "2027-03-31",
        },
    )

    season_id = create_response.json()["id"]

    response = authenticated_client.patch(
        f"/seasons/{season_id}",
        json={
            "end_date": "2026-09-01",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "End date cannot be earlier than start date"
    )