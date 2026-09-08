from sqlalchemy import select

from app.models.game import Game
from app.models.player import Player
from app.models.season import Season
from app.models.season_roster import (
    RosterStatus,
    SeasonRoster,
)
from app.models.team import Team


def _create_season(
    db_session,
):
    team = Team(
        name="Game Guard Team",
        abbreviation="GGT",
    )

    opponent = Team(
        name="Game Guard Opponent",
        abbreviation="GGO",
    )

    db_session.add_all(
        [
            team,
            opponent,
        ]
    )

    db_session.flush()

    season = Season(
        team_id=team.id,
        name="2034-2035",
    )

    db_session.add(season)
    db_session.commit()

    db_session.refresh(season)
    db_session.refresh(opponent)

    return season, opponent


def _game_form_data(
    season_id: int,
    opponent_id: int,
) -> dict[str, str]:
    return {
        "season_id": str(
            season_id
        ),
        "game_date": "11/15/2034",
        "opponent_team_id": str(
            opponent_id
        ),
        "new_opponent_name": "",
        "new_opponent_abbreviation": "",
        "venue_type": "HOME",
        "opponent_score": "",
        "notes": "",
    }


def test_game_creation_blocked_for_empty_roster(
    authenticated_client,
    db_session,
):
    season, opponent = _create_season(
        db_session,
    )

    response = authenticated_client.post(
        "/app/games/new",
        data=_game_form_data(
            season.id,
            opponent.id,
        ),
        follow_redirects=False,
    )

    assert response.status_code == 422

    assert (
        "This Season has no ACTIVE roster "
        "players."
        in response.text
    )

    games = list(
        db_session.scalars(
            select(Game).where(
                Game.season_id
                == season.id
            )
        ).all()
    )

    assert games == []


def test_game_creation_blocked_for_inactive_only_roster(
    authenticated_client,
    db_session,
):
    season, opponent = _create_season(
        db_session,
    )

    player = Player(
        full_name="Inactive Player",
    )

    db_session.add(player)
    db_session.flush()

    roster = SeasonRoster(
        season_id=season.id,
        player_id=player.id,
        jersey_number=4,
        status=RosterStatus.INACTIVE,
    )

    db_session.add(roster)
    db_session.commit()

    response = authenticated_client.post(
        "/app/games/new",
        data=_game_form_data(
            season.id,
            opponent.id,
        ),
        follow_redirects=False,
    )

    assert response.status_code == 422

    assert (
        "This Season has no ACTIVE roster "
        "players."
        in response.text
    )

    games = list(
        db_session.scalars(
            select(Game).where(
                Game.season_id
                == season.id
            )
        ).all()
    )

    assert games == []


def test_game_creation_allowed_with_active_roster(
    authenticated_client,
    db_session,
):
    season, opponent = _create_season(
        db_session,
    )

    player = Player(
        full_name="Active Player",
    )

    db_session.add(player)
    db_session.flush()

    roster = SeasonRoster(
        season_id=season.id,
        player_id=player.id,
        jersey_number=10,
        status=RosterStatus.ACTIVE,
    )

    db_session.add(roster)
    db_session.commit()

    response = authenticated_client.post(
        "/app/games/new",
        data=_game_form_data(
            season.id,
            opponent.id,
        ),
        follow_redirects=False,
    )

    assert response.status_code == 303

    game = db_session.scalar(
        select(Game).where(
            Game.season_id
            == season.id
        )
    )

    assert game is not None

    assert (
        response.headers["location"]
        == f"/app/games/{game.id}/stats"
    )


def test_empty_roster_guard_does_not_create_new_opponent(
    authenticated_client,
    db_session,
):
    season, _ = _create_season(
        db_session,
    )

    response = authenticated_client.post(
        "/app/games/new",
        data={
            "season_id": str(
                season.id
            ),
            "game_date": "12/01/2034",
            "opponent_team_id": "new",
            "new_opponent_name": (
                "Should Not Be Created"
            ),
            "new_opponent_abbreviation": (
                "SNBC"
            ),
            "venue_type": "AWAY",
            "opponent_score": "",
            "notes": "",
        },
        follow_redirects=False,
    )

    assert response.status_code == 422

    new_opponent = db_session.scalar(
        select(Team).where(
            Team.name
            == "Should Not Be Created"
        )
    )

    assert new_opponent is None

    games = list(
        db_session.scalars(
            select(Game).where(
                Game.season_id
                == season.id
            )
        ).all()
    )

    assert games == []