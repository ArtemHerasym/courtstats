"""Public report isolation and regression coverage for existing access rules."""

from html.parser import HTMLParser
import re

import pytest
from fastapi.testclient import TestClient

from app.core.templates import templates
from app.database.dependencies import get_db
from app.main import app
from app.routes.season_report import REPORT_DATA


REPORT_URL = "/season-report/2025-26"


class ReportHTML(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def test_public_report_renders_without_database_or_session():
    def forbidden_database():
        pytest.fail("The public report must not access the database")

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = forbidden_database
    try:
        with TestClient(app) as client:
            response = client.get(REPORT_URL, follow_redirects=False)
            assert response.status_code == 200
            assert response.template.name == "season_report.html"
            assert "text/html" in response.headers["content-type"]
            assert "set-cookie" not in response.headers
            assert not client.cookies
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)

    html = response.text
    assert "2025–26 Season Analytics" in html
    assert "Jordan Christian Preparatory National Team" in html
    assert "120" in html and "7–8" in html
    assert "Season figures and team findings verified" in html
    assert "TODO" not in html
    assert "csrf_token" not in html
    parsed = ReportHTML(html)
    assert not any(tag in {"form", "input"} for tag, _ in parsed.tags)
    assert sum(tag == "canvas" for tag, _ in parsed.tags) == 9
    assert sum(tag == "h1" for tag, _ in parsed.tags) == 1
    assert sum(tag == "nav" and attrs.get("aria-label") == "Primary navigation"
               for tag, attrs in parsed.tags) == 1
    ids = [attrs["id"] for _, attrs in parsed.tags if "id" in attrs]
    assert len(ids) == len(set(ids))
    for tag, attrs in parsed.tags:
        if tag == "a" and attrs.get("href", "").startswith("#"):
            assert attrs["href"][1:] in ids
    assert "/static/css/app.css" in html
    assert "/static/css/season-report.css" in html
    assert "/static/js/app.js" in html
    assert "chart.umd" in html
    assert "/static/js/dashboard.js" in html
    assert "/static/js/season-report.js" in html
    assert "docs.google.com" not in html
    assert "grade_level" not in html


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_public_report_has_no_write_methods(client, method):
    assert getattr(client, method)(REPORT_URL).status_code == 405


