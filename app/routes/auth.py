from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.security import (
    csrf_tokens_match,
    generate_csrf_token,
)
from app.core.templates import templates
from app.database.dependencies import get_db
from app.services.auth import authenticate_user


router = APIRouter(
    tags=["auth"],
    include_in_schema=False,
)


@router.get(
    "/login",
    response_class=HTMLResponse,
)
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "error": None,
            "username": "",
        },
    )


@router.post(
    "/login",
    response_class=HTMLResponse,
)
def login(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    user = authenticate_user(
        db,
        username,
        password,
    )

    if user is None:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "Invalid username or password.",
                "username": username,
            },
            status_code=401,
        )

    request.session.clear()

    request.session["user_id"] = user.id
    request.session["csrf_token"] = (
        generate_csrf_token()
    )

    return RedirectResponse(
        url="/",
        status_code=303,
    )


@router.post("/logout")
def logout(
    request: Request,
    csrf_token: str = Form(""),
):
    expected_token = request.session.get(
        "csrf_token"
    )

    if not csrf_tokens_match(
        expected_token,
        csrf_token,
    ):
        return HTMLResponse(
            content="Invalid CSRF token.",
            status_code=403,
        )

    request.session.clear()

    return RedirectResponse(
        url="/login",
        status_code=303,
    )