"""Deletion ownership, completed-game invariants, and HTML security boundaries."""
from datetime import date
from html.parser import HTMLParser
import re
from unittest.mock import patch

import pytest
from sqlalchemy import event, select
from sqlalchemy.exc import SQLAlchemyError

from app.models.external_game import ExternalGame
from app.models.external_game_player_stats import ExternalGamePlayerStats
from app.models.game import Game, GameStatus, VenueType
from app.models.player import Player
from app.models.player_game_stats import ParticipationStatus, PlayerGameStats
from app.models.season import Season, SeasonStatus
from app.models.season_roster import SeasonRoster
from app.models.team import Team
from app.models.user import User
from app.services.external_game import delete_external_game, ExternalGameNotFoundError
from app.services.external_game_analysis import get_external_game_report
from app.services.player import delete_player, PlayerNotFoundError, PlayerDeletionConflictError
from app.services.season import delete_season, SeasonNotFoundError
from app.services.statistics import calculate_team_season_summary


@pytest.fixture
def history(db_session):
    team, opponent = Team(name="Jordan Christian Preparatory"), Team(name="Other team")
    players = [Player(full_name=f"Disposable player {i}") for i in range(2)]
    db_session.add_all([team, opponent, *players])
    db_session.flush()
    seasons = [Season(team_id=team.id, name=name) for name in ["2025-26", "Other season"]]
    db_session.add_all(seasons)
    db_session.flush()
    rosters, games, stats, external, external_stats = [], [], [], [], []
    for i, season in enumerate(seasons):
        rows = [SeasonRoster(season_id=season.id, player_id=p.id) for p in players]
        game = Game(season_id=season.id, opponent_team_id=opponent.id,
                    game_date=date(2025, 12, 1), venue_type=VenueType.HOME,
                    status=GameStatus.COMPLETED, opponent_score=5)
        ext = ExternalGame(name=f"Disposable external {i}", opponent_team_id=opponent.id,
                           game_date=date(2025, 12, 1), venue_type=VenueType.HOME,
                           status=GameStatus.COMPLETED, opponent_score=5)
        db_session.add_all([*rows, game, ext])
        db_session.flush()
        normal_rows = [PlayerGameStats(game_id=game.id, season_roster_id=r.id,
                       participation_status=ParticipationStatus.PLAYED,
                       two_point_makes=n, two_point_attempts=4) for r, n in zip(rows, [3, 1])]
        ext_rows = [ExternalGamePlayerStats(external_game_id=ext.id, player_id=p.id,
                    participation_status=ParticipationStatus.PLAYED,
                    two_point_makes=n, two_point_attempts=4) for p, n in zip(players, [3, 1])]
        db_session.add_all([*normal_rows, *ext_rows])
        rosters.extend(rows)
        games.append(game)
        external.append(ext)
        stats.extend(normal_rows)
        external_stats.extend(ext_rows)
    db_session.commit()
    return dict(teams=[team, opponent], players=players, seasons=seasons,
                rosters=rosters, games=games, stats=stats,
                external=external, external_stats=external_stats)


def snapshot(db):
    models = [Team, Player, Season, SeasonRoster, Game, PlayerGameStats,
              ExternalGame, ExternalGamePlayerStats, User]
    return {m: list(db.execute(select(*m.__table__.columns).order_by(m.id))) for m in models}


def assert_remain(db, objects):
    for obj in objects:
        assert db.get(type(obj), obj.id) is not None


@pytest.mark.parametrize("status", list(SeasonStatus))
def test_season_owned_rows_only(db_session, history, status):
    season = history["seasons"][0]
    season.status = status
    db_session.commit()
    season_id, game_id = season.id, history["games"][0].id
    assert len(season.games) == 1 and len(season.season_rosters) == 2
    assert len(season.games[0].player_game_stats) == 2
    with patch.object(db_session, "commit", wraps=db_session.commit) as commit:
        delete_season(db_session, season_id)
    commit.assert_called_once_with()
    assert db_session.get(Season, season_id) is None
    assert db_session.get(Game, game_id) is None
    assert not db_session.scalars(select(SeasonRoster).where(SeasonRoster.season_id == season_id)).all()
    assert not db_session.scalars(select(PlayerGameStats).where(PlayerGameStats.game_id == game_id)).all()
    assert_remain(db_session, history["teams"] + history["players"] + history["external"]
                  + history["external_stats"] + history["seasons"][1:]
                  + history["games"][1:] + history["stats"][2:] + history["rosters"][2:])


