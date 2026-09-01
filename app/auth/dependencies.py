from fastapi import (
    Depends,
    Form,
    Header,
    HTTPException,
    Request,
    status,
)
from app.core.security import csrf_tokens_match
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.models.user import User


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User | None:
    user_id = request.session.get("user_id")

    if not isinstance(user_id, int):
        return None

    user = db.get(User, user_id)

    if user is None:
        return None

    if not user.is_active:
        return None

    return user


def require_html_user(
    current_user: User | None = Depends(
        get_current_user
    ),
) -> User:
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={
                "Location": "/login",
            },
        )

    return current_user


def require_api_user(
    current_user: User | None = Depends(
        get_current_user
    ),
) -> User:
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    return current_user


def require_html_csrf(
    request: Request,
    csrf_token: str = Form(""),
    x_csrf_token: str | None = Header(
        default=None,
        alias="X-CSRF-Token",
    ),
) -> None:
    expected_token = request.session.get(
        "csrf_token"
    )

    submitted_token = (
        csrf_token or x_csrf_token
    )

    if not csrf_tokens_match(
        expected_token,
        submitted_token,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token.",
        )


def require_api_csrf(
    request: Request,
    x_csrf_token: str | None = Header(
        default=None,
        alias="X-CSRF-Token",
    ),
) -> None:
    if request.method not in {
        "POST",
        "PATCH",
        "DELETE",
    }:
        return

    expected_token = request.session.get(
        "csrf_token"
    )

    if not csrf_tokens_match(
        expected_token,
        x_csrf_token,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token.",
        )