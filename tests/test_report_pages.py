from sqlalchemy import select

from app.models.game import Game
from app.models.player_game_stats import PlayerGameStats
from app.models.team import Team


def _setup_game_with_roster(
    authenticated_client,
    db_session,
):
    team = Team(
        name="Jordan Christian Preparatory",
        abbreviation="JCP",
    )

    opponent = Team(
        name="Test Opponent",
        abbreviation="TEST",
    )

    db_session.add_all(
        [team, opponent]
    )
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

    game_response = authenticated_client.post(
        "/app/games/new",
        data={
            "season_id": str(
                season["id"]
            ),
            "game_date": "08/28/2026",
            "opponent_team_id": str(
                opponent.id
            ),
            "venue_type": "HOME",
            "opponent_score": "",
            "notes": "Report test",
        },
        follow_redirects=False,
    )

    assert game_response.status_code == 303

    game = db_session.scalar(
        select(Game).order_by(
            Game.id.desc()
        )
    )

    assert game is not None

    return game, roster


def _stats_payload(
    roster_id: int,
    *,
    participation: str = "PLAYED",
) -> dict[str, str]:
    return {
        "roster_ids": str(roster_id),
        (
            f"participation_{roster_id}"
        ): participation,
        (
            f"three_point_attempts_{roster_id}"
        ): "0",
        (
            f"three_point_makes_{roster_id}"
        ): "0",
        (
            f"two_point_attempts_{roster_id}"
        ): "0",
        (
            f"two_point_makes_{roster_id}"
        ): "0",
        (
            f"free_throw_attempts_{roster_id}"
        ): "0",
        (
            f"free_throw_makes_{roster_id}"
        ): "0",
        (
            f"turnovers_{roster_id}"
        ): "0",
        (
            f"assists_{roster_id}"
        ): "0",
        (
            f"offensive_rebounds_{roster_id}"
        ): "0",
        (
            f"defensive_rebounds_{roster_id}"
        ): "0",
        (
            f"steals_{roster_id}"
        ): "0",
        (
            f"deflections_{roster_id}"
        ): "0",
        (
            f"personal_fouls_{roster_id}"
        ): "0",
    }


def _known_stat_line(
    roster_id: int,
) -> dict[str, str]:
    data = _stats_payload(
        roster_id,
    )

    # 3PT: 2/4 = 6 points
    data[
        f"three_point_attempts_{roster_id}"
    ] = "4"
    data[
        f"three_point_makes_{roster_id}"
    ] = "2"

    # 2PT: 3/6 = 6 points
    data[
        f"two_point_attempts_{roster_id}"
    ] = "6"
    data[
        f"two_point_makes_{roster_id}"
    ] = "3"

    # FT: 3/4 = 3 points
    data[
        f"free_throw_attempts_{roster_id}"
    ] = "4"
    data[
        f"free_throw_makes_{roster_id}"
    ] = "3"

    # Total = 15 points
    data[
        f"turnovers_{roster_id}"
    ] = "2"
    data[
        f"assists_{roster_id}"
    ] = "4"

    data[
        f"offensive_rebounds_{roster_id}"
    ] = "2"
    data[
        f"defensive_rebounds_{roster_id}"
    ] = "3"

    data[
        f"steals_{roster_id}"
    ] = "1"
    data[
        f"deflections_{roster_id}"
    ] = "2"
    data[
        f"personal_fouls_{roster_id}"
    ] = "2"

    return data


def _finalize_known_game(
    authenticated_client,
    game_id: int,
    roster_id: int,
):
    data = _known_stat_line(
        roster_id,
    )

    data["action"] = "finalize"
    data["opponent_score"] = "12"

    response = authenticated_client.post(
        f"/app/games/{game_id}/stats",
        data=data,
        follow_redirects=False,
    )

    assert response.status_code == 303


def _normalize_html(
    html: str,
) -> str:
    return " ".join(
        html.split()
    )


