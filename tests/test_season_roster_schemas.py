from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.season_roster import RosterStatus
from app.schemas.season_roster import (
    SeasonRosterCreate,
    SeasonRosterRead,
    SeasonRosterUpdate,
)


def test_season_roster_create_valid_minimal():
    roster = SeasonRosterCreate(
        season_id=1,
        player_id=1,
    )

    assert roster.season_id == 1
    assert roster.player_id == 1
    assert roster.jersey_number is None
    assert roster.position is None
    assert roster.grade_level is None
    assert roster.status == RosterStatus.ACTIVE


def test_season_roster_create_valid_full():
    roster = SeasonRosterCreate(
        season_id=1,
        player_id=2,
        jersey_number=12,
        position="Guard",
        grade_level="Senior",
        status=RosterStatus.INACTIVE,
    )

    assert roster.season_id == 1
    assert roster.player_id == 2
    assert roster.jersey_number == 12
    assert roster.position == "Guard"
    assert roster.grade_level == "Senior"
    assert roster.status == RosterStatus.INACTIVE


def test_season_roster_create_trims_optional_text():
    roster = SeasonRosterCreate(
        season_id=1,
        player_id=1,
        position="  Guard  ",
        grade_level="  Senior  ",
    )

    assert roster.position == "Guard"
    assert roster.grade_level == "Senior"


def test_season_roster_create_rejects_blank_position():
    with pytest.raises(ValidationError):
        SeasonRosterCreate(
            season_id=1,
            player_id=1,
            position="   ",
        )


def test_season_roster_create_rejects_blank_grade_level():
    with pytest.raises(ValidationError):
        SeasonRosterCreate(
            season_id=1,
            player_id=1,
            grade_level="   ",
        )


def test_season_roster_update_allows_partial_update():
    update = SeasonRosterUpdate(
        jersey_number=12,
    )

    assert update.jersey_number == 12
    assert update.position is None
    assert update.grade_level is None
    assert update.status is None


def test_season_roster_update_exclude_unset():
    update = SeasonRosterUpdate(
        jersey_number=12,
    )

    assert update.model_dump(exclude_unset=True) == {
        "jersey_number": 12,
    }


def test_season_roster_update_can_explicitly_clear_optional_field():
    update = SeasonRosterUpdate(
        position=None,
    )

    assert update.model_dump(exclude_unset=True) == {
        "position": None,
    }


def test_season_roster_status_validation():
    roster = SeasonRosterCreate(
        season_id=1,
        player_id=1,
        status="INACTIVE",
    )

    assert roster.status == RosterStatus.INACTIVE

    with pytest.raises(ValidationError):
        SeasonRosterCreate(
            season_id=1,
            player_id=1,
            status="INVALID_STATUS",
        )


def test_season_roster_read_from_attributes():
    class FakeSeasonRoster:
        id = 1
        season_id = 2
        player_id = 3
        jersey_number = 12
        position = "Guard"
        grade_level = "Senior"
        status = RosterStatus.ACTIVE
        created_at = datetime(
            2026,
            8,
            13,
            12,
            0,
            tzinfo=timezone.utc,
        )
        updated_at = datetime(
            2026,
            8,
            13,
            13,
            0,
            tzinfo=timezone.utc,
        )

    roster = SeasonRosterRead.model_validate(FakeSeasonRoster())

    assert roster.id == 1
    assert roster.season_id == 2
    assert roster.player_id == 3
    assert roster.jersey_number == 12
    assert roster.position == "Guard"
    assert roster.grade_level == "Senior"
    assert roster.status == RosterStatus.ACTIVE

def test_season_roster_update_allows_membership_fields():
    update = SeasonRosterUpdate(
        season_id=2,
        player_id=3,
    )

    assert update.season_id == 2
    assert update.player_id == 3

def test_season_roster_update_membership_fields_exclude_unset():
    update = SeasonRosterUpdate(
        player_id=3,
    )

    assert update.model_dump(exclude_unset=True) == {
        "player_id": 3,
    }