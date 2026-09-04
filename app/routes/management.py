from datetime import date

from fastapi import (
    APIRouter,
    Depends,
    Form,
    Request,
)
from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
)
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    require_html_csrf,
    require_html_user,
)
from app.core.templates import templates
from app.database.dependencies import get_db
from app.models.season import SeasonStatus
from app.models.season_roster import RosterStatus
from app.schemas.player import (
    PlayerCreate,
    PlayerUpdate,
)
from app.schemas.season import (
    SeasonCreate,
    SeasonUpdate,
)
from app.schemas.season_roster import (
    SeasonRosterCreate,
    SeasonRosterUpdate,
)
from app.services.player import (
    PlayerNotFoundError,
    create_player,
    get_player,
    list_players,
    update_player,
)
from app.services.season import (
    SeasonNameConflictError,
    SeasonNotFoundError,
    create_season,
    get_season,
    list_seasons,
    update_season,
)
from app.services.season_roster import (
    SeasonRosterJerseyConflictError,
    SeasonRosterMembershipConflictError,
    SeasonRosterNotFoundError,
    create_season_roster,
    get_season_roster,
    update_season_roster,
)
from app.services.team import list_teams


router = APIRouter(
    tags=["management-pages"],
    include_in_schema=False,
    dependencies=[
        Depends(require_html_user),
    ],
)


def _first_validation_message(
    exc: ValidationError,
) -> str:
    message = exc.errors()[0]["msg"]

    if message.startswith("Value error, "):
        message = message.removeprefix(
            "Value error, "
        )

    return message


def _parse_optional_date(
    value: str,
) -> date | None:
    value = value.strip()

    if not value:
        return None

    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            "Please enter a valid date."
        ) from exc


def _parse_optional_jersey(
    value: str,
) -> int | None:
    value = value.strip()

    if not value:
        return None

    try:
        jersey_number = int(value)
    except ValueError as exc:
        raise ValueError(
            "Jersey number must be an integer."
        ) from exc

    if jersey_number < 0:
        raise ValueError(
            "Jersey number cannot be negative."
        )

    return jersey_number


# =========================================================
# Seasons
# =========================================================


def _render_season_form(
    request: Request,
    db: Session,
    *,
    season=None,
    errors: dict[str, str] | None = None,
    values: dict[str, str] | None = None,
    status_code: int = 200,
):
    return templates.TemplateResponse(
        request=request,
        name="seasons/form.html",
        context={
            "season": season,
            "teams": list_teams(db),
            "season_statuses": list(
                SeasonStatus
            ),
            "errors": errors or {},
            "values": values or {},
        },
        status_code=status_code,
    )


@router.get(
    "/app/seasons/new",
    response_class=HTMLResponse,
)
def new_season_page(
    request: Request,
    db: Session = Depends(get_db),
):
    return _render_season_form(
        request,
        db,
    )


@router.post(
    "/app/seasons/new",
    dependencies=[
        Depends(require_html_csrf),
    ],
)
def create_season_page(
    request: Request,
    team_id: str = Form(""),
    name: str = Form(""),
    start_date: str = Form(""),
    end_date: str = Form(""),
    db: Session = Depends(get_db),
):
    values = {
        "team_id": team_id,
        "name": name,
        "start_date": start_date,
        "end_date": end_date,
    }

    errors: dict[str, str] = {}

    try:
        parsed_team_id = int(team_id)
    except ValueError:
        parsed_team_id = 0
        errors["team_id"] = (
            "Please select a valid team."
        )

    try:
        parsed_start_date = (
            _parse_optional_date(
                start_date
            )
        )
    except ValueError as exc:
        parsed_start_date = None
        errors["start_date"] = str(exc)

    try:
        parsed_end_date = (
            _parse_optional_date(
                end_date
            )
        )
    except ValueError as exc:
        parsed_end_date = None
        errors["end_date"] = str(exc)

    if errors:
        return _render_season_form(
            request,
            db,
            errors=errors,
            values=values,
            status_code=422,
        )

    try:
        season_data = SeasonCreate(
            team_id=parsed_team_id,
            name=name,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
        )

        season = create_season(
            db,
            season_data,
        )

    except ValidationError as exc:
        errors["form"] = (
            _first_validation_message(exc)
        )

    except SeasonNameConflictError as exc:
        errors["form"] = str(exc)

    except Exception as exc:
        errors["form"] = str(exc)

    if errors:
        return _render_season_form(
            request,
            db,
            errors=errors,
            values=values,
            status_code=422,
        )

    return RedirectResponse(
        url=(
            f"/app/seasons/"
            f"{season.id}/dashboard"
        ),
        status_code=303,
    )


