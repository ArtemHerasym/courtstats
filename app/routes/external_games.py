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
from app.core.dates import (
    GameDateValidationError,
    parse_game_date,
)
from app.core.templates import templates
from app.database.dependencies import get_db
from app.models.game import (
    GameStatus,
    VenueType,
)
from app.models.player_game_stats import (
    ParticipationStatus,
)
from app.schemas.external_game import (
    ExternalGameCreate,
)
from app.schemas.external_game_player_stats import (
    ExternalGamePlayerStatsCreate,
)
from app.schemas.team import TeamCreate
from app.services.external_game import (
    ExternalGameNotFoundError,
    ExternalGameOpponentNotFoundError,
    create_external_game,
    get_external_game,
    list_external_games,
)
from app.services.external_game_player_stats import (
    ExternalGamePlayerStatsConflictError,
    RAW_STAT_FIELDS,
    list_external_game_player_stats,
)
from app.services.external_game_workflow import (
    finalize_external_game_with_stats,
    save_external_game_stats,
    sync_external_game_players,
)
from app.services.player import (
    PlayerNotFoundError,
    list_players,
)
from app.services.team import (
    TeamNameConflictError,
    create_team,
    list_teams,
)


router = APIRouter(
    tags=["external-games-pages"],
    include_in_schema=False,
    dependencies=[
        Depends(require_html_user),
    ],
)


def render_new_external_game_form(
    request: Request,
    db: Session,
    *,
    errors: dict[str, str] | None = None,
    form_values: dict[str, str] | None = None,
    status_code: int = 200,
):
    return templates.TemplateResponse(
        request=request,
        name="external_games/new.html",
        context={
            "teams": list_teams(db),
            "venue_types": list(VenueType),
            "errors": errors or {},
            "form_values": form_values or {},
        },
        status_code=status_code,
    )


def render_external_game_players_form(
    request: Request,
    db: Session,
    external_game,
    *,
    selected_player_ids: set[int] | None = None,
    error: str | None = None,
    status_code: int = 200,
):
    if selected_player_ids is None:
        existing_stats = (
            list_external_game_player_stats(
                db,
                external_game.id,
            )
        )

        selected_player_ids = {
            stats.player_id
            for stats in existing_stats
        }

    return templates.TemplateResponse(
        request=request,
        name=(
            "external_games/"
            "select_players.html"
        ),
        context={
            "external_game": external_game,
            "players": list_players(db),
            "selected_player_ids": (
                selected_player_ids
            ),
            "error": error,
        },
        status_code=status_code,
    )


def render_external_game_stats_form(
    request: Request,
    db: Session,
    external_game,
    *,
    row_errors: dict[int, str] | None = None,
    form_values: dict[str, str] | None = None,
    saved: bool = False,
    status_code: int = 200,
):
    stats_rows = (
        list_external_game_player_stats(
            db,
            external_game.id,
        )
    )

    return templates.TemplateResponse(
        request=request,
        name=(
            "external_games/"
            "stats_entry.html"
        ),
        context={
            "external_game": external_game,
            "stats_rows": stats_rows,
            "participation_statuses": list(
                ParticipationStatus
            ),
            "row_errors": row_errors or {},
            "form_values": form_values or {},
            "saved": saved,
        },
        status_code=status_code,
    )


@router.get(
    "/app/external-games",
    response_class=HTMLResponse,
)
def external_games_page(
    request: Request,
    db: Session = Depends(get_db),
):
    external_games = list_external_games(db)

    return templates.TemplateResponse(
        request=request,
        name="external_games/index.html",
        context={
            "external_games": external_games,
        },
    )


@router.get(
    "/app/external-games/new",
    response_class=HTMLResponse,
)
def new_external_game_page(
    request: Request,
    db: Session = Depends(get_db),
):
    return render_new_external_game_form(
        request,
        db,
    )


