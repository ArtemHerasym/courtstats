import re


def _extract_csrf_token(client) -> str:
    response = client.get(
        "/app/games/new"
    )

    assert response.status_code == 200

    match = re.search(
        r'name="csrf_token"\s+'
        r'value="([^"]+)"',
        response.text,
    )

    assert match is not None

    return match.group(1)


def _game_form_data(
    csrf_token: str | None = None,
) -> dict[str, str]:
    data = {
        "season_id": "1",
        "game_date": "08/28/2026",
        "opponent_team_id": "1",
        "venue_type": "HOME",
        "opponent_score": "",
        "notes": "",
    }

    if csrf_token is not None:
        data["csrf_token"] = csrf_token

    return data


def test_html_post_rejects_missing_csrf(
    logged_in_client,
):
    response = logged_in_client.post(
        "/app/games/new",
        data=_game_form_data(),
        follow_redirects=False,
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Invalid CSRF token."
    }


def test_html_post_rejects_invalid_csrf(
    logged_in_client,
):
    response = logged_in_client.post(
        "/app/games/new",
        data=_game_form_data(
            csrf_token="invalid-token"
        ),
        follow_redirects=False,
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Invalid CSRF token."
    }


def test_api_get_does_not_require_csrf(
    logged_in_client,
):
    response = logged_in_client.get(
        "/players"
    )

    assert response.status_code == 200


def test_api_post_rejects_missing_csrf(
    logged_in_client,
):
    response = logged_in_client.post(
        "/players",
        json={
            "full_name": "Missing CSRF Player",
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Invalid CSRF token."
    }


def test_api_post_rejects_invalid_csrf(
    logged_in_client,
):
    response = logged_in_client.post(
        "/players",
        json={
            "full_name": "Invalid CSRF Player",
        },
        headers={
            "X-CSRF-Token": "invalid-token",
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Invalid CSRF token."
    }


def test_api_post_accepts_valid_csrf(
    authenticated_client,
):
    response = authenticated_client.post(
        "/players",
        json={
            "full_name": "Valid CSRF Player",
        },
    )

    assert response.status_code == 201


def test_api_patch_rejects_missing_csrf(
    authenticated_client,
):
    create_response = authenticated_client.post(
        "/players",
        json={
            "full_name": "Patch CSRF Player",
        },
    )

    assert create_response.status_code == 201

    player_id = create_response.json()["id"]

    authenticated_client.headers.pop(
        "X-CSRF-Token",
        None,
    )

    response = authenticated_client.patch(
        f"/players/{player_id}",
        json={
            "full_name": "Changed Player",
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Invalid CSRF token."
    }


def test_logout_rejects_missing_csrf(
    logged_in_client,
):
    response = logged_in_client.post(
        "/logout",
        data={},
        follow_redirects=False,
    )

    assert response.status_code == 403


def test_logout_rejects_invalid_csrf(
    logged_in_client,
):
    response = logged_in_client.post(
        "/logout",
        data={
            "csrf_token": "invalid-token",
        },
        follow_redirects=False,
    )

    assert response.status_code == 403


def test_logout_accepts_valid_csrf(
    logged_in_client,
):
    csrf_token = _extract_csrf_token(
        logged_in_client
    )

    response = logged_in_client.post(
        "/logout",
        data={
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/login"

    protected_response = logged_in_client.get(
        "/",
        follow_redirects=False,
    )

    assert protected_response.status_code == 303
    assert (
        protected_response.headers["location"]
        == "/login"
    )