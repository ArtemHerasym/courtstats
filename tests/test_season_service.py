from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.season import SeasonStatus
from app.models.team import Team
from app.schemas.season import SeasonCreate, SeasonUpdate
from app.services.season import (
    SeasonNameConflictError,
    SeasonNotFoundError,
    create_season,
    get_season,
    list_seasons,
    update_season,
)

def test_create_season(db_session):
    team = Team(
        name="Jordan Christian Preparatory",
        abbreviation="JCP",
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    season_data = SeasonCreate(
        team_id=team.id,
        name="2026-27",
        start_date=date(2026, 10, 1),
        end_date=date(2027, 3, 31),
    )

    season = create_season(db_session, season_data)

    assert season.id is not None
    assert season.team_id == team.id
    assert season.name == "2026-27"
    assert season.start_date == date(2026, 10, 1)
    assert season.end_date == date(2027, 3, 31)
    assert season.status == SeasonStatus.SETUP

def test_create_season_rejects_duplicate_name_for_same_team(db_session):
    team = Team(name="Jordan Christian Preparatory", abbreviation="JCP")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    first_season = SeasonCreate(
        team_id=team.id,
        name="2026-27",
    )

    duplicate_season = SeasonCreate(
        team_id=team.id,
        name="2026-27",
    )

    create_season(db_session, first_season)

    with pytest.raises(SeasonNameConflictError):
        create_season(db_session, duplicate_season)

def test_create_season_allows_same_name_for_different_teams(db_session):
    first_team = Team(name="Jordan Christian Preparatory", abbreviation="JCP")
    second_team = Team(name="Another Team", abbreviation="AT")

    db_session.add_all([first_team, second_team])
    db_session.commit()
    db_session.refresh(first_team)
    db_session.refresh(second_team)

    first_season = create_season(
        db_session,
        SeasonCreate(
            team_id=first_team.id,
            name="2026-27",
        ),
    )

    second_season = create_season(
        db_session,
        SeasonCreate(
            team_id=second_team.id,
            name="2026-27",
        ),
    )

    assert first_season.name == second_season.name
    assert first_season.team_id != second_season.team_id

def test_get_season_returns_existing_season(db_session):
    team = Team(name="Jordan Christian Preparatory", abbreviation="JCP")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    created_season = create_season(
        db_session,
        SeasonCreate(
            team_id=team.id,
            name="2026-27",
        ),
    )

    found_season = get_season(db_session, created_season.id)

    assert found_season.id == created_season.id
    assert found_season.name == "2026-27"

def test_get_season_raises_not_found_for_missing_id(db_session):
    with pytest.raises(SeasonNotFoundError):
        get_season(db_session, 999999)

def test_list_seasons_returns_seasons_in_id_order(db_session):
    team = Team(name="Jordan Christian Preparatory", abbreviation="JCP")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    first = create_season(
        db_session,
        SeasonCreate(team_id=team.id, name="2025-26"),
    )
    second = create_season(
        db_session,
        SeasonCreate(team_id=team.id, name="2026-27"),
    )

    seasons = list_seasons(db_session)

    assert [season.id for season in seasons] == [first.id, second.id]

def test_update_season_changes_only_provided_fields(db_session):
    team = Team(name="Jordan Christian Preparatory", abbreviation="JCP")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    season = create_season(
        db_session,
        SeasonCreate(
            team_id=team.id,
            name="2026-27",
            start_date=date(2026, 10, 1),
            end_date=date(2027, 3, 31),
        ),
    )

    updated_season = update_season(
        db_session,
        season.id,
        SeasonUpdate(status=SeasonStatus.ACTIVE),
    )

    assert updated_season.status == SeasonStatus.ACTIVE
    assert updated_season.name == "2026-27"
    assert updated_season.start_date == date(2026, 10, 1)
    assert updated_season.end_date == date(2027, 3, 31)
    assert updated_season.team_id == team.id

def test_update_season_raises_not_found_for_missing_id(db_session):
    with pytest.raises(SeasonNotFoundError):
        update_season(
            db_session,
            999999,
            SeasonUpdate(status=SeasonStatus.ACTIVE),
        )

def test_update_season_rejects_duplicate_name_for_same_team(db_session):
    team = Team(name="Jordan Christian Preparatory", abbreviation="JCP")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    create_season(
        db_session,
        SeasonCreate(
            team_id=team.id,
            name="2025-26",
        ),
    )

    second_season = create_season(
        db_session,
        SeasonCreate(
            team_id=team.id,
            name="2026-27",
        ),
    )

    with pytest.raises(SeasonNameConflictError):
        update_season(
            db_session,
            second_season.id,
            SeasonUpdate(name="2025-26"),
        )

def test_update_season_rejects_invalid_final_date_range(db_session):
    team = Team(name="Jordan Christian Preparatory", abbreviation="JCP")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    season = create_season(
        db_session,
        SeasonCreate(
            team_id=team.id,
            name="2026-27",
            start_date=date(2026, 10, 1),
            end_date=date(2027, 3, 31),
        ),
    )

    with pytest.raises(ValueError):
        update_season(
            db_session,
            season.id,
            SeasonUpdate(end_date=date(2026, 9, 1)),
        )

def test_create_season_rolls_back_after_integrity_error(db_session):
    invalid_season = SeasonCreate(
        team_id=999999,
        name="Invalid Season",
    )

    with pytest.raises(IntegrityError):
        create_season(db_session, invalid_season)

    team = Team(
        name="Jordan Christian Preparatory",
        abbreviation="JCP",
    )
    db_session.add(team)
    db_session.commit()

    assert team.id is not None

def test_update_season_rolls_back_after_integrity_error(db_session):
    team = Team(
        name="Jordan Christian Preparatory",
        abbreviation="JCP",
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    season = create_season(
        db_session,
        SeasonCreate(
            team_id=team.id,
            name="2026-27",
        ),
    )

    with pytest.raises(IntegrityError):
        update_season(
            db_session,
            season.id,
            SeasonUpdate(team_id=999999),
        )

    recovered_season = get_season(db_session, season.id)

    assert recovered_season.team_id == team.id

def test_update_season_can_clear_optional_date(db_session):
    team = Team(name="Jordan Christian Preparatory", abbreviation="JCP")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    season = create_season(
        db_session,
        SeasonCreate(
            team_id=team.id,
            name="2026-27",
            start_date=date(2026, 10, 1),
            end_date=date(2027, 3, 31),
        ),
    )

    updated_season = update_season(
        db_session,
        season.id,
        SeasonUpdate(end_date=None),
    )

    assert updated_season.start_date == date(2026, 10, 1)
    assert updated_season.end_date is None