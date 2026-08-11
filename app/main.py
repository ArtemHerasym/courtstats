from fastapi import FastAPI
from app.routers.season import router as season_router

app = FastAPI()
app.include_router(season_router)

@app.get("/health")
async def root():
    return {"status": "ok"}