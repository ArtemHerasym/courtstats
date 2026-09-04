from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from app.routes.exports import router as exports_router

from app.auth.dependencies import (
    require_api_csrf,
    require_api_user,
)
from app.core.config import settings
from app.routes.auth import router as auth_router
from app.routes.pages import router as pages_router
from app.routers.game import router as game_router
from app.routers.player import router as player_router
from app.routers.player_game_stats import (
    router as player_game_stats_router,
)
from app.routers.season import router as season_router
from app.routers.season_roster import (
    router as season_roster_router,
)
from app.routers.statistics import router as statistics_router
from app.routes.management import (
    router as management_router,
)


app = FastAPI(
    docs_url=(
        None
        if settings.is_production
        else "/docs"
    ),
    redoc_url=(
        None
        if settings.is_production
        else "/redoc"
    ),
    openapi_url=(
        None
        if settings.is_production
        else "/openapi.json"
    ),
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    session_cookie="courtstats_session",
    max_age=12 * 60 * 60,
    same_site="lax",
    https_only=settings.session_cookie_secure,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"

app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static",
)

# Public authentication routes.
app.include_router(auth_router)

# Protected HTML/Jinja routes.
# pages_router already has require_html_user.
app.include_router(pages_router)
app.include_router(management_router)
app.include_router(exports_router)

# Protected JSON API routes.
app.include_router(
    season_router,
    dependencies=[
        Depends(require_api_user),
        Depends(require_api_csrf),
    ],
)
app.include_router(
    player_router,
    dependencies=[
        Depends(require_api_user),
        Depends(require_api_csrf),
    ],
)
app.include_router(
    season_roster_router,
    dependencies=[
        Depends(require_api_user),
        Depends(require_api_csrf),
    ],
)
app.include_router(
    game_router,
    dependencies=[
        Depends(require_api_user),
        Depends(require_api_csrf),
    ],
)
app.include_router(
    player_game_stats_router,
    dependencies=[
        Depends(require_api_user),
        Depends(require_api_csrf),
    ],
)
app.include_router(
    statistics_router,
    dependencies=[
        Depends(require_api_user),
        Depends(require_api_csrf),
    ],
)


@app.get("/health")
async def root():
    return {"status": "ok"}