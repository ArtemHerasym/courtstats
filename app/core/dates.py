import re
from datetime import date, datetime


GAME_DATE_PATTERN = re.compile(r"^\d{2}/\d{2}/\d{4}$")


class GameDateValidationError(ValueError):
    pass


def parse_game_date(value: str) -> date:
    value = value.strip()

    if not value:
        raise GameDateValidationError(
            "Game date is required."
        )

    if GAME_DATE_PATTERN.fullmatch(value) is None:
        raise GameDateValidationError(
            "Game date must use exactly MM/DD/YYYY."
        )

    try:
        return datetime.strptime(
            value,
            "%m/%d/%Y",
        ).date()
    except ValueError as exc:
        raise GameDateValidationError(
            "Game date is not a valid calendar date."
        ) from exc