@pytest.mark.parametrize("path", [
    "/", "/app/seasons", "/app/seasons/1/dashboard", "/app/players",
    "/app/roster", "/app/games", "/app/games/new", "/app/games/1/report",
    "/app/games/1/stats", "/app/external-games", "/app/external-games/new",
])
def test_report_does_not_unlock_private_pages(client, path):
    assert client.get(REPORT_URL).status_code == 200
    response = client.get(path, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


@pytest.mark.parametrize("path", ["/players", "/seasons", "/games", "/seasons-rosters"])
def test_report_does_not_unlock_private_apis(client, path):
    client.get(REPORT_URL)
    assert client.get(path).status_code == 401
    assert client.post(path, json={}).status_code == 401


def test_report_does_not_change_authenticated_session_or_publish_private_data(logged_in_client):
    response = logged_in_client.get(REPORT_URL)
    assert response.status_code == 200
    assert "test-coach" not in response.text
    assert "csrf_token" not in response.text
    assert "<form" not in response.text
    assert logged_in_client.get("/").status_code == 200
    assert logged_in_client.post("/players", json={}).status_code == 403


def test_home_has_one_report_entry_and_keeps_logout(logged_in_client):
    html = logged_in_client.get("/").text
    links = [attrs for tag, attrs in ReportHTML(html).tags if tag == "a"]
    assert sum(attrs.get("href", "").endswith(REPORT_URL) for attrs in links) == 1
    assert 'action="/logout"' in html


def test_report_preserves_methodology_and_limitations(client):
    html = client.get(REPORT_URL).text
    for text in [
        "total makes divided by total attempts", "never the average",
        "result is undefined", "0.44", "No minutes played", "PLAYED/DNP",
        "No quarter-by-quarter", "shot locations", "No opponent box-score",
        "No lineup combinations", "causation", "Opponent quality",
        "per-36", "usage-rate", "clutch", "exact pace", "rebounding margin",
    ]:
        assert text in html


def test_chart_component_has_accessible_fallback_and_escapes_labels():
    # Synthetic component fixture only; never included in published report data.
    component = templates.env.get_template("components/season_report.html").module
    chart = {
        "id": "fixture-chart", "title": "Component fixture", "units": "count",
        "sample_note": "Synthetic test data", "interpretation": "Test only",
        "caution": "Not season results", "category_label": "Label",
        "kind": "player", "labels": ["<script>unsafe</script>"],
        "datasets": [{"label": "Fixture", "data": [None]}],
        "rows": [{"label": "<script>unsafe</script>", "values": ["Undefined"]}],
    }
    html = component.chart(chart)
    assert "<script>unsafe</script>" not in html
    assert "&lt;script&gt;unsafe&lt;/script&gt;" in html
    assert 'scope="row"' in html
    assert 'role="img"' in html
    assert "Undefined" in html
    assert 'class="report-chart-canvas" hidden' in html
    chart["datasets"] = []
    assert "<canvas" not in component.chart(chart)


def test_verified_snapshot_reconciles_games_players_and_shooting():
    totals = REPORT_DATA["team_totals"]
    players = REPORT_DATA["players"]
    games = REPORT_DATA["games"]
    assert len(players) == 8 and len(games) == 15
    assert sum(player["observations"] for player in players) == 120
    assert sum(game["result"] == "Win" for game in games) == 7
    assert sum(game["result"] == "Loss" for game in games) == 8
    assert [game["date"] for game in games] == sorted(game["date"] for game in games)
    for game in games:
        assert game["result"] == ("Win" if game["points"] > game["opponent_points"] else "Loss")
    assert sum(game["points"] for game in games) == totals["points"] == 998
    assert sum(game["opponent_points"] for game in games) == totals["opponent_points"] == 1065
    for key in ("points", "rebounds", "assists", "turnovers", "field_makes", "field_attempts",
                "three_makes", "three_attempts", "two_makes", "two_attempts", "free_makes", "free_attempts"):
        assert sum(player[key] for player in players) == totals[key]
    for player in players:
        assert re.fullmatch(r"#\d+", player["label"])
        assert not ({"name", "full_name", "grade", "grade_level", "notes", "id"} & player.keys())
        assert player["points"] == 3 * player["three_makes"] + 2 * player["two_makes"] + player["free_makes"]
        assert player["ppg"] == f'{player["points"] / player["observations"]:.1f}'
        assert player["rpg"] == f'{player["rebounds"] / player["observations"]:.1f}'
        for prefix, percentage in (("field", "fg"), ("three", "three"), ("two", "two"), ("free", "ft")):
            assert player[f"{prefix}_makes"] <= player[f"{prefix}_attempts"]
            assert player[percentage] == f'{player[f"{prefix}_makes"] / player[f"{prefix}_attempts"]:.1%}'
        assert player["ts"] == f'{player["points"] / (2 * (player["field_attempts"] + .44 * player["free_attempts"])):.1%}'
    metrics = {metric["label"]: metric["value"] for metric in REPORT_DATA["team_metrics"]}
    assert metrics["FG%"] == f'{totals["field_makes"] / totals["field_attempts"]:.1%}'
    assert metrics["TS%"] == f'{totals["points"] / (2 * (totals["field_attempts"] + .44 * totals["free_attempts"])):.1%}'
    assert metrics["Average Margin"] == f'{(totals["points"] - totals["opponent_points"]) / 15:.1f}'


def test_static_chart_values_match_the_verified_snapshot_and_fallback_tables():
    games = REPORT_DATA["games"]
    progression = REPORT_DATA["progression_charts"][0]
    assert progression["datasets"][0]["data"] == [game["points"] for game in games]
    assert progression["datasets"][1]["data"] == [game["opponent_points"] for game in games]
    scoring = REPORT_DATA["player_charts"][0]
    points = {player["label"]: player["points"] for player in REPORT_DATA["players"]}
    assert scoring["datasets"][0]["data"] == [points[label] for label in scoring["labels"]]
    for visual in (REPORT_DATA["team_charts"] + REPORT_DATA["progression_charts"]
                   + REPORT_DATA["player_charts"] + REPORT_DATA["comparison_charts"]
                   + REPORT_DATA["period_charts"]):
        assert len(visual["labels"]) == len(visual["rows"])
        for index, row in enumerate(visual["rows"]):
            assert [float(value) for value in row["values"]] == [dataset["data"][index] for dataset in visual["datasets"]]


def test_public_player_tables_explain_observations_and_small_attempt_samples(client):
    html = client.get(REPORT_URL).text
    assert "It counts rows, not verified appearances" in html
    assert "Small samples should not be treated as reliable efficiency rankings" in html
    assert "FGM / FGA" in html
    assert "48.7%" in html and "56.1%" in html and "66.5" in html


def test_user_verified_findings_keep_approved_values_and_sample_context(client):
    comparisons = {row["metric"]: (row["wins"], row["losses"]) for row in REPORT_DATA["win_loss_rows"]}
    assert comparisons == {
        "PPG": ("72.7", "61.1"), "FG%": ("52.7%", "45.3%"),
        "TS%": ("61.3%", "51.5%"), "3P%": ("38.8%", "29.6%"),
        "2P%": ("61.6%", "53.4%"), "REB/G": ("44.3", "27.4"),
        "OREB/G": ("19.0", "7.3"), "AST/G": ("16.1", "12.6"),
        "TOV/G": ("10.3", "22.0"), "AST:TOV": ("1.57", "0.57"),
        "FGA/G": ("55.6", "55.5"),
    }
    periods = {row["metric"]: (row["first"], row["final"]) for row in REPORT_DATA["period_rows"]}
    assert periods == {
        "PPG": ("59.6", "71.6"), "Turnovers / game": ("20.0", "14.4"),
        "FG%": ("46.0%", "50.9%"), "TS%": ("52.7%", "58.9%"),
        "Rebounds / game": ("32.4", "38.4"), "Average scoring margin": ("-17.0", "+0.8"),
    }
    assert [period["value"] for period in REPORT_DATA["period_records"]] == ["1–4", "3–2", "3–2"]
    assert len(REPORT_DATA["major_findings"]) == 4
    assert all(chart["sample_note"] == "7 wins and 8 losses" for chart in REPORT_DATA["comparison_charts"])
    html = client.get(REPORT_URL).text
    for text in ("10–11", "17–25", "16.9 more rebounds", "at least 35 rebounds",
                 "All 7 games below 35 rebounds", "associated with", "Opponent quality"):
        assert text in html
    assert "caused" not in html and "winning formula" not in html
