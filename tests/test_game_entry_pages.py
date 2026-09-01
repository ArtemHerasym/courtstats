from sqlalchemy import select
from datetime import date, timedelta
from app.models.game import Game, GameStatus
from app.models.player_game_stats import PlayerGameStats
from app.models.team import Team


def _setup_game_with_roster(authenticated_client, db_session):
    team = Team(
        name="Jordan Christian Preparatory",
        abbreviation="JCP",
    )
    opponent = Team(
        name="Test Opponent",
        abbreviation="TEST",
    )

    db_session.add_all([team, opponent])
    db_session.commit()
    db_session.refresh(team)
    db_session.refresh(opponent)

    season_response = authenticated_client.post(
        "/seasons",
        json={
            "team_id": team.id,
            "name": "2026-27",
        },
    )
    assert season_response.status_code == 201
    season = season_response.json()

    player_response = authenticated_client.post(
        "/players",
        json={
            "full_name": "Test Player",
        },
    )
    assert player_response.status_code == 201
    player = player_response.json()

    roster_response = authenticated_client.post(
        "/seasons-rosters",
        json={
            "season_id": season["id"],
            "player_id": player["id"],
            "jersey_number": 12,
        },
    )
    assert roster_response.status_code == 201
    roster = roster_response.json()

    response = authenticated_client.post(
        "/app/games/new",
        data={
            "season_id": str(season["id"]),
            "game_date": "08/28/2026",
            "opponent_team_id": str(opponent.id),
            "venue_type": "HOME",
            "opponent_score": "",
            "notes": "Integration test",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    game = db_session.scalar(
        select(Game).order_by(Game.id.desc())
    )

    assert game is not None

    return game, roster


def test_add_game_html_creates_draft(authenticated_client, db_session):
    game, _ = _setup_game_with_roster(
        authenticated_client,
        db_session,
    )

    assert game.status == GameStatus.DRAFT
    assert game.game_date.isoformat() == "2026-08-28"
    assert game.notes == "Integration test"


def test_game_stats_page_loads_roster(authenticated_client, db_session):
    game, _ = _setup_game_with_roster(
        authenticated_client,
        db_session,
    )

    response = authenticated_client.get(
        f"/app/games/{game.id}/stats"
    )

    assert response.status_code == 200
    assert "Test Player" in response.text
    assert "#12" in response.text
    assert "Save Draft" in response.text


def test_save_game_stats_draft_creates_stats(
    authenticated_client,
    db_session,
):
    game, roster = _setup_game_with_roster(
        authenticated_client,
        db_session,
    )

    roster_id = roster["id"]

    response = authenticated_client.post(
        f"/app/games/{game.id}/stats",
        data={
            "roster_ids": str(roster_id),
            f"participation_{roster_id}": "PLAYED",
            f"three_point_attempts_{roster_id}": "3",
            f"three_point_makes_{roster_id}": "1",
            f"two_point_attempts_{roster_id}": "5",
            f"two_point_makes_{roster_id}": "2",
            f"free_throw_attempts_{roster_id}": "2",
            f"free_throw_makes_{roster_id}": "1",
            f"turnovers_{roster_id}": "1",
            f"assists_{roster_id}": "3",
            f"offensive_rebounds_{roster_id}": "1",
            f"defensive_rebounds_{roster_id}": "4",
            f"steals_{roster_id}": "2",
            f"deflections_{roster_id}": "1",
            f"personal_fouls_{roster_id}": "2",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    stats = db_session.scalar(
        select(PlayerGameStats).where(
            PlayerGameStats.game_id == game.id,
            PlayerGameStats.season_roster_id == roster_id,
        )
    )

    assert stats is not None
    assert stats.three_point_attempts == 3
    assert stats.three_point_makes == 1
    assert stats.assists == 3

    db_session.refresh(game)
    assert game.status == GameStatus.DRAFT

def _stats_payload(
    roster_id: int,
    *,
    participation: str = "PLAYED",
    three_pa: int = 0,
    three_pm: int = 0,
    assists: int = 0,
) -> dict[str, str]:
    return {
        "roster_ids": str(roster_id),
        f"participation_{roster_id}": participation,
        f"three_point_attempts_{roster_id}": str(three_pa),
        f"three_point_makes_{roster_id}": str(three_pm),
        f"two_point_attempts_{roster_id}": "0",
        f"two_point_makes_{roster_id}": "0",
        f"free_throw_attempts_{roster_id}": "0",
        f"free_throw_makes_{roster_id}": "0",
        f"turnovers_{roster_id}": "0",
        f"assists_{roster_id}": str(assists),
        f"offensive_rebounds_{roster_id}": "0",
        f"defensive_rebounds_{roster_id}": "0",
        f"steals_{roster_id}": "0",
        f"deflections_{roster_id}": "0",
        f"personal_fouls_{roster_id}": "0",
    }

def test_save_game_stats_draft_updates_existing_row(
    authenticated_client,
    db_session,
):
    game, roster = _setup_game_with_roster(
        authenticated_client,
        db_session,
    )

    roster_id = roster["id"]

    first_response = authenticated_client.post(
        f"/app/games/{game.id}/stats",
        data=_stats_payload(
            roster_id,
            three_pa=3,
            three_pm=1,
            assists=2,
        ),
        follow_redirects=False,
    )

    assert first_response.status_code == 303

    second_response = authenticated_client.post(
        f"/app/games/{game.id}/stats",
        data=_stats_payload(
            roster_id,
            three_pa=6,
            three_pm=2,
            assists=5,
        ),
        follow_redirects=False,
    )

    assert second_response.status_code == 303

    rows = list(
        db_session.scalars(
            select(PlayerGameStats).where(
                PlayerGameStats.game_id == game.id,
                PlayerGameStats.season_roster_id == roster_id,
            )
        ).all()
    )

    assert len(rows) == 1
    assert rows[0].three_point_attempts == 6
    assert rows[0].three_point_makes == 2
    assert rows[0].assists == 5


def test_save_game_stats_draft_allows_dnp_with_zero_stats(
    authenticated_client,
    db_session,
):
    game, roster = _setup_game_with_roster(
        authenticated_client,
        db_session,
    )

    roster_id = roster["id"]

    response = authenticated_client.post(
        f"/app/games/{game.id}/stats",
        data=_stats_payload(
            roster_id,
            participation="DID_NOT_PLAY",
        ),
        follow_redirects=False,
    )

    assert response.status_code == 303

    stats = db_session.scalar(
        select(PlayerGameStats).where(
            PlayerGameStats.game_id == game.id,
            PlayerGameStats.season_roster_id == roster_id,
        )
    )

    assert stats is not None
    assert stats.participation_status.value == "DID_NOT_PLAY"
    assert stats.three_point_attempts == 0
    assert stats.assists == 0

def test_invalid_stats_submission_does_not_partially_save(
    authenticated_client,
    db_session,
):
    game, first_roster = _setup_game_with_roster(
        authenticated_client,
        db_session,
    )

    first_roster_id = first_roster["id"]

    # Establish valid saved data first.
    response = authenticated_client.post(
        f"/app/games/{game.id}/stats",
        data=_stats_payload(
            first_roster_id,
            three_pa=4,
            three_pm=2,
            assists=3,
        ),
        follow_redirects=False,
    )

    assert response.status_code == 303

    # Add a second player to the same seasons.
    player_response = authenticated_client.post(
        "/players",
        json={
            "full_name": "Second Test Player",
        },
    )
    assert player_response.status_code == 201

    second_player = player_response.json()

    roster_response = authenticated_client.post(
        "/seasons-rosters",
        json={
            "season_id": game.season_id,
            "player_id": second_player["id"],
            "jersey_number": 20,
        },
    )
    assert roster_response.status_code == 201

    second_roster_id = roster_response.json()["id"]

    # First row contains changed valid data.
    # Second row is invalid because 3PM > 3PA.
    first_data = _stats_payload(
        first_roster_id,
        three_pa=10,
        three_pm=5,
        assists=8,
    )

    second_data = _stats_payload(
        second_roster_id,
        three_pa=2,
        three_pm=4,
    )

    combined_data = {
        key: value
        for key, value in first_data.items()
        if key != "roster_ids"
    }

    combined_data.update(
        {
            key: value
            for key, value in second_data.items()
            if key != "roster_ids"
        }
    )

    combined_data["roster_ids"] = [
        str(first_roster_id),
        str(second_roster_id),
    ]

    response = authenticated_client.post(
        f"/app/games/{game.id}/stats",
        data=combined_data,
        follow_redirects=False,
    )

    assert response.status_code == 422

    db_session.expire_all()

    first_stats = db_session.scalar(
        select(PlayerGameStats).where(
            PlayerGameStats.game_id == game.id,
            PlayerGameStats.season_roster_id == first_roster_id,
        )
    )

    second_stats = db_session.scalar(
        select(PlayerGameStats).where(
            PlayerGameStats.game_id == game.id,
            PlayerGameStats.season_roster_id == second_roster_id,
        )
    )

    # Original saved values must remain unchanged.
    assert first_stats is not None
    assert first_stats.three_point_attempts == 4
    assert first_stats.three_point_makes == 2
    assert first_stats.assists == 3

    # Invalid second row must not have been created.
    assert second_stats is None

def test_finalize_game_successfully(
    authenticated_client,
    db_session,
):
    game, roster = _setup_game_with_roster(
        authenticated_client,
        db_session,
    )

    roster_id = roster["id"]

    data = _stats_payload(
        roster_id,
        three_pa=4,
        three_pm=2,
        assists=3,
    )
    data["action"] = "finalize"
    data["opponent_score"] = "60"

    response = authenticated_client.post(
        f"/app/games/{game.id}/stats",
        data=data,
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].endswith(
        "?finalized=1"
    )

    db_session.expire_all()

    saved_game = db_session.get(
        Game,
        game.id,
    )

    stats = db_session.scalar(
        select(PlayerGameStats).where(
            PlayerGameStats.game_id == game.id,
            PlayerGameStats.season_roster_id == roster_id,
        )
    )

    assert saved_game.status == GameStatus.COMPLETED
    assert saved_game.opponent_score == 60

    assert stats is not None
    assert stats.participation_status.value == "PLAYED"
    assert stats.three_point_attempts == 4
    assert stats.three_point_makes == 2
    assert stats.assists == 3

    page_response = authenticated_client.get(
        f"/app/games/{game.id}/stats?finalized=1"
    )

    assert page_response.status_code == 200
    assert "Game finalized successfully." in page_response.text
    assert "COMPLETED" in page_response.text
    assert "Save Changes" in page_response.text


def test_finalize_game_rejects_missing_opponent_score(
    authenticated_client,
    db_session,
):
    game, roster = _setup_game_with_roster(
        authenticated_client,
        db_session,
    )

    roster_id = roster["id"]

    data = _stats_payload(
        roster_id,
        three_pa=3,
        three_pm=1,
    )
    data["action"] = "finalize"
    data["opponent_score"] = ""

    response = authenticated_client.post(
        f"/app/games/{game.id}/stats",
        data=data,
        follow_redirects=False,
    )

    assert response.status_code == 422
    assert (
        "Completed game requires an opponent score"
        in response.text
    )

    db_session.expire_all()

    saved_game = db_session.get(
        Game,
        game.id,
    )

    stats = db_session.scalar(
        select(PlayerGameStats).where(
            PlayerGameStats.game_id == game.id,
        )
    )

    assert saved_game.status == GameStatus.DRAFT
    assert saved_game.opponent_score is None
    assert stats is None


def test_finalize_game_rejects_no_stats(
    authenticated_client,
    db_session,
):
    game, _ = _setup_game_with_roster(
        authenticated_client,
        db_session,
    )

    response = authenticated_client.post(
        f"/app/games/{game.id}/stats",
        data={
            "action": "finalize",
            "opponent_score": "55",
        },
        follow_redirects=False,
    )

    assert response.status_code == 422
    assert (
        "Completed game requires at least one "
        "player game stats row"
        in response.text
    )

    db_session.expire_all()

    saved_game = db_session.get(
        Game,
        game.id,
    )

    assert saved_game.status == GameStatus.DRAFT
    assert saved_game.opponent_score is None


def test_finalize_game_rejects_dnp_only_stats(
    authenticated_client,
    db_session,
):
    game, roster = _setup_game_with_roster(
        authenticated_client,
        db_session,
    )

    roster_id = roster["id"]

    data = _stats_payload(
        roster_id,
        participation="DID_NOT_PLAY",
    )
    data["action"] = "finalize"
    data["opponent_score"] = "50"

    response = authenticated_client.post(
        f"/app/games/{game.id}/stats",
        data=data,
        follow_redirects=False,
    )

    assert response.status_code == 422
    assert (
        "Completed game requires at least one PLAYED "
        "player game stats row"
        in response.text
    )

    db_session.expire_all()

    saved_game = db_session.get(
        Game,
        game.id,
    )

    stats = db_session.scalar(
        select(PlayerGameStats).where(
            PlayerGameStats.game_id == game.id,
        )
    )

    assert saved_game.status == GameStatus.DRAFT
    assert saved_game.opponent_score is None
    assert stats is None


def test_finalize_game_rejects_future_game(
    authenticated_client,
    db_session,
):
    game, roster = _setup_game_with_roster(
        authenticated_client,
        db_session,
    )

    game.game_date = (
        date.today()
        + timedelta(days=1)
    )
    db_session.commit()

    roster_id = roster["id"]

    data = _stats_payload(
        roster_id,
        three_pa=2,
        three_pm=1,
    )
    data["action"] = "finalize"
    data["opponent_score"] = "65"

    response = authenticated_client.post(
        f"/app/games/{game.id}/stats",
        data=data,
        follow_redirects=False,
    )

    assert response.status_code == 422
    assert (
        "Future-dated game cannot be completed"
        in response.text
    )

    db_session.expire_all()

    saved_game = db_session.get(
        Game,
        game.id,
    )

    stats = db_session.scalar(
        select(PlayerGameStats).where(
            PlayerGameStats.game_id == game.id,
        )
    )

    assert saved_game.status == GameStatus.DRAFT
    assert saved_game.opponent_score is None
    assert stats is None


def test_finalize_game_rejects_invalid_stats(
    authenticated_client,
    db_session,
):
    game, roster = _setup_game_with_roster(
        authenticated_client,
        db_session,
    )

    roster_id = roster["id"]

    data = _stats_payload(
        roster_id,
        three_pa=2,
        three_pm=4,
    )
    data["action"] = "finalize"
    data["opponent_score"] = "60"

    response = authenticated_client.post(
        f"/app/games/{game.id}/stats",
        data=data,
        follow_redirects=False,
    )

    assert response.status_code == 422

    db_session.expire_all()

    saved_game = db_session.get(
        Game,
        game.id,
    )

    stats = db_session.scalar(
        select(PlayerGameStats).where(
            PlayerGameStats.game_id == game.id,
        )
    )

    assert saved_game.status == GameStatus.DRAFT
    assert saved_game.opponent_score is None
    assert stats is None


def test_completed_game_allows_valid_stats_edit(
    authenticated_client,
    db_session,
):
    game, roster = _setup_game_with_roster(
        authenticated_client,
        db_session,
    )

    roster_id = roster["id"]

    finalize_data = _stats_payload(
        roster_id,
        three_pa=4,
        three_pm=2,
        assists=2,
    )
    finalize_data["action"] = "finalize"
    finalize_data["opponent_score"] = "70"

    finalize_response = authenticated_client.post(
        f"/app/games/{game.id}/stats",
        data=finalize_data,
        follow_redirects=False,
    )

    assert finalize_response.status_code == 303

    edit_data = _stats_payload(
        roster_id,
        three_pa=6,
        three_pm=3,
        assists=7,
    )
    edit_data["action"] = "save"
    edit_data["opponent_score"] = "70"

    edit_response = authenticated_client.post(
        f"/app/games/{game.id}/stats",
        data=edit_data,
        follow_redirects=False,
    )

    assert edit_response.status_code == 303
    assert edit_response.headers["location"].endswith(
        "?saved=1"
    )

    db_session.expire_all()

    saved_game = db_session.get(
        Game,
        game.id,
    )

    rows = list(
        db_session.scalars(
            select(PlayerGameStats).where(
                PlayerGameStats.game_id == game.id,
            )
        ).all()
    )

    assert saved_game.status == GameStatus.COMPLETED
    assert saved_game.opponent_score == 70

    assert len(rows) == 1
    assert rows[0].three_point_attempts == 6
    assert rows[0].three_point_makes == 3
    assert rows[0].assists == 7


def test_completed_game_rejects_edit_that_removes_last_played_player(
    authenticated_client,
    db_session,
):
    game, roster = _setup_game_with_roster(
        authenticated_client,
        db_session,
    )

    roster_id = roster["id"]

    finalize_data = _stats_payload(
        roster_id,
        three_pa=4,
        three_pm=2,
        assists=3,
    )
    finalize_data["action"] = "finalize"
    finalize_data["opponent_score"] = "68"

    finalize_response = authenticated_client.post(
        f"/app/games/{game.id}/stats",
        data=finalize_data,
        follow_redirects=False,
    )

    assert finalize_response.status_code == 303

    invalid_edit = _stats_payload(
        roster_id,
        participation="DID_NOT_PLAY",
    )
    invalid_edit["action"] = "save"
    invalid_edit["opponent_score"] = "68"

    response = authenticated_client.post(
        f"/app/games/{game.id}/stats",
        data=invalid_edit,
        follow_redirects=False,
    )

    assert response.status_code == 422
    assert (
        "Completed game requires at least one PLAYED "
        "player game stats row"
        in response.text
    )

    db_session.expire_all()

    saved_game = db_session.get(
        Game,
        game.id,
    )

    stats = db_session.scalar(
        select(PlayerGameStats).where(
            PlayerGameStats.game_id == game.id,
            PlayerGameStats.season_roster_id == roster_id,
        )
    )

    assert saved_game.status == GameStatus.COMPLETED
    assert saved_game.opponent_score == 68

    assert stats is not None
    assert stats.participation_status.value == "PLAYED"
    assert stats.three_point_attempts == 4
    assert stats.three_point_makes == 2
    assert stats.assists == 3


def test_failed_finalization_rolls_back_stats_and_game_changes(
    authenticated_client,
    db_session,
):
    game, roster = _setup_game_with_roster(
        authenticated_client,
        db_session,
    )

    roster_id = roster["id"]

    # Save an existing valid draft state first.
    baseline_data = _stats_payload(
        roster_id,
        three_pa=4,
        three_pm=2,
        assists=3,
    )
    baseline_data["action"] = "save"
    baseline_data["opponent_score"] = "40"

    baseline_response = authenticated_client.post(
        f"/app/games/{game.id}/stats",
        data=baseline_data,
        follow_redirects=False,
    )

    assert baseline_response.status_code == 303

    # Attempt to change both Game and stats while finalizing.
    # This must fail because every player would be DNP.
    failed_data = _stats_payload(
        roster_id,
        participation="DID_NOT_PLAY",
    )
    failed_data["action"] = "finalize"
    failed_data["opponent_score"] = "75"

    response = authenticated_client.post(
        f"/app/games/{game.id}/stats",
        data=failed_data,
        follow_redirects=False,
    )

    assert response.status_code == 422

    db_session.expire_all()

    saved_game = db_session.get(
        Game,
        game.id,
    )

    stats = db_session.scalar(
        select(PlayerGameStats).where(
            PlayerGameStats.game_id == game.id,
            PlayerGameStats.season_roster_id == roster_id,
        )
    )

    # Game changes must have rolled back.
    assert saved_game.status == GameStatus.DRAFT
    assert saved_game.opponent_score == 40

    # Stats changes must also have rolled back.
    assert stats is not None
    assert stats.participation_status.value == "PLAYED"
    assert stats.three_point_attempts == 4
    assert stats.three_point_makes == 2
    assert stats.assists == 3