def test_empty_setup_season(db_session, history):
    season = Season(team_id=history["teams"][0].id, name="Empty")
    db_session.add(season)
    db_session.commit()
    season_id = season.id
    delete_season(db_session, season_id)
    assert db_session.get(Season, season_id) is None


@pytest.mark.parametrize("status", list(GameStatus))
def test_external_owned_rows_only(db_session, history, status):
    game = history["external"][0]
    game.status = status
    db_session.commit()
    game_id = game.id
    assert len(game.player_stats) == 2
    before = snapshot(db_session)
    with patch.object(db_session, "commit", wraps=db_session.commit) as commit:
        delete_external_game(db_session, game_id)
    commit.assert_called_once_with()
    assert db_session.get(ExternalGame, game_id) is None
    assert not db_session.scalars(select(ExternalGamePlayerStats).where(
        ExternalGamePlayerStats.external_game_id == game_id)).all()
    after = snapshot(db_session)
    for model in before.keys() - {ExternalGame, ExternalGamePlayerStats}:
        assert before[model] == after[model]
    assert_remain(db_session, history["external"][1:] + history["external_stats"][2:])
    with pytest.raises(ExternalGameNotFoundError):
        get_external_game_report(db_session, game_id)


@pytest.mark.parametrize("roster_only", [False, True])
def test_player_without_stats(db_session, history, roster_only):
    player = Player(full_name="Unused")
    db_session.add(player)
    db_session.flush()
    player_id = player.id
    if roster_only:
        db_session.add(SeasonRoster(player_id=player_id, season_id=history["seasons"][0].id))
    db_session.commit()
    delete_player(db_session, player_id)
    assert db_session.get(Player, player_id) is None
    assert not db_session.scalars(select(SeasonRoster).where(SeasonRoster.player_id == player_id)).all()


def test_safe_player_removes_only_history_and_recalculates(db_session, history):
    player_id = history["players"][0].id
    season_id = history["seasons"][0].id
    ext_id = history["external"][0].id
    assert len(history["players"][0].season_rosters) == 2
    assert calculate_team_season_summary(db_session, season_id)["points"] == 8
    assert get_external_game_report(db_session, ext_id)["summary"]["points"] == 8
    with patch.object(db_session, "commit", wraps=db_session.commit) as commit:
        delete_player(db_session, player_id)
    commit.assert_called_once_with()
    assert db_session.get(Player, player_id) is None
    for key in ["rosters", "stats", "external_stats"]:
        for obj in history[key][::2]:
            assert db_session.get(type(obj), obj.id) is None
        assert_remain(db_session, history[key][1::2])
    assert_remain(db_session, history["teams"] + history["seasons"] + history["games"]
                  + history["external"] + history["players"][1:])
    normal = calculate_team_season_summary(db_session, season_id)
    assert (normal["points"], normal["games_played"], normal["field_goal_percentage"]) == (2, 1, 0.25)
    ext = get_external_game_report(db_session, ext_id)["summary"]
    assert ext["points"] == 2


@pytest.mark.parametrize("kind", ["stats", "external_stats"])
@pytest.mark.parametrize("other_dnp", [False, True])
def test_sole_played_conflict_is_zero_mutations(db_session, history, kind, other_dnp):
    other = history[kind][1]
    if other_dnp:
        other.participation_status = ParticipationStatus.DID_NOT_PLAY
        other.two_point_makes = other.two_point_attempts = 0
    else:
        db_session.delete(other)
    db_session.commit()
    before = snapshot(db_session)
    statements = []
    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement.strip().split()[0].upper())
    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", record)
    try:
        with pytest.raises(PlayerDeletionConflictError, match="only PLAYED participant"):
            delete_player(db_session, history["players"][0].id)
    finally:
        event.remove(engine, "before_cursor_execute", record)
    assert not {"INSERT", "UPDATE", "DELETE"}.intersection(statements)
    assert snapshot(db_session) == before


