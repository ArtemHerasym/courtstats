from fastapi import FastAPI
from app.routers.season import router as season_router
from app.routers.player import router as player_router


app = FastAPI()

app.include_router(season_router)
app.include_router(player_router)


@app.get("/health")
async def root():
    return {"status": "ok"}