def test_game_report_renders_calculated_values(
    authenticated_client,
    db_session,
):
    game, roster = _setup_game_with_roster(
        authenticated_client,
        db_session,
    )

    roster_id = roster["id"]

    _finalize_known_game(
        authenticated_client,
        game.id,
        roster_id,
    )

    response = authenticated_client.get(
        f"/app/games/{game.id}/report"
    )

    assert response.status_code == 200

    html = _normalize_html(
        response.text
    )

    assert (
        "Jordan Christian Preparatory"
        in html
    )
    assert "Test Opponent" in html

    # 15 - 12 = WIN by 3.
    assert "WIN" in html
    assert "+3" in html

    # Combined shooting:
    # FG = 5/10 = 50%
    # 2PT = 3/6 = 50%
    # 3PT = 2/4 = 50%
    # FT = 3/4 = 75%
    assert "50.0%" in html
    assert "75.0%" in html

    # TS% = 15 /
    # [2 * (10 + .44 * 4)]
    assert "63.8%" in html

    # 4 AST / 2 TO
    assert "2.00" in html

    assert (
            f"/app/season-rosters/"
            f"{roster_id}/profile"
            in html
    )

    # Completed stats page links to report.
    stats_response = authenticated_client.get(
        f"/app/games/{game.id}/stats"
    )

    assert stats_response.status_code == 200

    assert (
        f"/app/games/{game.id}/report"
        in stats_response.text
    )


def test_game_report_returns_404_for_missing_game(
    authenticated_client,
):
    response = authenticated_client.get(
        "/app/games/999999/report"
    )

    assert response.status_code == 404
    assert "Game not found." in response.text


def test_game_report_handles_empty_stats(
    authenticated_client,
    db_session,
):
    game, _ = _setup_game_with_roster(
        authenticated_client,
        db_session,
    )

    response = authenticated_client.get(
        f"/app/games/{game.id}/report"
    )

    assert response.status_code == 200

    assert (
        "Game summary requires an opponent score"
        in response.text
    )

    assert (
        "No player statistics are available "
        "for this game."
        in response.text
    )


def test_player_profile_renders_season_summary_and_game_log(
    authenticated_client,
    db_session,
):
    game, roster = _setup_game_with_roster(
        authenticated_client,
        db_session,
    )

    roster_id = roster["id"]

    _finalize_known_game(
        authenticated_client,
        game.id,
        roster_id,
    )

    response = authenticated_client.get(
        f"/app/seasons-rosters/"
        f"{roster_id}/profile"
    )

    assert response.status_code == 200

    html = _normalize_html(
        response.text
    )

    assert "Test Player" in html
    assert "2026-27" in html

    assert (
        "<span>GP</span> "
        "<strong>1</strong>"
        in html
    )

    assert (
        "<span>PTS</span> "
        "<strong>15</strong>"
        in html
    )

    assert "15.0" in html
    assert "5.0" in html
    assert "4.0" in html

    assert "50.0%" in html
    assert "75.0%" in html
    assert "63.8%" in html
    assert "2.00" in html

    assert "Test Opponent" in html
    assert "WIN" in html

    assert (
        f"/app/games/{game.id}/report"
        in html
    )


def test_player_profile_returns_404_for_missing_roster(
    authenticated_client,
):
    response = authenticated_client.get(
        "/app/seasons-rosters/999999/profile"
    )

    assert response.status_code == 404

    assert (
        "Season roster entry not found."
        in response.text
    )


