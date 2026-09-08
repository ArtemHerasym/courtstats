from fastapi import (
    APIRouter,
    Depends,
    Form,
    Request,
)
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
)
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    require_html_csrf,
    require_html_user,
)
from app.core.dates import (
    DateValidationError,
    parse_optional_date,
)
from app.core.templates import templates
from app.database.dependencies import get_db
from app.models.season import SeasonStatus
from app.models.season_roster import RosterStatus
from app.schemas.player import (
    PlayerCreate,
    PlayerUpdate,
)
from app.schemas.season import SeasonUpdate
from app.schemas.season_roster import (
    SeasonRosterCreate,
    SeasonRosterUpdate,
)
from app.services.external_game import (
    ExternalGameNotFoundError,
    get_external_game,
)
from app.services.player import (
    PlayerNotFoundError,
    create_player,
    get_player,
    search_players,
    update_player,
)
from app.services.season import (
    SeasonNameConflictError,
    SeasonNotFoundError,
    create_season_for_team_name,
    get_season,
    list_seasons,
    update_season,
)
from app.services.season_roster import (
    SeasonRosterJerseyConflictError,
    SeasonRosterMembershipConflictError,
    SeasonRosterNotFoundError,
    SeasonRosterRemovalBlockedError,
    create_season_roster,
    get_season_roster,
    list_season_rosters_for_season,
    remove_season_roster,
    update_season_roster,
)
from app.services.team import TeamNameConflictError


router = APIRouter(
    tags=["management-pages"],
    include_in_schema=False,
    dependencies=[
        Depends(require_html_user),
    ],
)


PLAYER_RETURN_CONTEXTS = {
    "season_setup",
    "roster",
    "external_game",
}


def _first_validation_message(
    exc: ValidationError,
) -> str:
    message = exc.errors()[0]["msg"]

    if message.startswith("Value error, "):
        message = message.removeprefix(
            "Value error, "
        )

    return message


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


def _normalize_return_context(
    value: str | None,
) -> str | None:
    if value in PLAYER_RETURN_CONTEXTS:
        return value

    return None


# =========================================================
# Seasons
# =========================================================


def _render_season_form(
    request: Request,
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
):
    return _render_season_form(
        request,
    )


@router.post(
    "/app/seasons/new",
    dependencies=[
        Depends(require_html_csrf),
    ],
)
def create_season_page(
    request: Request,
    team_name: str = Form(""),
    name: str = Form(""),
    start_date: str = Form(""),
    end_date: str = Form(""),
    db: Session = Depends(get_db),
):
    values = {
        "team_name": team_name,
        "name": name,
        "start_date": start_date,
        "end_date": end_date,
    }

    errors: dict[str, str] = {}

    try:
        parsed_start_date = parse_optional_date(
            start_date,
            field_name="Start date",
        )
    except DateValidationError as exc:
        parsed_start_date = None
        errors["start_date"] = str(exc)

    try:
        parsed_end_date = parse_optional_date(
            end_date,
            field_name="End date",
        )
    except DateValidationError as exc:
        parsed_end_date = None
        errors["end_date"] = str(exc)

    if errors:
        return _render_season_form(
            request,
            errors=errors,
            values=values,
            status_code=422,
        )

    try:
        season = create_season_for_team_name(
            db,
            team_name=team_name,
            season_name=name,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
        )

    except ValidationError as exc:
        errors["form"] = (
            _first_validation_message(exc)
        )

    except (
        SeasonNameConflictError,
        TeamNameConflictError,
        ValueError,
    ) as exc:
        errors["form"] = str(exc)

    if errors:
        return _render_season_form(
            request,
            errors=errors,
            values=values,
            status_code=422,
        )

    return RedirectResponse(
        url=(
            f"/app/seasons/"
            f"{season.id}/setup-roster"
        ),
        status_code=303,
    )


