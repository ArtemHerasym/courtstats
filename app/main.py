from fastapi import FastAPI
from app.routers.season import router as season_router
from app.routers.player import router as player_router
from app.routers.season_roster import router as season_roster_router
from app.routers.game import router as game_router
from app.routers.player_game_stats import (
    router as player_game_stats_router,
)
from app.routers.statistics import router as statistics_router

from pathlib import Path

from fastapi.staticfiles import StaticFiles

from app.routes.pages import router as pages_router


app = FastAPI()

STATIC_DIR = Path(__file__).resolve().parent / "static"

app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static",
)
app.include_router(pages_router)
app.include_router(season_router)
app.include_router(player_router)
app.include_router(season_roster_router)
app.include_router(game_router)
app.include_router(player_game_stats_router)
app.include_router(statistics_router)


@app.get("/health")
async def root():
    return {"status": "ok"}