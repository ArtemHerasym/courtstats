import pytest

from app.core.dates import (
    GameDateValidationError,
    parse_game_date,
)


def test_parse_game_date():
    parsed = parse_game_date("08/28/2026")

    assert parsed.year == 2026
    assert parsed.month == 8
    assert parsed.day == 28


@pytest.mark.parametrize(
    "value",
    [
        "8/28/2026",
        "08-28-2026",
        "2026/08/28",
        "02/30/2026",
    ],
)
def test_parse_game_date_rejects_invalid_values(value):
    with pytest.raises(GameDateValidationError):
        parse_game_date(value)