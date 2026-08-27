from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.core.templates import templates


router = APIRouter(
    tags=["pages"],
    include_in_schema=False,
)


@router.get("/", response_class=HTMLResponse)
def home_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="home.html",
    )