@router.post(
    "/app/external-games/new",
    response_class=HTMLResponse,
    dependencies=[
        Depends(require_html_csrf),
    ],
)
def create_external_game_page(
    request: Request,
    name: str = Form(""),
    game_date: str = Form(""),
    opponent_team_id: str = Form(""),
    new_opponent_name: str = Form(""),
    new_opponent_abbreviation: str = Form(""),
    venue_type: str = Form(""),
    opponent_score: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    errors: dict[str, str] = {}

    form_values = {
        "name": name,
        "game_date": game_date,
        "opponent_team_id": opponent_team_id,
        "new_opponent_name": (
            new_opponent_name
        ),
        "new_opponent_abbreviation": (
            new_opponent_abbreviation
        ),
        "venue_type": venue_type,
        "opponent_score": opponent_score,
        "notes": notes,
    }

    if not name.strip():
        errors["name"] = (
            "External game name is required."
        )

    try:
        parsed_game_date = parse_game_date(
            game_date
        )
    except GameDateValidationError as exc:
        errors["game_date"] = str(exc)
        parsed_game_date = None

    try:
        parsed_venue_type = VenueType(
            venue_type
        )
    except ValueError:
        errors["venue_type"] = (
            "Please select a valid venue."
        )
        parsed_venue_type = None

    parsed_opponent_score = None

    if opponent_score.strip():
        try:
            parsed_opponent_score = int(
                opponent_score
            )

            if parsed_opponent_score < 0:
                raise ValueError

        except ValueError:
            errors["opponent_score"] = (
                "Opponent score must be "
                "a nonnegative integer."
            )

    parsed_opponent_team_id = None
    new_team_data = None

    if opponent_team_id == "new":
        try:
            new_team_data = TeamCreate(
                name=new_opponent_name,
                abbreviation=(
                    new_opponent_abbreviation
                    or None
                ),
            )

        except ValidationError as exc:
            message = (
                exc.errors()[0]["msg"]
            )

            if message.startswith(
                "Value error, "
            ):
                message = (
                    message.removeprefix(
                        "Value error, "
                    )
                )

            errors[
                "new_opponent_name"
            ] = message

    else:
        try:
            parsed_opponent_team_id = int(
                opponent_team_id
            )

        except ValueError:
            errors["opponent_team_id"] = (
                "Please select an opponent."
            )

    if errors:
        return render_new_external_game_form(
            request,
            db,
            errors=errors,
            form_values=form_values,
            status_code=422,
        )

    if new_team_data is not None:
        try:
            opponent = create_team(
                db,
                new_team_data,
            )

            parsed_opponent_team_id = (
                opponent.id
            )

        except TeamNameConflictError as exc:
            errors[
                "new_opponent_name"
            ] = str(exc)

            return (
                render_new_external_game_form(
                    request,
                    db,
                    errors=errors,
                    form_values=form_values,
                    status_code=409,
                )
            )

    try:
        external_game = create_external_game(
            db,
            ExternalGameCreate(
                name=name.strip(),
                opponent_team_id=(
                    parsed_opponent_team_id
                ),
                game_date=parsed_game_date,
                venue_type=(
                    parsed_venue_type
                ),
                status=GameStatus.DRAFT,
                opponent_score=(
                    parsed_opponent_score
                ),
                notes=(
                    notes.strip()
                    or None
                ),
            ),
        )

    except ValidationError as exc:
        message = (
            exc.errors()[0]["msg"]
        )

        if message.startswith(
            "Value error, "
        ):
            message = message.removeprefix(
                "Value error, "
            )

        errors["form"] = message

    except (
        ExternalGameOpponentNotFoundError
    ) as exc:
        errors["opponent_team_id"] = (
            str(exc)
        )

    except ValueError as exc:
        errors["form"] = str(exc)

    if errors:
        return render_new_external_game_form(
            request,
            db,
            errors=errors,
            form_values=form_values,
            status_code=422,
        )

    return RedirectResponse(
        url=(
            "/app/external-games/"
            f"{external_game.id}/players"
        ),
        status_code=303,
    )


@router.get(
    "/app/external-games/"
    "{external_game_id}/players",
    response_class=HTMLResponse,
)
def external_game_players_page(
    request: Request,
    external_game_id: int,
    db: Session = Depends(get_db),
):
    try:
        external_game = get_external_game(
            db,
            external_game_id,
        )

    except ExternalGameNotFoundError:
        return HTMLResponse(
            content="External game not found.",
            status_code=404,
        )

    return render_external_game_players_form(
        request,
        db,
        external_game,
    )


@router.post(
    "/app/external-games/"
    "{external_game_id}/players",
    response_class=HTMLResponse,
    dependencies=[
        Depends(require_html_csrf),
    ],
)
async def save_external_game_players_page(
    request: Request,
    external_game_id: int,
    db: Session = Depends(get_db),
):
    try:
        external_game = get_external_game(
            db,
            external_game_id,
        )

    except ExternalGameNotFoundError:
        return HTMLResponse(
            content="External game not found.",
            status_code=404,
        )

    form = await request.form()

    raw_player_ids = form.getlist(
        "player_ids"
    )

    try:
        player_ids = [
            int(raw_player_id)
            for raw_player_id
            in raw_player_ids
        ]

    except ValueError:
        return (
            render_external_game_players_form(
                request,
                db,
                external_game,
                error=(
                    "Invalid player selection."
                ),
                status_code=422,
            )
        )

    try:
        sync_external_game_players(
            db,
            external_game.id,
            player_ids,
        )

    except (
        ExternalGamePlayerStatsConflictError,
        PlayerNotFoundError,
        ValueError,
    ) as exc:
        return (
            render_external_game_players_form(
                request,
                db,
                external_game,
                selected_player_ids=set(
                    player_ids
                ),
                error=str(exc),
                status_code=422,
            )
        )

    return RedirectResponse(
        url=(
            "/app/external-games/"
            f"{external_game.id}/stats"
        ),
        status_code=303,
    )


@router.get(
    "/app/external-games/"
    "{external_game_id}/stats",
    response_class=HTMLResponse,
)
def external_game_stats_page(
    request: Request,
    external_game_id: int,
    db: Session = Depends(get_db),
):
    try:
        external_game = get_external_game(
            db,
            external_game_id,
        )

    except ExternalGameNotFoundError:
        return HTMLResponse(
            content="External game not found.",
            status_code=404,
        )

    return render_external_game_stats_form(
        request,
        db,
        external_game,
        saved=(
                request.query_params.get("saved")
                == "1"
                or
                request.query_params.get("finalized")
                == "1"
        ),
    )


@router.post(
    "/app/external-games/"
    "{external_game_id}/stats",
    response_class=HTMLResponse,
    dependencies=[
        Depends(require_html_csrf),
    ],
)
async def save_external_game_stats_page(
    request: Request,
    external_game_id: int,
    db: Session = Depends(get_db),
):
    try:
        external_game = get_external_game(
            db,
            external_game_id,
        )

    except ExternalGameNotFoundError:
        return HTMLResponse(
            content="External game not found.",
            status_code=404,
        )

    form = await request.form()

    action = str(
        form.get("action", "save")
    )

    raw_player_ids = form.getlist(
        "player_ids"
    )

    row_errors: dict[int, str] = {}

    form_values = {
        key: str(value)
        for key, value
        in form.multi_items()
        if key != "player_ids"
    }

    raw_opponent_score = str(
        form.get(
            "opponent_score",
            "",
        )
    ).strip()

    opponent_score: int | None = None

    if raw_opponent_score:
        try:
            opponent_score = int(
                raw_opponent_score
            )

            if opponent_score < 0:
                raise ValueError

        except ValueError:
            row_errors[0] = (
                "Opponent score must be "
                "a nonnegative integer."
            )

    stats_rows: list[
        ExternalGamePlayerStatsCreate
    ] = []

    for raw_player_id in raw_player_ids:
        player_id = 0

        try:
            player_id = int(
                raw_player_id
            )

            participation = (
                ParticipationStatus(
                    str(
                        form.get(
                            (
                                "participation_"
                                f"{player_id}"
                            ),
                            "",
                        )
                    )
                )
            )

            parsed_stats: dict[
                str,
                int,
            ] = {}

            for field in RAW_STAT_FIELDS:
                raw_value = str(
                    form.get(
                        f"{field}_{player_id}",
                        "",
                    )
                ).strip()

                if raw_value == "":
                    raise ValueError(
                        (
                            "All statistic fields "
                            "must contain a value."
                        )
                    )

                value = int(raw_value)

                if value < 0:
                    raise ValueError(
                        (
                            "Statistics cannot "
                            "be negative."
                        )
                    )

                parsed_stats[field] = value

            stats_rows.append(
                ExternalGamePlayerStatsCreate(
                    external_game_id=(
                        external_game.id
                    ),
                    player_id=player_id,
                    participation_status=(
                        participation
                    ),
                    **parsed_stats,
                )
            )

        except (
            ValueError,
            ValidationError,
        ) as exc:
            if isinstance(
                exc,
                ValidationError,
            ):
                message = (
                    exc.errors()[0]["msg"]
                )

                if message.startswith(
                    "Value error, "
                ):
                    message = (
                        message.removeprefix(
                            "Value error, "
                        )
                    )

            else:
                message = str(exc)

            row_errors[
                player_id
            ] = message

    if row_errors:
        return (
            render_external_game_stats_form(
                request,
                db,
                external_game,
                row_errors=row_errors,
                form_values=form_values,
                status_code=422,
            )
        )

    if action not in {
        "save",
        "finalize",
    }:
        return (
            render_external_game_stats_form(
                request,
                db,
                external_game,
                row_errors={
                    0: (
                        "Invalid external "
                        "game action."
                    )
                },
                form_values=form_values,
                status_code=422,
            )
        )

    try:
        if action == "finalize":
            finalize_external_game_with_stats(
                db,
                external_game.id,
                stats_rows,
                opponent_score,
            )

        else:
            save_external_game_stats(
                db,
                external_game.id,
                stats_rows,
                opponent_score,
            )

    except (
        ExternalGamePlayerStatsConflictError,
        PlayerNotFoundError,
        ValueError,
    ) as exc:
        return (
            render_external_game_stats_form(
                request,
                db,
                external_game,
                row_errors={
                    0: str(exc)
                },
                form_values=form_values,
                status_code=422,
            )
        )

    query_flag = (
        "finalized=1"
        if action == "finalize"
        else "saved=1"
    )

    return RedirectResponse(
        url=(
            "/app/external-games/"
            f"{external_game.id}/stats"
            f"?{query_flag}"
        ),
        status_code=303,
    )