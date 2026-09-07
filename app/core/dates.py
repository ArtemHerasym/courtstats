import re
from datetime import date, datetime


DATE_PATTERN = re.compile(
    r"^\d{2}/\d{2}/\d{4}$"
)


class DateValidationError(ValueError):
    pass


class GameDateValidationError(
    DateValidationError
):
    pass


def parse_required_date(
    value: str,
    *,
    field_name: str = "Date",
) -> date:
    value = value.strip()

    if not value:
        raise DateValidationError(
            f"{field_name} is required."
        )

    if DATE_PATTERN.fullmatch(value) is None:
        raise DateValidationError(
            (
                f"{field_name} must use exactly "
                "MM/DD/YYYY."
            )
        )

    try:
        return datetime.strptime(
            value,
            "%m/%d/%Y",
        ).date()

    except ValueError as exc:
        raise DateValidationError(
            (
                f"{field_name} is not a valid "
                "calendar date."
            )
        ) from exc


def parse_optional_date(
    value: str,
    *,
    field_name: str = "Date",
) -> date | None:
    value = value.strip()

    if not value:
        return None

    return parse_required_date(
        value,
        field_name=field_name,
    )


def parse_game_date(
    value: str,
) -> date:
    try:
        return parse_required_date(
            value,
            field_name="Game date",
        )

    except DateValidationError as exc:
        raise GameDateValidationError(
            str(exc)
        ) from exc