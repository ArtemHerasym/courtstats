"""Public portfolio routing and separation from protected operations."""

from html.parser import HTMLParser

import pytest
from fastapi.testclient import TestClient

from app.database.dependencies import get_db
from app.main import app


class Links(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.links = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.append(dict(attrs))


@pytest.mark.parametrize("path", ["/", "/season-report/2025-26"])
def test_public_pages_without_database_or_anonymous_session(path):
    def forbidden_database():
        pytest.fail("Public pages must not access operational data")

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = forbidden_database
    try:
        with TestClient(app) as client:
            response = client.get(path)
            assert response.status_code == 200
            assert "set-cookie" not in response.headers
            assert not client.cookies
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)

    links = Links(response.text).links
    assert not any("/app" in link.get("href", "") for link in links)
    assert '<form' not in response.text
    assert 'csrf_token' not in response.text
    assert 'Add Game' not in response.text
    assert 'Log out' not in response.text
    assert 'External Games' not in response.text
    assert 'Authorized Staff Login' in response.text
    github = [link for link in links if link.get('href') == 'https://github.com/ArtemHerasym/courtstats']
    assert github
    assert all(link.get('target') == '_blank' and link.get('rel') == 'noopener noreferrer' for link in github)
    assert '/static/css/app.css' in response.text
    assert '/static/js/app.js' in response.text
    assert 'savedTheme === "dark" ? "dark" : "light"' in response.text


def test_portfolio_content_and_no_account_creation():
    with TestClient(app) as client:
        html = client.get('/').text
    for text in ['CourtStats | Basketball Analytics Platform',
                 'Designed and developed by Artem Herasymenko',
                 'Jordan Christian Preparatory', '15', '8', '120',
                 'Player-game observations', 'View Source Code',
                 'View 2025–26 Analytics Case Study', 'SQLAlchemy', 'PostgreSQL',
                 'anonymized', 'read-only', 'verified season snapshot']:
        assert text in html
    assert not any(link.get('href') == '/signup' for link in Links(html).links)
    assert '/static/css/public.css' in html


def test_named_private_home_and_navigation(logged_in_client):
    assert str(app.url_path_for('home_page')) == '/app'
    assert str(app.url_path_for('public_home')) == '/'
    html = logged_in_client.get('/app').text
    assert 'action="/logout"' in html
    assert 'Add Game' in html
    links = Links(html).links
    assert any(link.get('href', '').endswith('/app') and link.get('aria-current') == 'page' for link in links)
    assert logged_in_client.get('/').template.name == 'public_home.html'


@pytest.mark.parametrize('method', ['post', 'put', 'patch', 'delete'])
def test_public_landing_is_read_only(method):
    with TestClient(app) as client:
        assert getattr(client, method)('/').status_code == 405


@pytest.mark.parametrize('path', ['/app', '/app/seasons', '/app/players',
                                 '/app/roster', '/app/games', '/app/external-games'])
def test_anonymous_private_navigation_is_protected(path):
    with TestClient(app) as client:
        client.get('/')
        client.get('/season-report/2025-26')
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers['location'] == '/login'


@pytest.mark.parametrize('path', ['/players', '/seasons', '/games', '/seasons-rosters'])
def test_anonymous_api_reads_and_writes_remain_protected(path):
    with TestClient(app) as client:
        client.get('/')
        assert client.get(path).status_code == 401
        assert client.post(path, json={}).status_code == 401


def test_public_pages_after_logout(logged_in_client):
    # The protected home supplies the existing session token to its logout form.
    import re
    html = logged_in_client.get('/app').text
    token = re.search(r'name="csrf_token"\s+value="([^"]+)"', html).group(1)
    response = logged_in_client.post('/logout', data={'csrf_token': token}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers['location'] == '/login'
    assert logged_in_client.get('/').status_code == 200
    assert logged_in_client.get('/season-report/2025-26').status_code == 200
    assert logged_in_client.get('/app', follow_redirects=False).headers['location'] == '/login'
