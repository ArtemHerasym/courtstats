from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy.orm import Session

from app.auth.dependencies import require_html_user
from app.database.dependencies import get_db
from app.services.csv_exports import (
    build_game_csv,
    build_player_season_csv,
    build_season_csv,
)
from app.services.game import GameNotFoundError
from app.services.season_roster import (
    SeasonRosterNotFoundError,
)
from app.services.season import (
    SeasonNotFoundError,
)


router = APIRouter(
    prefix="/exports",
    tags=["exports"],
    include_in_schema=False,
    dependencies=[
        Depends(require_html_user),
    ],
)


@router.get("/games/{game_id}.csv")
def export_game_csv(
    game_id: int,
    db: Session = Depends(get_db),
):
    try:
        csv_content = build_game_csv(
            db,
            game_id,
        )

    except GameNotFoundError:
        return PlainTextResponse(
            content="Game not found.",
            status_code=404,
        )

    except ValueError as exc:
        return PlainTextResponse(
            content=str(exc),
            status_code=422,
        )

    filename = (
        f"game-{game_id}-report.csv"
    )

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            ),
        },
    )

@router.get(
    "/season-rosters/{season_roster_id}.csv"
)
def export_player_season_csv(
    season_roster_id: int,
    db: Session = Depends(get_db),
):
    try:
        csv_content = build_player_season_csv(
            db,
            season_roster_id,
        )

    except SeasonRosterNotFoundError:
        return PlainTextResponse(
            content=(
                "Season roster entry not found."
            ),
            status_code=404,
        )

    filename = (
        f"player-season-"
        f"{season_roster_id}.csv"
    )

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                f'attachment; filename="'
                f'{filename}"'
            ),
        },
    )

@router.get("/seasons/{season_id}.csv")
def export_season_csv(
    season_id: int,
    db: Session = Depends(get_db),
):
    try:
        csv_content = build_season_csv(
            db,
            season_id,
        )

    except SeasonNotFoundError:
        return PlainTextResponse(
            content="Season not found.",
            status_code=404,
        )

    filename = (
        f"season-{season_id}-summary.csv"
    )

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            ),
        },
    )