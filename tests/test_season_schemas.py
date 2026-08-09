from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.season import SeasonStatus
from app.schemas.season import SeasonCreate, SeasonRead, SeasonUpdate

def test_season_create_valid_minimal():
    season = SeasonCreate(
        team_id=1,
        name="2026-27 JCP Basketball",
    )

    assert season.team_id == 1
    assert season.name == "2026-27 JCP Basketball"
    assert season.start_date is None
    assert season.end_date is None

def test_season_create_valid_with_dates_and_trimmed_name():
    season = SeasonCreate(
        team_id=1,
        name="  2026-27 JCP Basketball  ",
        start_date=date(2026, 10, 1),
        end_date=date(2027, 3, 1),
    )

    assert season.name == "2026-27 JCP Basketball"
    assert season.start_date == date(2026, 10, 1)
    assert season.end_date == date(2027, 3, 1)

def test_season_create_rejects_blank_name():
    with pytest.raises(ValidationError):
        SeasonCreate(
            team_id=1,
            name="   ",
        )

def test_season_create_rejects_invalid_date_range():
    with pytest.raises(ValidationError):
        SeasonCreate(
            team_id=1,
            name="2026-27 JCP Basketball",
            start_date=date(2027, 3, 1),
            end_date=date(2026, 10, 1),
        )

def test_season_update_allows_partial_update():
    update = SeasonUpdate(
        status=SeasonStatus.ACTIVE,
    )

    assert update.status == SeasonStatus.ACTIVE
    assert update.name is None
    assert update.start_date is None
    assert update.end_date is None

def test_season_update_rejects_blank_name():
    with pytest.raises(ValidationError):
        SeasonUpdate(
            name="   ",
        )

def test_season_update_rejects_invalid_status():
    with pytest.raises(ValidationError):
        SeasonUpdate(
            status="INVALID",
        )

def test_season_update_rejects_invalid_date_range():
    with pytest.raises(ValidationError):
        SeasonUpdate(
            start_date=date(2027, 3, 1),
            end_date=date(2026, 10, 1),
        )

def test_season_update_exclude_unset():
    update = SeasonUpdate(
        status=SeasonStatus.ACTIVE,
    )

    assert update.model_dump(exclude_unset=True) == {
        "status": SeasonStatus.ACTIVE,
    }

def test_season_read_from_attributes():
    class FakeSeason:
        id = 1
        team_id = 2
        name = "2026-27 JCP Basketball"
        start_date = date(2026, 10, 1)
        end_date = date(2027, 3, 1)
        status = SeasonStatus.ACTIVE
        created_at = datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc)
        updated_at = datetime(2026, 8, 8, 13, 0, tzinfo=timezone.utc)

    season = SeasonRead.model_validate(FakeSeason())

    assert season.id == 1
    assert season.team_id == 2
    assert season.status == SeasonStatus.ACTIVE
    assert season.name == "2026-27 JCP Basketball"