from sqlalchemy import select

from app.models.player import Player
from app.models.season import Season
from app.models.season_roster import (
    RosterStatus,
    SeasonRoster,
)
from app.models.team import Team


def _season(
    db_session,
    *,
    team_name="Player Onboarding Team",
    season_name="2031-2032",
):
    team = Team(
        name=team_name,
    )

    db_session.add(team)
    db_session.flush()

    season = Season(
        team_id=team.id,
        name=season_name,
    )

    db_session.add(season)
    db_session.commit()
    db_session.refresh(season)

    return season


def test_player_search_returns_matches(
    logged_in_client,
    db_session,
):
    db_session.add_all(
        [
            Player(
                full_name="Kevin Johnson",
                display_name="Kevin",
            ),
            Player(
                full_name="Michael Smith",
            ),
        ]
    )

    db_session.commit()

    response = logged_in_client.get(
        "/app/players/search?q=kevin"
    )

    assert response.status_code == 200

    payload = response.json()

    assert len(payload) == 1

    assert (
        payload[0]["full_name"]
        == "Kevin Johnson"
    )

    assert (
        payload[0]["display_name"]
        == "Kevin"
    )


def test_player_search_is_case_insensitive(
    logged_in_client,
    db_session,
):
    player = Player(
        full_name="Alexander Brown",
    )

    db_session.add(player)
    db_session.commit()

    response = logged_in_client.get(
        "/app/players/search?q=ALEX"
    )

    assert response.status_code == 200

    assert any(
        row["id"] == player.id
        for row in response.json()
    )


def test_empty_player_search_returns_empty_list(
    logged_in_client,
):
    response = logged_in_client.get(
        "/app/players/search?q="
    )

    assert response.status_code == 200
    assert response.json() == []


def test_roster_form_uses_player_picker(
    logged_in_client,
    db_session,
):
    season = _season(
        db_session,
    )

    response = logged_in_client.get(
        (
            "/app/roster/new?"
            f"season_id={season.id}"
        )
    )

    assert response.status_code == 200

    assert "data-player-picker" in (
        response.text
    )

    assert "Search Player" in (
        response.text
    )

    assert "+ Create New Player" in (
        response.text
    )

    assert (
        '<select class="select" '
        'id="player_id"'
        not in response.text
    )


def test_create_player_from_season_setup_returns_to_roster_form(
    authenticated_client,
    db_session,
):
    season = _season(
        db_session,
    )

    response = authenticated_client.post(
        "/app/players/new",
        data={
            "full_name": "New Setup Player",
            "display_name": "Setup",
            "return_context": (
                "season_setup"
            ),
            "season_id": str(
                season.id
            ),
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    player = db_session.scalar(
        select(Player).where(
            Player.full_name
            == "New Setup Player"
        )
    )

    assert player is not None

    assert (
        response.headers["location"]
        == (
            "/app/roster/new?"
            f"new_player_id={player.id}"
            f"&season_id={season.id}"
            "&return_context=season_setup"
        )
    )

    roster_entries = list(
        db_session.scalars(
            select(SeasonRoster).where(
                SeasonRoster.season_id
                == season.id
            )
        ).all()
    )

    assert roster_entries == []


def test_new_player_is_preselected_after_return(
    logged_in_client,
    db_session,
):
    season = _season(
        db_session,
    )

    player = Player(
        full_name="Preselected Player",
    )

    db_session.add(player)
    db_session.commit()
    db_session.refresh(player)

    response = logged_in_client.get(
        (
            "/app/roster/new?"
            f"season_id={season.id}&"
            "return_context=season_setup&"
            f"new_player_id={player.id}"
        )
    )

    assert response.status_code == 200

    normalized_html = " ".join(
        response.text.split()
    )

    assert "Preselected Player" in (
        response.text
    )

    assert (
        f'name="player_id" '
        f'data-player-id '
        f'value="{player.id}"'
        in normalized_html
    )


def test_duplicate_player_names_remain_allowed(
    authenticated_client,
    db_session,
):
    existing = Player(
        full_name="Same Name",
    )

    db_session.add(existing)
    db_session.commit()

    response = authenticated_client.post(
        "/app/players/new",
        data={
            "full_name": "Same Name",
            "display_name": "",
            "return_context": "",
            "season_id": "",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    players = list(
        db_session.scalars(
            select(Player).where(
                Player.full_name
                == "Same Name"
            )
        ).all()
    )

    assert len(players) == 2


def test_edit_roster_locks_player_and_season_identity(
    logged_in_client,
    db_session,
):
    season = _season(
        db_session,
    )

    player = Player(
        full_name="Locked Player",
    )

    db_session.add(player)
    db_session.flush()

    roster = SeasonRoster(
        season_id=season.id,
        player_id=player.id,
        jersey_number=5,
        status=RosterStatus.ACTIVE,
    )

    db_session.add(roster)
    db_session.commit()
    db_session.refresh(roster)

    response = logged_in_client.get(
        f"/app/roster/{roster.id}/edit"
    )

    assert response.status_code == 200

    assert "Locked Player" in response.text
    assert season.name in response.text

    assert 'id="player_display"' in (
        response.text
    )

    assert 'id="season_display"' in (
        response.text
    )

    assert 'name="player_id"' not in (
        response.text
    )

    assert 'name="season_id"' not in (
        response.text
    )


def test_edit_roster_ignores_identity_fields(
    authenticated_client,
    db_session,
):
    season = _season(
        db_session,
    )

    other_season = _season(
        db_session,
        team_name="Other Team",
        season_name="2032-2033",
    )

    player = Player(
        full_name="Original Player",
    )

    other_player = Player(
        full_name="Other Player",
    )

    db_session.add_all(
        [
            player,
            other_player,
        ]
    )

    db_session.flush()

    roster = SeasonRoster(
        season_id=season.id,
        player_id=player.id,
        jersey_number=7,
        status=RosterStatus.ACTIVE,
    )

    db_session.add(roster)
    db_session.commit()
    db_session.refresh(roster)

    response = authenticated_client.post(
        f"/app/roster/{roster.id}/edit",
        data={
            "season_id": str(
                other_season.id
            ),
            "player_id": str(
                other_player.id
            ),
            "jersey_number": "14",
            "position": "Guard",
            "grade_level": "12",
            "status": "ACTIVE",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    db_session.refresh(roster)

    assert roster.season_id == season.id
    assert roster.player_id == player.id

    assert roster.jersey_number == 14
    assert roster.position == "Guard"