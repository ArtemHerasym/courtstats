"""Public editorial content, deliberately independent of private season data."""

import json
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.core.templates import templates


router = APIRouter(tags=["pages"], include_in_schema=False)

# Checked-in, public-safe snapshot. No production connection to Google Sheets.
REPORT_DATA = json.loads(
    (Path(__file__).resolve().parents[1] / "data" / "season_report_2025_26.json")
    .read_text(encoding="utf-8")
)


@router.get("/season-report/2025-26", response_class=HTMLResponse)
def season_report_page(request: Request):
    # No database, user, session mutation, or operational statistics services.
    return templates.TemplateResponse(
        request=request,
        name="season_report.html",
        context={"report": REPORT_DATA},
    )
