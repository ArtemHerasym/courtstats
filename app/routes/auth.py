from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Request,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    ensure_csrf_token,
    get_current_user,
    require_html_csrf,
)
from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.security import (
    csrf_tokens_match,
    generate_csrf_token,
    verify_signup_access_code,
)
from app.core.templates import templates
from app.database.dependencies import get_db
from app.models.user import User
from app.services.auth import (
    UserAlreadyExistsError,
    authenticate_user,
    create_user,
    validate_new_user_credentials,
)


GENERIC_SIGNUP_ERROR = (
    "Account could not be created with the "
    "provided information."
)


router = APIRouter(
    tags=["auth"],
    include_in_schema=False,
)


def _configured_signup_access_code() -> str | None:
    if not settings.signup_enabled:
        return None

    return (
        settings.signup_access_code
        .get_secret_value()
    )


def _login_context(
    *,
    error: str | None = None,
    username: str = "",
    created: bool = False,
) -> dict[str, object]:
    return {
        "error": error,
        "username": username,
        "created": created,
        "signup_enabled": settings.signup_enabled,
    }


def _signup_response(
    request: Request,
    *,
    error: str | None = None,
    username: str = "",
    status_code: int = 200,
):
    return templates.TemplateResponse(
        request=request,
        name="signup.html",
        context={
            "error": error,
            "username": username,
            "csrf_token": ensure_csrf_token(request),
        },
        status_code=status_code,
    )


@router.get(
    "/login",
    response_class=HTMLResponse,
)
def login_page(
    request: Request,
    created: str | None = None,
):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context=_login_context(
            created=created == "1",
        ),
    )


@router.post(
    "/login",
    response_class=HTMLResponse,
)
@limiter.limit("10/minute")
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
            context=_login_context(
                error="Invalid username or password.",
                username=username,
            ),
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


@router.get(
    "/signup",
    response_class=HTMLResponse,
)
def signup_page(
    request: Request,
    current_user: User | None = Depends(
        get_current_user
    ),
):
    if not settings.signup_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if current_user is not None:
        return RedirectResponse(
            url="/",
            status_code=303,
        )

    return _signup_response(request)


@router.post(
    "/signup",
    response_class=HTMLResponse,
    dependencies=[
        Depends(require_html_csrf),
    ],
)
@limiter.limit("5/minute")
def signup(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    password_confirmation: str = Form(""),
    school_access_code: str = Form(""),
    db: Session = Depends(get_db),
):
    if not settings.signup_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
        )

    safe_username = (
        ""
        if school_access_code
        and school_access_code in username
        else username
    )

    try:
        validate_new_user_credentials(
            username,
            password,
        )
    except ValueError as exc:
        return _signup_response(
            request,
            error=str(exc),
            username=safe_username,
            status_code=400,
        )

    if password != password_confirmation:
        return _signup_response(
            request,
            error="Passwords do not match.",
            username=safe_username,
            status_code=400,
        )

    if not verify_signup_access_code(
        school_access_code,
        _configured_signup_access_code(),
    ):
        return _signup_response(
            request,
            error=GENERIC_SIGNUP_ERROR,
            username=safe_username,
            status_code=400,
        )

    try:
        create_user(
            db,
            username,
            password,
        )
    except UserAlreadyExistsError:
        return _signup_response(
            request,
            error=GENERIC_SIGNUP_ERROR,
            username=safe_username,
            status_code=400,
        )

    request.session.clear()

    return RedirectResponse(
        url="/login?created=1",
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
