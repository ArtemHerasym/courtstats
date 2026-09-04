from app.models.player import Player
from app.models.season import Season
from app.models.season_roster import (
    SeasonRoster,
)
from app.models.team import Team


def _team(
    db_session,
):
    team = Team(
        name="Management Team",
        abbreviation="MGT",
    )

    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    return team


def test_management_form_pages_load(
    authenticated_client,
):
    paths = [
        "/app/seasons/new",
        "/app/players/new",
        "/app/roster/new",
    ]

    for path in paths:
        response = authenticated_client.get(
            path
        )

        assert response.status_code == 200


def test_create_and_edit_season_through_html(
    authenticated_client,
    db_session,
):
    team = _team(
        db_session,
    )

    response = authenticated_client.post(
        "/app/seasons/new",
        data={
            "team_id": str(team.id),
            "name": "2030-31",
            "start_date": "2030-08-01",
            "end_date": "2031-05-31",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    season = (
        db_session.query(Season)
        .filter_by(name="2030-31")
        .one()
    )

    edit_response = (
        authenticated_client.post(
            f"/app/seasons/"
            f"{season.id}/edit",
            data={
                "team_id": str(team.id),
                "name": "2030-31 Updated",
                "start_date": "2030-08-01",
                "end_date": "2031-05-31",
                "status": "ACTIVE",
            },
            follow_redirects=False,
        )
    )

    assert edit_response.status_code == 303

    db_session.refresh(season)

    assert (
        season.name
        == "2030-31 Updated"
    )

    assert season.status.value == "ACTIVE"


def test_create_and_edit_player_through_html(
    authenticated_client,
    db_session,
):
    response = authenticated_client.post(
        "/app/players/new",
        data={
            "full_name": "New Player",
            "display_name": "New",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    player = (
        db_session.query(Player)
        .filter_by(
            full_name="New Player"
        )
        .one()
    )

    response = authenticated_client.post(
        f"/app/players/"
        f"{player.id}/edit",
        data={
            "full_name": "Updated Player",
            "display_name": "Updated",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    db_session.refresh(player)

    assert (
        player.full_name
        == "Updated Player"
    )

    assert (
        player.display_name
        == "Updated"
    )


def test_add_and_edit_roster_entry_through_html(
    authenticated_client,
    db_session,
):
    team = _team(
        db_session,
    )

    season = Season(
        team_id=team.id,
        name="Roster Season",
    )

    player = Player(
        full_name="Roster Player",
    )

    db_session.add_all(
        [
            season,
            player,
        ]
    )

    db_session.commit()

    response = authenticated_client.post(
        "/app/roster/new",
        data={
            "season_id": str(
                season.id
            ),
            "player_id": str(
                player.id
            ),
            "jersey_number": "12",
            "position": "G",
            "grade_level": "12",
            "status": "ACTIVE",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    roster = (
        db_session.query(
            SeasonRoster
        )
        .filter_by(
            season_id=season.id,
            player_id=player.id,
        )
        .one()
    )

    assert roster.jersey_number == 12
    assert roster.position == "G"

    response = authenticated_client.post(
        f"/app/roster/"
        f"{roster.id}/edit",
        data={
            "season_id": str(
                season.id
            ),
            "player_id": str(
                player.id
            ),
            "jersey_number": "24",
            "position": "F",
            "grade_level": "12",
            "status": "ACTIVE",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    db_session.refresh(roster)

    assert roster.jersey_number == 24
    assert roster.position == "F"


def test_management_pages_require_authentication(
    client,
):
    paths = [
        "/app/seasons/new",
        "/app/players/new",
        "/app/roster/new",
    ]

    for path in paths:
        response = client.get(
            path,
            follow_redirects=False,
        )

        assert response.status_code == 303

        assert (
            response.headers["location"]
            == "/login"
        )