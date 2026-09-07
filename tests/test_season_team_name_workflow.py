import pytest
from sqlalchemy import func, select

from app.models.season import Season
from app.models.team import Team
from app.schemas.season import (
    SeasonCreate,
)
from app.services.season import (
    SeasonNameConflictError,
    create_season,
    create_season_for_team_name,
)
from app.services.team import (
    find_team_by_name,
)


def test_find_team_by_name_returns_existing_team(
    db_session,
):
    team = Team(
        name="Jordan Christian Preparatory",
    )

    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    found = find_team_by_name(
        db_session,
        "Jordan Christian Preparatory",
    )

    assert found is not None
    assert found.id == team.id


def test_find_team_by_name_is_case_insensitive(
    db_session,
):
    team = Team(
        name="Jordan Christian Preparatory",
    )

    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    found = find_team_by_name(
        db_session,
        "jOrDaN cHrIsTiAn PrEpArAtOrY",
    )

    assert found is not None
    assert found.id == team.id


def test_find_team_by_name_normalizes_outer_whitespace(
    db_session,
):
    team = Team(
        name="Jordan Christian Preparatory",
    )

    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    found = find_team_by_name(
        db_session,
        "  Jordan Christian Preparatory  ",
    )

    assert found is not None
    assert found.id == team.id


def test_find_team_by_name_rejects_blank(
    db_session,
):
    with pytest.raises(
        ValueError,
        match="Team name cannot be blank",
    ):
        find_team_by_name(
            db_session,
            "   ",
        )


def test_create_season_for_team_name_reuses_existing_team(
    db_session,
):
    team = Team(
        name="Jordan Christian Preparatory",
    )

    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    season = create_season_for_team_name(
        db_session,
        team_name=(
            "Jordan Christian Preparatory"
        ),
        season_name="2027-2028",
    )

    assert season.team_id == team.id

    team_count = db_session.scalar(
        select(
            func.count(Team.id)
        )
    )

    assert team_count == 1


def test_create_season_for_team_name_reuses_existing_team_case_insensitively(
    db_session,
):
    team = Team(
        name="Jordan Christian Preparatory",
    )

    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    season = create_season_for_team_name(
        db_session,
        team_name=(
            "JORDAN CHRISTIAN PREPARATORY"
        ),
        season_name="2027-2028",
    )

    assert season.team_id == team.id

    team_count = db_session.scalar(
        select(
            func.count(Team.id)
        )
    )

    assert team_count == 1


def test_create_season_for_team_name_creates_new_team(
    db_session,
):
    season = create_season_for_team_name(
        db_session,
        team_name=(
            "Jordan Christian Preparatory"
        ),
        season_name="2027-2028",
    )

    team = db_session.get(
        Team,
        season.team_id,
    )

    assert team is not None

    assert (
        team.name
        == "Jordan Christian Preparatory"
    )

    assert season.name == "2027-2028"


def test_create_season_for_team_name_normalizes_whitespace(
    db_session,
):
    season = create_season_for_team_name(
        db_session,
        team_name=(
            "  Jordan Christian Preparatory  "
        ),
        season_name="  2027-2028  ",
    )

    team = db_session.get(
        Team,
        season.team_id,
    )

    assert team is not None

    assert (
        team.name
        == "Jordan Christian Preparatory"
    )

    assert season.name == "2027-2028"


def test_create_season_for_team_name_rejects_blank_team_name(
    db_session,
):
    with pytest.raises(
        ValueError,
        match="Team name cannot be blank",
    ):
        create_season_for_team_name(
            db_session,
            team_name="   ",
            season_name="2027-2028",
        )

    team_count = db_session.scalar(
        select(
            func.count(Team.id)
        )
    )

    season_count = db_session.scalar(
        select(
            func.count(Season.id)
        )
    )

    assert team_count == 0
    assert season_count == 0


def test_create_season_for_team_name_preserves_season_uniqueness(
    db_session,
):
    first = create_season_for_team_name(
        db_session,
        team_name=(
            "Jordan Christian Preparatory"
        ),
        season_name="2027-2028",
    )

    with pytest.raises(
        SeasonNameConflictError
    ):
        create_season_for_team_name(
            db_session,
            team_name=(
                "jordan christian preparatory"
            ),
            season_name="2027-2028",
        )

    seasons = list(
        db_session.scalars(
            select(Season)
        ).all()
    )

    assert len(seasons) == 1
    assert seasons[0].id == first.id


def test_create_season_for_team_name_rolls_back_new_team_if_final_commit_fails(
    db_session,
    monkeypatch,
):
    original_commit = db_session.commit

    def failing_commit():
        raise RuntimeError(
            "Simulated final operation failure"
        )

    monkeypatch.setattr(
        db_session,
        "commit",
        failing_commit,
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "Simulated final operation failure"
        ),
    ):
        create_season_for_team_name(
            db_session,
            team_name="Rollback Team",
            season_name="2027-2028",
        )

    # Restore normal commits before inspecting
    # persisted database state.
    monkeypatch.setattr(
        db_session,
        "commit",
        original_commit,
    )

    db_session.expire_all()

    team = find_team_by_name(
        db_session,
        "Rollback Team",
    )

    season_count = db_session.scalar(
        select(
            func.count(Season.id)
        )
    )

    assert team is None
    assert season_count == 0


def test_existing_create_season_service_still_works(
    db_session,
):
    team = Team(
        name="Existing Service Team",
    )

    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    season = create_season(
        db_session,
        SeasonCreate(
            team_id=team.id,
            name="2026-2027",
        ),
    )

    assert season.id is not None
    assert season.team_id == team.id
    assert season.name == "2026-2027"