def test_player_profile_excludes_draft_games(
    authenticated_client,
    db_session,
):
    game, roster = _setup_game_with_roster(
        authenticated_client,
        db_session,
    )

    roster_id = roster["id"]

    # Completed game:
    # 1/1 from 2PT = 2 points.
    completed_data = _stats_payload(
        roster_id,
    )

    completed_data[
        f"two_point_attempts_{roster_id}"
    ] = "1"

    completed_data[
        f"two_point_makes_{roster_id}"
    ] = "1"

    completed_data["action"] = "finalize"
    completed_data["opponent_score"] = "1"

    completed_response = authenticated_client.post(
        f"/app/games/{game.id}/stats",
        data=completed_data,
        follow_redirects=False,
    )

    assert completed_response.status_code == 303

    # Create another opponent/game that remains DRAFT.
    draft_opponent = Team(
        name="Draft Opponent",
        abbreviation="DRAFT",
    )

    db_session.add(
        draft_opponent
    )
    db_session.commit()
    db_session.refresh(
        draft_opponent
    )

    draft_game_response = authenticated_client.post(
        "/app/games/new",
        data={
            "season_id": str(
                game.season_id
            ),
            "game_date": "08/29/2026",
            "opponent_team_id": str(
                draft_opponent.id
            ),
            "venue_type": "AWAY",
            "opponent_score": "",
            "notes": "Must be excluded",
        },
        follow_redirects=False,
    )

    assert draft_game_response.status_code == 303

    draft_game = db_session.scalar(
        select(Game).order_by(
            Game.id.desc()
        )
    )

    assert draft_game is not None
    assert draft_game.id != game.id

    # Save large stats to the DRAFT.
    # They must not affect the profile.
    draft_data = _stats_payload(
        roster_id,
    )

    draft_data[
        f"three_point_attempts_{roster_id}"
    ] = "5"

    draft_data[
        f"three_point_makes_{roster_id}"
    ] = "5"

    draft_data[
        f"assists_{roster_id}"
    ] = "9"

    draft_data["action"] = "save"
    draft_data["opponent_score"] = ""

    draft_save_response = authenticated_client.post(
        f"/app/games/{draft_game.id}/stats",
        data=draft_data,
        follow_redirects=False,
    )

    assert draft_save_response.status_code == 303

    response = authenticated_client.get(
        f"/app/seasons-rosters/"
        f"{roster_id}/profile"
    )

    assert response.status_code == 200

    html = _normalize_html(
        response.text
    )

    # Only the completed game counts.
    assert (
        "<span>GP</span> "
        "<strong>1</strong>"
        in html
    )

    assert (
        "<span>PTS</span> "
        "<strong>2</strong>"
        in html
    )

    # Draft game must not appear in the completed log.
    assert "Draft Opponent" not in html


def test_dnp_does_not_increase_player_games_played(
    authenticated_client,
    db_session,
):
    game, roster = _setup_game_with_roster(
        authenticated_client,
        db_session,
    )

    dnp_roster_id = roster["id"]

    # A second player must PLAY so that the
    # game itself can validly be completed.
    second_player_response = authenticated_client.post(
        "/players",
        json={
            "full_name": "Played Player",
        },
    )

    assert (
        second_player_response.status_code
        == 201
    )

    second_player = (
        second_player_response.json()
    )

    second_roster_response = authenticated_client.post(
        "/seasons-rosters",
        json={
            "season_id": game.season_id,
            "player_id": second_player["id"],
            "jersey_number": 20,
        },
    )

    assert (
        second_roster_response.status_code
        == 201
    )

    played_roster_id = (
        second_roster_response.json()["id"]
    )

    dnp_data = _stats_payload(
        dnp_roster_id,
        participation="DID_NOT_PLAY",
    )

    played_data = _stats_payload(
        played_roster_id,
        participation="PLAYED",
    )

    combined_data = {
        key: value
        for key, value
        in dnp_data.items()
        if key != "roster_ids"
    }

    combined_data.update(
        {
            key: value
            for key, value
            in played_data.items()
            if key != "roster_ids"
        }
    )

    combined_data["roster_ids"] = [
        str(dnp_roster_id),
        str(played_roster_id),
    ]

    combined_data["action"] = "finalize"
    combined_data["opponent_score"] = "0"

    finalize_response = authenticated_client.post(
        f"/app/games/{game.id}/stats",
        data=combined_data,
        follow_redirects=False,
    )

    assert finalize_response.status_code == 303

    response = authenticated_client.get(
        f"/app/seasons-rosters/"
        f"{dnp_roster_id}/profile"
    )

    assert response.status_code == 200

    html = _normalize_html(
        response.text
    )

    # Completed game appears in the log...
    assert "Test Opponent" in html
    assert "DNP" in html

    # ...but does not count as a game played.
    assert (
        "<span>GP</span> "
        "<strong>0</strong>"
        in html
    )


def test_player_profile_handles_no_completed_games(
    authenticated_client,
    db_session,
):
    _, roster = _setup_game_with_roster(
        authenticated_client,
        db_session,
    )

    roster_id = roster["id"]

    response = authenticated_client.get(
        f"/app/seasons-rosters/"
        f"{roster_id}/profile"
    )

    assert response.status_code == 200

    html = _normalize_html(
        response.text
    )

    assert (
        "<span>GP</span> "
        "<strong>0</strong>"
        in html
    )

    assert (
        "No completed games are available "
        "for this player."
        in html
    )