@pytest.mark.parametrize("kind", ["stats", "external_stats"])
def test_deleting_dnp_player_does_not_block(db_session, history, kind):
    for row in history[kind][::2]:
        row.participation_status = ParticipationStatus.DID_NOT_PLAY
        row.two_point_makes = row.two_point_attempts = 0
    db_session.commit()
    player_id = history["players"][0].id
    delete_player(db_session, player_id)
    assert db_session.get(Player, player_id) is None


def test_draft_games_can_lose_the_only_played_player(db_session, history):
    for key in ["games", "external"]:
        for game in history[key]:
            game.status = GameStatus.DRAFT
    for key in ["stats", "external_stats"]:
        for row in history[key][1::2]:
            db_session.delete(row)
    db_session.commit()
    delete_player(db_session, history["players"][0].id)
    assert_remain(db_session, history["games"] + history["external"])


CASES = [
    ("seasons", Season, delete_season, SeasonNotFoundError, "Season"),
    ("players", Player, delete_player, PlayerNotFoundError, "Player"),
    ("external", ExternalGame, delete_external_game, ExternalGameNotFoundError, "External game"),
]


@pytest.mark.parametrize("key,model,service,error,label", CASES)
def test_missing_service(db_session, key, model, service, error, label):
    with pytest.raises(error, match="999999"):
        service(db_session, 999999)


@pytest.mark.parametrize("key,model,service,error,label", CASES)
@pytest.mark.parametrize("failure_point", ["execute", "delete", "commit"])
def test_failure_rolls_back_every_row(db_session, history, key, model, service, error, label, failure_point):
    before = snapshot(db_session)
    target_id = history[key][0].id
    with patch.object(db_session, failure_point, side_effect=SQLAlchemyError("injected failure")):
        with patch.object(db_session, "rollback", wraps=db_session.rollback) as rollback:
            with pytest.raises(SQLAlchemyError, match="injected failure"):
                service(db_session, target_id)
            rollback.assert_called_once_with()
    assert snapshot(db_session) == before


def path(key):
    return "/app/" + ("external-games" if key == "external" else key)


