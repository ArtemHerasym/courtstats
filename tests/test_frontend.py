def test_home_page(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "CourtStats" in response.text


def test_home_page_loads_stylesheet(client):
    response = client.get("/")

    assert "/static/css/app.css" in response.text


def test_static_css_is_served(client):
    response = client.get("/static/css/app.css")

    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]