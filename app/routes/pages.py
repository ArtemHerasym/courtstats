from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.dates import GameDateValidationError, parse_game_date
from app.core.templates import templates
from app.database.dependencies import get_db
from app.models.game import GameStatus, VenueType
from app.schemas.game import GameCreate
from app.schemas.team import TeamCreate
from app.services.game import (
    GameNotFoundError,
    GameOpponentConflictError,
    OpponentTeamNotFoundError,
    create_game,
    get_game,
)
from app.services.season import (
    SeasonNotFoundError,
    get_season,
    list_seasons,
)
from app.services.team import (
    TeamNameConflictError,
    create_team,
    list_teams,
)
from app.models.player_game_stats import ParticipationStatus
from app.services.player_game_stats import (
    PlayerGameStatsConflictError,
    PlayerGameStatsSeasonMismatchError,
    finalize_game_with_stats,
    list_player_game_stats_for_game,
    save_player_game_stats,
)
from app.services.season_roster import (
    list_season_rosters_for_season,
)
from app.schemas.player_game_stats import PlayerGameStatsCreate



router = APIRouter(
    tags=["pages"],
    include_in_schema=False,
)

def render_new_game_form(
    request: Request,
    db: Session,
    *,
    errors: dict[str, str] | None = None,
    form_values: dict[str, str] | None = None,
    status_code: int = 200,
):
    return templates.TemplateResponse(
        request=request,
        name="games/new.html",
        context={
            "seasons": list_seasons(db),
            "teams": list_teams(db),
            "venue_types": list(VenueType),
            "errors": errors or {},
            "form_values": form_values or {},
        },
        status_code=status_code,
    )


@router.get("/", response_class=HTMLResponse)
def home_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="home.html",
    )


@router.get(
    "/app/games/new",
    response_class=HTMLResponse,
)
def new_game_page(
    request: Request,
    db: Session = Depends(get_db),
):
    return render_new_game_form(
        request,
        db,
    )

@router.post(
    "/app/games/new",
    response_class=HTMLResponse,
)
def create_game_page(
    request: Request,
    season_id: str = Form(""),
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
        "season_id": season_id,
        "game_date": game_date,
        "opponent_team_id": opponent_team_id,
        "new_opponent_name": new_opponent_name,
        "new_opponent_abbreviation": new_opponent_abbreviation,
        "venue_type": venue_type,
        "opponent_score": opponent_score,
        "notes": notes,
    }

    try:
        parsed_season_id = int(season_id)
        get_season(db, parsed_season_id)
    except (ValueError, SeasonNotFoundError):
        errors["season_id"] = "Please select a valid season."
        parsed_season_id = None

    try:
        parsed_game_date = parse_game_date(game_date)
    except GameDateValidationError as exc:
        errors["game_date"] = str(exc)
        parsed_game_date = None

    try:
        parsed_venue_type = VenueType(venue_type)
    except ValueError:
        errors["venue_type"] = "Please select a valid venue."
        parsed_venue_type = None

    parsed_opponent_score = None

    if opponent_score.strip():
        try:
            parsed_opponent_score = int(opponent_score)

            if parsed_opponent_score < 0:
                raise ValueError

        except ValueError:
            errors["opponent_score"] = (
                "Opponent score must be a nonnegative integer."
            )

    parsed_opponent_team_id = None
    new_team_data = None

    if opponent_team_id == "new":
        try:
            new_team_data = TeamCreate(
                name=new_opponent_name,
                abbreviation=new_opponent_abbreviation or None,
            )
        except ValidationError as exc:
            errors["new_opponent_name"] = (
                exc.errors()[0]["msg"]
                .removeprefix("Value error, ")
            )
    else:
        try:
            parsed_opponent_team_id = int(opponent_team_id)
        except ValueError:
            errors["opponent_team_id"] = "Please select an opponent."

    if errors:
        return render_new_game_form(
            request,
            db,
            errors=errors,
            form_values=form_values,
            status_code=422,
        )

    if new_team_data is not None:
        try:
            opponent = create_team(db, new_team_data)
            parsed_opponent_team_id = opponent.id
        except TeamNameConflictError as exc:
            errors["new_opponent_name"] = str(exc)

            return render_new_game_form(
                request,
                db,
                errors=errors,
                form_values=form_values,
                status_code=409,
            )

    try:
        game = create_game(
            db,
            GameCreate(
                season_id=parsed_season_id,
                opponent_team_id=parsed_opponent_team_id,
                game_date=parsed_game_date,
                venue_type=parsed_venue_type,
                status=GameStatus.DRAFT,
                opponent_score=parsed_opponent_score,
                notes=notes.strip() or None,
            ),
        )

    except OpponentTeamNotFoundError as exc:
        errors["opponent_team_id"] = str(exc)

    except GameOpponentConflictError as exc:
        errors["opponent_team_id"] = str(exc)

    except ValueError as exc:
        errors["form"] = str(exc)

    if errors:
        return render_new_game_form(
            request,
            db,
            errors=errors,
            form_values=form_values,
            status_code=422,
        )

    return RedirectResponse(
        url=f"/app/games/{game.id}/stats",
        status_code=303,
    )

