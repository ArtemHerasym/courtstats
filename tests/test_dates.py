from datetime import date

import pytest

from app.core.dates import (
    DateValidationError,
    GameDateValidationError,
    parse_game_date,
    parse_optional_date,
    parse_required_date,
)


def test_parse_game_date():
    parsed = parse_game_date(
        "08/28/2026"
    )

    assert parsed == date(
        2026,
        8,
        28,
    )


@pytest.mark.parametrize(
    "value",
    [
        "8/28/2026",
        "08-28-2026",
        "2026/08/28",
        "02/30/2026",
    ],
)
def test_parse_game_date_rejects_invalid_values(
    value,
):
    with pytest.raises(
        GameDateValidationError
    ):
        parse_game_date(value)


def test_parse_required_date_returns_date():
    parsed = parse_required_date(
        "08/28/2026"
    )

    assert parsed == date(
        2026,
        8,
        28,
    )


def test_parse_required_date_accepts_leap_day():
    parsed = parse_required_date(
        "02/29/2028"
    )

    assert parsed == date(
        2028,
        2,
        29,
    )


@pytest.mark.parametrize(
    "value",
    [
        "02/29/2027",
        "02/31/2026",
        "13/01/2026",
        "08-28-2026",
        "2026/08/28",
        "8/28/2026",
    ],
)
def test_parse_required_date_rejects_invalid_values(
    value,
):
    with pytest.raises(
        DateValidationError
    ):
        parse_required_date(value)


def test_parse_required_date_rejects_blank():
    with pytest.raises(
        DateValidationError,
        match="Date is required",
    ):
        parse_required_date("")


def test_parse_required_date_trims_whitespace():
    parsed = parse_required_date(
        "  08/28/2026  "
    )

    assert parsed == date(
        2026,
        8,
        28,
    )


def test_parse_required_date_uses_custom_field_name():
    with pytest.raises(
        DateValidationError,
        match="Start date is required",
    ):
        parse_required_date(
            "",
            field_name="Start date",
        )


def test_parse_optional_date_returns_none_for_blank():
    assert (
        parse_optional_date("")
        is None
    )


def test_parse_optional_date_returns_none_for_whitespace():
    assert (
        parse_optional_date("   ")
        is None
    )


def test_parse_optional_date_returns_date():
    parsed = parse_optional_date(
        "09/07/2026"
    )

    assert parsed == date(
        2026,
        9,
        7,
    )


def test_parse_optional_date_rejects_invalid_date():
    with pytest.raises(
        DateValidationError
    ):
        parse_optional_date(
            "02/29/2027"
        )


def test_parse_game_date_preserves_game_specific_message():
    with pytest.raises(
        GameDateValidationError,
        match=(
            "Game date must use exactly "
            "MM/DD/YYYY"
        ),
    ):
        parse_game_date(
            "2026-08-28"
        )