@pytest.mark.parametrize("key,model,service,error,label", CASES)
def test_delete_form_post_success(logged_in_client, db_session, history, key, model, service, error, label):
    target_id = history[key][0].id
    url = f"{path(key)}/{target_id}/delete"
    page = logged_in_client.get(path(key))
    form = re.search(r'<form\s+method="post"\s+action="[^"]*' + url + r'"[\s\S]*?</form>', page.text).group()
    assert "button-destructive" in form
    assert "return confirm('Delete this " in form and "This cannot be undone." in form
    token = re.search(r'name="csrf_token"\s+value="([^"]+)"', form).group(1)
    users_before = snapshot(db_session)[User]
    response = logged_in_client.post(url, data={"csrf_token": token}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == path(key) + "?deleted=1"
    assert db_session.get(model, target_id) is None
    assert snapshot(db_session)[User] == users_before
    page = logged_in_client.get(response.headers["location"])
    assert f"{label} deleted." in page.text
    assert url not in page.text
    assert f"{label} deleted." not in logged_in_client.get(path(key)).text


@pytest.mark.parametrize("key,model,service,error,label", CASES)
@pytest.mark.parametrize("data", [{}, {"csrf_token": "invalid"}])
def test_csrf_rejected(logged_in_client, db_session, history, key, model, service, error, label, data):
    before = snapshot(db_session)
    response = logged_in_client.post(f"{path(key)}/{history[key][0].id}/delete", data=data)
    assert response.status_code == 403
    assert snapshot(db_session) == before


@pytest.mark.parametrize("key,model,service,error,label", CASES)
def test_anonymous_protected(client, db_session, history, key, model, service, error, label):
    before = snapshot(db_session)
    response = client.post(f"{path(key)}/{history[key][0].id}/delete", follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"] == "/login"
    assert snapshot(db_session) == before


@pytest.mark.parametrize("key,model,service,error,label", CASES)
def test_get_never_deletes_and_post_missing_404(authenticated_client, db_session, history, key, model, service, error, label):
    before = snapshot(db_session)
    assert authenticated_client.get(f"{path(key)}/{history[key][0].id}/delete").status_code == 405
    response = authenticated_client.post(f"{path(key)}/999999/delete")
    assert response.status_code == 404 and response.text == f"{label} not found."
    assert snapshot(db_session) == before


@pytest.mark.parametrize("kind", ["stats", "external_stats"])
def test_conflict_page_is_clean(authenticated_client, db_session, history, kind):
    db_session.delete(history[kind][1])
    db_session.commit()
    before = snapshot(db_session)
    response = authenticated_client.post(f"/app/players/{history['players'][0].id}/delete", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/app/players?deletion_conflict=1"
    page = authenticated_client.get(response.headers["location"])
    assert page.status_code == 200
    assert "message-error" in page.text and "only PLAYED participant" in page.text
    assert "Correct or delete that game first." in page.text
    assert snapshot(db_session) == before


class FormParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active_form = None
        self.controls = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            assert self.active_form is None, "Nested form breaks delete/analysis submission"
            self.active_form = attrs.get("id", attrs.get("action"))
        if tag in {"input", "button"}:
            self.controls.append((attrs, attrs.get("form", self.active_form)))

    def handle_endtag(self, tag):
        if tag == "form":
            self.active_form = None


@pytest.mark.parametrize("status", list(GameStatus))
def test_external_confirmation_and_analysis_form(logged_in_client, db_session, history, status):
    history["external"][0].status = status
    db_session.commit()
    page = logged_in_client.get("/app/external-games")
    message = ("Delete this draft external game? This cannot be undone." if status == GameStatus.DRAFT else
               "Delete this completed external game and all of its player statistics? This cannot be undone.")
    assert message in page.text
    parser = FormParser()
    parser.feed(page.text)
    for attrs, owner in parser.controls:
        if attrs.get("name") == "game_ids" or attrs.get("id") == "view-analysis-button":
            assert owner == "external-games-analysis-form"
        elif attrs.get("name") == "csrf_token" and "external-games" in str(owner):
            assert owner.endswith("/delete")


def test_report_link_only_for_exact_historical_row(logged_in_client, db_session, history):
    other = Season(team_id=history["teams"][1].id, name="2025-26")
    db_session.add(other)
    db_session.commit()
    page = logged_in_client.get("/app/seasons")
    rows = re.findall(r"<tr>[\s\S]*?</tr>", page.text)
    linked = [row for row in rows if "Season Report" in row]
    assert len(linked) == 1
    assert "Jordan Christian Preparatory" in linked[0] and "2025-26" in linked[0]
    assert '/season-report/2025-26"' in linked[0]
    for row in rows:
        if "Other season" in row or "Other team" in row:
            assert "Season Report" not in row
    report = logged_in_client.get("/season-report/2025-26")
    assert report.status_code == 200
    assert '/static/css/season-report.css' in report.text
    assert '/static/js/season-report.js' in report.text
    assert 'http://testserver/static' not in report.text


@pytest.mark.parametrize("url", ["/login", "/signup", "/app/seasons", "/season-report/2025-26"])
def test_rendered_theme_defaults(logged_in_client, url):
    page = logged_in_client.get(url)
    assert page.status_code == 200
    assert 'savedTheme === "dark" ? "dark" : "light"' in page.text
    assert "prefers-color-scheme" not in page.text
    assert "data-theme-toggle" in page.text