def render_game_stats_form(
    request: Request,
    db: Session,
    game,
    *,
    row_errors: dict[int, str] | None = None,
    form_values: dict[str, str] | None = None,
    saved: bool = False,
    finalized: bool = False,
    status_code: int = 200,
):
    roster_entries = list_season_rosters_for_season(
        db,
        game.season_id,
    )

    existing_stats = list_player_game_stats_for_game(
        db,
        game.id,
    )

    stats_by_roster_id = {
        stats.season_roster_id: stats
        for stats in existing_stats
    }

    return templates.TemplateResponse(
        request=request,
        name="games/stats_entry.html",
        context={
            "game": game,
            "roster_entries": roster_entries,
            "stats_by_roster_id": stats_by_roster_id,
            "participation_statuses": list(ParticipationStatus),
            "row_errors": row_errors or {},
            "form_values": form_values or {},
            "saved": saved,
            "finalized": finalized,
        },
        status_code=status_code,
    )

@router.get(
    "/app/games/{game_id}/stats",
    response_class=HTMLResponse,
)
def game_stats_page(
    request: Request,
    game_id: int,
    db: Session = Depends(get_db),
):
    try:
        game = get_game(db, game_id)
    except GameNotFoundError:
        return HTMLResponse(
            content="Game not found.",
            status_code=404,
        )

    return render_game_stats_form(
        request,
        db,
        game,
        saved=(
                request.query_params.get("saved")
                == "1"
        ),
        finalized=(
                request.query_params.get("finalized")
                == "1"
        ),
    )

@router.post(
    "/app/games/{game_id}/stats",
    response_class=HTMLResponse,
)
async def save_game_stats_page(
    request: Request,
    game_id: int,
    db: Session = Depends(get_db),
):
    try:
        game = get_game(db, game_id)
    except GameNotFoundError:
        return HTMLResponse(
            content="Game not found.",
            status_code=404,
        )

    form = await request.form()

    action = str(
        form.get("action", "save")
    )

    roster_ids = form.getlist("roster_ids")

    row_errors: dict[int, str] = {}

    form_values = {
        key: str(value)
        for key, value in form.multi_items()
        if key != "roster_ids"
    }

    # -----------------------------
    # Opponent score
    # -----------------------------
    raw_opponent_score = str(
        form.get("opponent_score", "")
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

    # -----------------------------
    # Player statistics
    # -----------------------------
    stat_fields = (
        "three_point_attempts",
        "three_point_makes",
        "two_point_attempts",
        "two_point_makes",
        "free_throw_attempts",
        "free_throw_makes",
        "turnovers",
        "assists",
        "offensive_rebounds",
        "defensive_rebounds",
        "steals",
        "deflections",
        "personal_fouls",
    )

    stats_rows: list[
        PlayerGameStatsCreate
    ] = []

    for raw_roster_id in roster_ids:
        try:
            roster_id = int(
                raw_roster_id
            )

            participation = (
                ParticipationStatus(
                    str(
                        form.get(
                            f"participation_{roster_id}",
                            "",
                        )
                    )
                )
            )

            parsed_stats: dict[
                str,
                int,
            ] = {}

            for field in stat_fields:
                raw_value = str(
                    form.get(
                        f"{field}_{roster_id}",
                        "",
                    )
                ).strip()

                if raw_value == "":
                    raise ValueError(
                        "All statistic fields "
                        "must contain a value."
                    )

                value = int(raw_value)

                if value < 0:
                    raise ValueError(
                        "Statistics cannot "
                        "be negative."
                    )

                parsed_stats[field] = value

            stats_rows.append(
                PlayerGameStatsCreate(
                    game_id=game.id,
                    season_roster_id=roster_id,
                    participation_status=participation,
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
                roster_id
            ] = message

    if row_errors:
        return render_game_stats_form(
            request,
            db,
            game,
            row_errors=row_errors,
            form_values=form_values,
            status_code=422,
        )

    # -----------------------------
    # Save or finalize
    # -----------------------------
    try:
        if action == "finalize":
            finalize_game_with_stats(
                db,
                game.id,
                stats_rows,
                opponent_score,
            )

            redirect_url = (
                f"/app/games/{game.id}/stats"
                "?finalized=1"
            )

        elif action == "save":
            save_player_game_stats(
                db,
                game.id,
                stats_rows,
                opponent_score,
            )

            redirect_url = (
                f"/app/games/{game.id}/stats"
                "?saved=1"
            )

        else:
            raise ValueError(
                "Invalid game action."
            )

    except (
        PlayerGameStatsConflictError,
        PlayerGameStatsSeasonMismatchError,
        ValueError,
    ) as exc:
        return render_game_stats_form(
            request,
            db,
            game,
            row_errors={
                0: str(exc)
            },
            form_values=form_values,
            status_code=422,
        )

    return RedirectResponse(
        url=redirect_url,
        status_code=303,
    )