@router.get(
    "/app/seasons/{season_id}/setup-roster",
    response_class=HTMLResponse,
)
def season_setup_roster_page(
    request: Request,
    season_id: int,
    db: Session = Depends(get_db),
):
    try:
        season = get_season(
            db,
            season_id,
        )

        roster_entries = (
            list_season_rosters_for_season(
                db,
                season_id,
            )
        )

    except SeasonNotFoundError:
        return HTMLResponse(
            content="Season not found.",
            status_code=404,
        )

    return templates.TemplateResponse(
        request=request,
        name="seasons/setup_roster.html",
        context={
            "season": season,
            "roster_entries": roster_entries,
        },
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
        "name": name,
        "start_date": start_date,
        "end_date": end_date,
        "status": status,
    }

    errors: dict[str, str] = {}

    try:
        parsed_start_date = parse_optional_date(
            start_date,
            field_name="Start date",
        )
    except DateValidationError as exc:
        parsed_start_date = None
        errors["start_date"] = str(exc)

    try:
        parsed_end_date = parse_optional_date(
            end_date,
            field_name="End date",
        )
    except DateValidationError as exc:
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
            season=season,
            errors=errors,
            values=values,
            status_code=422,
        )

    try:
        update_data = SeasonUpdate(
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
    return_context: str | None = None,
    season_id: int | None = None,
    external_game_id: int | None = None,
    errors: dict[str, str] | None = None,
    values: dict[str, str] | None = None,
    status_code: int = 200,
):
    return templates.TemplateResponse(
        request=request,
        name="players/form.html",
        context={
            "player": player,
            "return_context": return_context,
            "season_id": season_id,
            "external_game_id": (
                external_game_id
            ),
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
    return_context: str | None = None,
    season_id: int | None = None,
    external_game_id: int | None = None,
    db: Session = Depends(get_db),
):
    normalized_context = (
        _normalize_return_context(
            return_context
        )
    )

    if season_id is not None:
        try:
            get_season(
                db,
                season_id,
            )
        except SeasonNotFoundError:
            return HTMLResponse(
                content="Season not found.",
                status_code=404,
            )

    if (
        normalized_context
        == "season_setup"
        and season_id is None
    ):
        normalized_context = None

    if (
        normalized_context
        == "external_game"
    ):
        if external_game_id is None:
            normalized_context = None

        else:
            try:
                get_external_game(
                    db,
                    external_game_id,
                )
            except ExternalGameNotFoundError:
                return HTMLResponse(
                    content=(
                        "External game "
                        "not found."
                    ),
                    status_code=404,
                )

    else:
        external_game_id = None

    return _render_player_form(
        request,
        return_context=normalized_context,
        season_id=season_id,
        external_game_id=external_game_id,
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
    return_context: str = Form(""),
    season_id: str = Form(""),
    external_game_id: str = Form(""),
    db: Session = Depends(get_db),
):
    normalized_context = (
        _normalize_return_context(
            return_context
        )
    )

    parsed_season_id: int | None = None
    parsed_external_game_id: int | None = None

    errors: dict[str, str] = {}

    if (
        normalized_context
        in {
            "season_setup",
            "roster",
        }
        and season_id.strip()
    ):
        try:
            parsed_season_id = int(
                season_id
            )

            get_season(
                db,
                parsed_season_id,
            )

        except (
            ValueError,
            SeasonNotFoundError,
        ):
            errors["form"] = (
                "Season context is invalid."
            )

    if (
        normalized_context
        == "season_setup"
        and parsed_season_id is None
    ):
        errors["form"] = (
            "Season context is required."
        )

    if (
        normalized_context
        == "external_game"
    ):
        if not external_game_id.strip():
            errors["form"] = (
                "External Game context "
                "is required."
            )

        else:
            try:
                parsed_external_game_id = int(
                    external_game_id
                )

                get_external_game(
                    db,
                    parsed_external_game_id,
                )

            except (
                ValueError,
                ExternalGameNotFoundError,
            ):
                errors["form"] = (
                    "External Game context "
                    "is invalid."
                )

    values = {
        "full_name": full_name,
        "display_name": display_name,
    }

    if not errors:
        try:
            player_data = PlayerCreate(
                full_name=full_name,
                display_name=(
                    display_name.strip()
                    or None
                ),
            )

            player = create_player(
                db,
                player_data,
            )

        except ValidationError as exc:
            errors["form"] = (
                _first_validation_message(
                    exc
                )
            )

    if errors:
        return _render_player_form(
            request,
            return_context=normalized_context,
            season_id=parsed_season_id,
            external_game_id=(
                parsed_external_game_id
            ),
            errors=errors,
            values=values,
            status_code=422,
        )

    if (
        normalized_context
        == "external_game"
    ):
        return RedirectResponse(
            url=(
                "/app/external-games/"
                f"{parsed_external_game_id}"
                "/players?"
                f"new_player_id={player.id}"
            ),
            status_code=303,
        )

    if normalized_context in {
        "season_setup",
        "roster",
    }:
        url = (
            "/app/roster/new?"
            f"new_player_id={player.id}"
        )

        if parsed_season_id is not None:
            url += (
                "&season_id="
                f"{parsed_season_id}"
            )

        url += (
            "&return_context="
            f"{normalized_context}"
        )

        return RedirectResponse(
            url=url,
            status_code=303,
        )

    return RedirectResponse(
        url="/app/players",
        status_code=303,
    )


@router.get(
    "/app/players/search",
)
def search_players_page(
    q: str = "",
    db: Session = Depends(get_db),
):
    players = search_players(
        db,
        q,
    )[:20]

    return JSONResponse(
        content=[
            {
                "id": player.id,
                "full_name": player.full_name,
                "display_name": (
                    player.display_name
                ),
            }
            for player in players
        ]
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
    selected_season=None,
    selected_player_id: int | None = None,
    return_context: str | None = None,
    errors: dict[str, str] | None = None,
    values: dict[str, str] | None = None,
    status_code: int = 200,
):
    values = values or {}

    if (
        selected_season is None
        and selected_season_id is not None
    ):
        try:
            selected_season = get_season(
                db,
                selected_season_id,
            )
        except SeasonNotFoundError:
            selected_season = None

    if (
        selected_player_id is None
        and values.get("player_id")
    ):
        try:
            selected_player_id = int(
                values["player_id"]
            )
        except ValueError:
            selected_player_id = None

    selected_player = None

    if selected_player_id is not None:
        try:
            selected_player = get_player(
                db,
                selected_player_id,
            )
        except PlayerNotFoundError:
            selected_player = None

    return templates.TemplateResponse(
        request=request,
        name="players/roster_form.html",
        context={
            "roster": roster,
            "seasons": list_seasons(db),
            "roster_statuses": list(
                RosterStatus
            ),
            "selected_season_id": (
                selected_season_id
            ),
            "selected_season": (
                selected_season
            ),
            "selected_player": (
                selected_player
            ),
            "return_context": (
                return_context
            ),
            "errors": errors or {},
            "values": values,
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
    return_context: str | None = None,
    new_player_id: int | None = None,
    db: Session = Depends(get_db),
):
    normalized_context = (
        _normalize_return_context(
            return_context
        )
    )

    selected_season = None

    if season_id is not None:
        try:
            selected_season = get_season(
                db,
                season_id,
            )
        except SeasonNotFoundError:
            return HTMLResponse(
                content="Season not found.",
                status_code=404,
            )

    if new_player_id is not None:
        try:
            get_player(
                db,
                new_player_id,
            )
        except PlayerNotFoundError:
            return HTMLResponse(
                content="Player not found.",
                status_code=404,
            )

    return _render_roster_form(
        request,
        db,
        selected_season_id=season_id,
        selected_season=selected_season,
        selected_player_id=new_player_id,
        return_context=normalized_context,
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
    return_context: str = Form(""),
    db: Session = Depends(get_db),
):
    normalized_context = (
        _normalize_return_context(
            return_context
        )
    )

    values = {
        "season_id": season_id,
        "player_id": player_id,
        "jersey_number": jersey_number,
        "position": position,
        "grade_level": grade_level,
        "status": status,
        "return_context": (
            normalized_context
            or ""
        ),
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
            "Please select or create a player."
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
            selected_player_id=(
                parsed_player_id
                if parsed_player_id
                else None
            ),
            return_context=normalized_context,
            errors=errors,
            values=values,
            status_code=422,
        )

    try:
        roster_data = SeasonRosterCreate(
            season_id=parsed_season_id,
            player_id=parsed_player_id,
            jersey_number=parsed_jersey,
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
            selected_player_id=(
                parsed_player_id
            ),
            return_context=normalized_context,
            errors=errors,
            values=values,
            status_code=422,
        )

    if normalized_context == "season_setup":
        return RedirectResponse(
            url=(
                f"/app/seasons/"
                f"{parsed_season_id}/"
                "setup-roster"
            ),
            status_code=303,
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
        selected_season=roster.season,
        selected_player_id=roster.player_id,
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
        "jersey_number": jersey_number,
        "position": position,
        "grade_level": grade_level,
        "status": status,
    }

    errors: dict[str, str] = {}

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
                roster.season_id
            ),
            selected_season=roster.season,
            selected_player_id=roster.player_id,
            errors=errors,
            values=values,
            status_code=422,
        )

    try:
        update_data = SeasonRosterUpdate(
            jersey_number=parsed_jersey,
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
                roster.season_id
            ),
            selected_season=roster.season,
            selected_player_id=roster.player_id,
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


@router.post(
    "/app/roster/{roster_id}/remove",
    dependencies=[
        Depends(require_html_csrf),
    ],
)
def remove_roster_entry_page(
    roster_id: int,
    db: Session = Depends(get_db),
):
    try:
        roster = get_season_roster(
            db,
            roster_id,
        )

        season_id = roster.season_id

        remove_season_roster(
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

    except SeasonRosterRemovalBlockedError:
        return RedirectResponse(
            url=(
                "/app/roster?"
                f"season_id={season_id}"
                "&remove_error=history"
            ),
            status_code=303,
        )

    return RedirectResponse(
        url=(
            "/app/roster?"
            f"season_id={season_id}"
            "&removed=1"
        ),
        status_code=303,
    )