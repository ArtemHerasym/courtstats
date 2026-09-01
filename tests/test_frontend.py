def test_home_page(authenticated_client):
    response = authenticated_client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "CourtStats" in response.text


def test_home_page_loads_stylesheet(
    authenticated_client,
):
    response = authenticated_client.get("/")

    assert "/static/css/app.css" in response.text


def test_static_css_is_served(client):
    response = client.get(
        "/static/css/app.css"
    )

    assert response.status_code == 200
    assert "text/css" in response.headers[
        "content-type"
    ]


def test_anonymous_home_redirects_to_login(
    client,
):
    response = client.get(
        "/",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/login"