@router.get(
    "/app/seasons/{season_id}/edit",
    response_class=HTMLResponse,
)
def edit_season_page(
    request: Request,
    season_id: int,
    db: Session = Depends(get_db),
):
    try:
        season = get_season(
            db,
            season_id,
        )
    except SeasonNotFoundError:
        return HTMLResponse(
            content="Season not found.",
            status_code=404,
        )

    return _render_season_form(
        request,
        db,
        season=season,
    )


@router.post(
    "/app/seasons/{season_id}/edit",
    dependencies=[
        Depends(require_html_csrf),
    ],
)
def update_season_page(
    request: Request,
    season_id: int,
    team_id: str = Form(""),
    name: str = Form(""),
    start_date: str = Form(""),
    end_date: str = Form(""),
    status: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        season = get_season(
            db,
            season_id,
        )
    except SeasonNotFoundError:
        return HTMLResponse(
            content="Season not found.",
            status_code=404,
        )

    values = {
        "team_id": team_id,
        "name": name,
        "start_date": start_date,
        "end_date": end_date,
        "status": status,
    }

    errors: dict[str, str] = {}

    try:
        parsed_team_id = int(team_id)
    except ValueError:
        parsed_team_id = season.team_id
        errors["team_id"] = (
            "Please select a valid team."
        )

    try:
        parsed_start_date = (
            _parse_optional_date(
                start_date
            )
        )
    except ValueError as exc:
        parsed_start_date = None
        errors["start_date"] = str(exc)

    try:
        parsed_end_date = (
            _parse_optional_date(
                end_date
            )
        )
    except ValueError as exc:
        parsed_end_date = None
        errors["end_date"] = str(exc)

    try:
        parsed_status = SeasonStatus(
            status
        )
    except ValueError:
        parsed_status = season.status
        errors["status"] = (
            "Please select a valid status."
        )

    if errors:
        return _render_season_form(
            request,
            db,
            season=season,
            errors=errors,
            values=values,
            status_code=422,
        )

    try:
        update_data = SeasonUpdate(
            team_id=parsed_team_id,
            name=name,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            status=parsed_status,
        )

        update_season(
            db,
            season_id,
            update_data,
        )

    except ValidationError as exc:
        errors["form"] = (
            _first_validation_message(exc)
        )

    except (
        SeasonNameConflictError,
        ValueError,
    ) as exc:
        errors["form"] = str(exc)

    if errors:
        return _render_season_form(
            request,
            db,
            season=season,
            errors=errors,
            values=values,
            status_code=422,
        )

    return RedirectResponse(
        url="/app/seasons",
        status_code=303,
    )


# =========================================================
# Players
# =========================================================


def _render_player_form(
    request: Request,
    *,
    player=None,
    errors: dict[str, str] | None = None,
    values: dict[str, str] | None = None,
    status_code: int = 200,
):
    return templates.TemplateResponse(
        request=request,
        name="players/form.html",
        context={
            "player": player,
            "errors": errors or {},
            "values": values or {},
        },
        status_code=status_code,
    )


@router.get(
    "/app/players/new",
    response_class=HTMLResponse,
)
def new_player_page(
    request: Request,
):
    return _render_player_form(
        request,
    )


@router.post(
    "/app/players/new",
    dependencies=[
        Depends(require_html_csrf),
    ],
)
def create_player_page(
    request: Request,
    full_name: str = Form(""),
    display_name: str = Form(""),
    db: Session = Depends(get_db),
):
    values = {
        "full_name": full_name,
        "display_name": display_name,
    }

    errors: dict[str, str] = {}

    try:
        player_data = PlayerCreate(
            full_name=full_name,
            display_name=(
                display_name.strip()
                or None
            ),
        )

        create_player(
            db,
            player_data,
        )

    except ValidationError as exc:
        errors["form"] = (
            _first_validation_message(exc)
        )

    if errors:
        return _render_player_form(
            request,
            errors=errors,
            values=values,
            status_code=422,
        )

    return RedirectResponse(
        url="/app/players",
        status_code=303,
    )


@router.get(
    "/app/players/{player_id}/edit",
    response_class=HTMLResponse,
)
def edit_player_page(
    request: Request,
    player_id: int,
    db: Session = Depends(get_db),
):
    try:
        player = get_player(
            db,
            player_id,
        )
    except PlayerNotFoundError:
        return HTMLResponse(
            content="Player not found.",
            status_code=404,
        )

    return _render_player_form(
        request,
        player=player,
    )


@router.post(
    "/app/players/{player_id}/edit",
    dependencies=[
        Depends(require_html_csrf),
    ],
)
def update_player_page(
    request: Request,
    player_id: int,
    full_name: str = Form(""),
    display_name: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        player = get_player(
            db,
            player_id,
        )
    except PlayerNotFoundError:
        return HTMLResponse(
            content="Player not found.",
            status_code=404,
        )

    values = {
        "full_name": full_name,
        "display_name": display_name,
    }

    errors: dict[str, str] = {}

    try:
        update_data = PlayerUpdate(
            full_name=full_name,
            display_name=(
                display_name.strip()
                or None
            ),
        )

        update_player(
            db,
            player_id,
            update_data,
        )

    except ValidationError as exc:
        errors["form"] = (
            _first_validation_message(exc)
        )

    except ValueError as exc:
        errors["form"] = str(exc)

    if errors:
        return _render_player_form(
            request,
            player=player,
            errors=errors,
            values=values,
            status_code=422,
        )

    return RedirectResponse(
        url="/app/players",
        status_code=303,
    )


# =========================================================
# Roster
# =========================================================


def _render_roster_form(
    request: Request,
    db: Session,
    *,
    roster=None,
    selected_season_id: int | None = None,
    errors: dict[str, str] | None = None,
    values: dict[str, str] | None = None,
    status_code: int = 200,
):
    return templates.TemplateResponse(
        request=request,
        name="players/roster_form.html",
        context={
            "roster": roster,
            "seasons": list_seasons(db),
            "players": list_players(db),
            "roster_statuses": list(
                RosterStatus
            ),
            "selected_season_id": (
                selected_season_id
            ),
            "errors": errors or {},
            "values": values or {},
        },
        status_code=status_code,
    )


@router.get(
    "/app/roster/new",
    response_class=HTMLResponse,
)
def new_roster_entry_page(
    request: Request,
    season_id: int | None = None,
    db: Session = Depends(get_db),
):
    return _render_roster_form(
        request,
        db,
        selected_season_id=season_id,
    )


@router.post(
    "/app/roster/new",
    dependencies=[
        Depends(require_html_csrf),
    ],
)
def create_roster_entry_page(
    request: Request,
    season_id: str = Form(""),
    player_id: str = Form(""),
    jersey_number: str = Form(""),
    position: str = Form(""),
    grade_level: str = Form(""),
    status: str = Form("ACTIVE"),
    db: Session = Depends(get_db),
):
    values = {
        "season_id": season_id,
        "player_id": player_id,
        "jersey_number": jersey_number,
        "position": position,
        "grade_level": grade_level,
        "status": status,
    }

    errors: dict[str, str] = {}

    try:
        parsed_season_id = int(
            season_id
        )
    except ValueError:
        parsed_season_id = 0
        errors["season_id"] = (
            "Please select a valid season."
        )

    try:
        parsed_player_id = int(
            player_id
        )
    except ValueError:
        parsed_player_id = 0
        errors["player_id"] = (
            "Please select a valid player."
        )

    try:
        parsed_jersey = (
            _parse_optional_jersey(
                jersey_number
            )
        )
    except ValueError as exc:
        parsed_jersey = None
        errors["jersey_number"] = str(exc)

    try:
        parsed_status = RosterStatus(
            status
        )
    except ValueError:
        parsed_status = (
            RosterStatus.ACTIVE
        )
        errors["status"] = (
            "Please select a valid status."
        )

    if errors:
        return _render_roster_form(
            request,
            db,
            selected_season_id=(
                parsed_season_id
                if parsed_season_id
                else None
            ),
            errors=errors,
            values=values,
            status_code=422,
        )

    try:
        roster_data = (
            SeasonRosterCreate(
                season_id=(
                    parsed_season_id
                ),
                player_id=(
                    parsed_player_id
                ),
                jersey_number=(
                    parsed_jersey
                ),
                position=(
                    position.strip()
                    or None
                ),
                grade_level=(
                    grade_level.strip()
                    or None
                ),
                status=parsed_status,
            )
        )

        create_season_roster(
            db,
            roster_data,
        )

    except ValidationError as exc:
        errors["form"] = (
            _first_validation_message(exc)
        )

    except (
        SeasonNotFoundError,
        PlayerNotFoundError,
        SeasonRosterMembershipConflictError,
        SeasonRosterJerseyConflictError,
    ) as exc:
        errors["form"] = str(exc)

    if errors:
        return _render_roster_form(
            request,
            db,
            selected_season_id=(
                parsed_season_id
            ),
            errors=errors,
            values=values,
            status_code=422,
        )

    return RedirectResponse(
        url=(
            "/app/roster?"
            f"season_id={parsed_season_id}"
        ),
        status_code=303,
    )


@router.get(
    "/app/roster/{roster_id}/edit",
    response_class=HTMLResponse,
)
def edit_roster_entry_page(
    request: Request,
    roster_id: int,
    db: Session = Depends(get_db),
):
    try:
        roster = get_season_roster(
            db,
            roster_id,
        )
    except SeasonRosterNotFoundError:
        return HTMLResponse(
            content=(
                "Season roster entry "
                "not found."
            ),
            status_code=404,
        )

    return _render_roster_form(
        request,
        db,
        roster=roster,
        selected_season_id=(
            roster.season_id
        ),
    )


@router.post(
    "/app/roster/{roster_id}/edit",
    dependencies=[
        Depends(require_html_csrf),
    ],
)
def update_roster_entry_page(
    request: Request,
    roster_id: int,
    season_id: str = Form(""),
    player_id: str = Form(""),
    jersey_number: str = Form(""),
    position: str = Form(""),
    grade_level: str = Form(""),
    status: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        roster = get_season_roster(
            db,
            roster_id,
        )
    except SeasonRosterNotFoundError:
        return HTMLResponse(
            content=(
                "Season roster entry "
                "not found."
            ),
            status_code=404,
        )

    values = {
        "season_id": season_id,
        "player_id": player_id,
        "jersey_number": jersey_number,
        "position": position,
        "grade_level": grade_level,
        "status": status,
    }

    errors: dict[str, str] = {}

    try:
        parsed_season_id = int(
            season_id
        )
    except ValueError:
        parsed_season_id = (
            roster.season_id
        )
        errors["season_id"] = (
            "Please select a valid season."
        )

    try:
        parsed_player_id = int(
            player_id
        )
    except ValueError:
        parsed_player_id = (
            roster.player_id
        )
        errors["player_id"] = (
            "Please select a valid player."
        )

    try:
        parsed_jersey = (
            _parse_optional_jersey(
                jersey_number
            )
        )
    except ValueError as exc:
        parsed_jersey = (
            roster.jersey_number
        )
        errors["jersey_number"] = str(exc)

    try:
        parsed_status = RosterStatus(
            status
        )
    except ValueError:
        parsed_status = roster.status
        errors["status"] = (
            "Please select a valid status."
        )

    if errors:
        return _render_roster_form(
            request,
            db,
            roster=roster,
            selected_season_id=(
                parsed_season_id
            ),
            errors=errors,
            values=values,
            status_code=422,
        )

    try:
        update_data = (
            SeasonRosterUpdate(
                season_id=(
                    parsed_season_id
                ),
                player_id=(
                    parsed_player_id
                ),
                jersey_number=(
                    parsed_jersey
                ),
                position=(
                    position.strip()
                    or None
                ),
                grade_level=(
                    grade_level.strip()
                    or None
                ),
                status=parsed_status,
            )
        )

        updated_roster = (
            update_season_roster(
                db,
                roster_id,
                update_data,
            )
        )

    except ValidationError as exc:
        errors["form"] = (
            _first_validation_message(exc)
        )

    except (
        SeasonNotFoundError,
        PlayerNotFoundError,
        SeasonRosterMembershipConflictError,
        SeasonRosterJerseyConflictError,
        ValueError,
    ) as exc:
        errors["form"] = str(exc)

    if errors:
        return _render_roster_form(
            request,
            db,
            roster=roster,
            selected_season_id=(
                parsed_season_id
            ),
            errors=errors,
            values=values,
            status_code=422,
        )

    return RedirectResponse(
        url=(
            "/app/roster?"
            f"season_id="
            f"{updated_roster.season_id}"
        ),
        status_code=303,
    )