from sqlalchemy import select

from app.models.player import Player
from app.models.season import Season
from app.models.season_roster import (
    RosterStatus,
    SeasonRoster,
)
from app.models.team import Team


def test_add_season_page_uses_team_name(
    logged_in_client,
):
    response = logged_in_client.get(
        "/app/seasons/new"
    )

    assert response.status_code == 200

    assert 'name="team_name"' in response.text
    assert 'id="team_name"' in response.text

    assert 'name="team_id"' not in response.text
    assert "Select team" not in response.text


def test_add_season_page_uses_mm_dd_yyyy_dates(
    logged_in_client,
):
    response = logged_in_client.get(
        "/app/seasons/new"
    )

    assert response.status_code == 200

    assert response.text.count(
        "data-date-input"
    ) >= 2

    assert (
        'placeholder="MM/DD/YYYY"'
        in response.text
    )

    assert 'type="date"' not in response.text


def test_create_season_creates_new_team(
    authenticated_client,
    db_session,
):
    response = authenticated_client.post(
        "/app/seasons/new",
        data={
            "team_name": (
                "Jordan Christian Preparatory"
            ),
            "name": "2027-2028",
            "start_date": "09/01/2027",
            "end_date": "03/15/2028",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    team = db_session.scalar(
        select(Team).where(
            Team.name
            == "Jordan Christian Preparatory"
        )
    )

    assert team is not None

    season = db_session.scalar(
        select(Season).where(
            Season.team_id == team.id,
            Season.name == "2027-2028",
        )
    )

    assert season is not None

    assert (
        response.headers["location"]
        == (
            f"/app/seasons/"
            f"{season.id}/setup-roster"
        )
    )


def test_create_season_reuses_existing_team_case_insensitive(
    authenticated_client,
    db_session,
):
    existing_team = Team(
        name="Jordan Christian Preparatory",
        abbreviation="JCP",
    )

    db_session.add(existing_team)
    db_session.commit()
    db_session.refresh(existing_team)

    response = authenticated_client.post(
        "/app/seasons/new",
        data={
            "team_name": (
                "jordan christian preparatory"
            ),
            "name": "2028-2029",
            "start_date": "",
            "end_date": "",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    teams = list(
        db_session.scalars(
            select(Team)
        ).all()
    )

    assert len(teams) == 1
    assert teams[0].id == existing_team.id

    season = db_session.scalar(
        select(Season).where(
            Season.name == "2028-2029"
        )
    )

    assert season is not None
    assert season.team_id == existing_team.id


def test_create_season_rejects_invalid_date(
    authenticated_client,
    db_session,
):
    response = authenticated_client.post(
        "/app/seasons/new",
        data={
            "team_name": "JCP",
            "name": "2029-2030",
            "start_date": "02/29/2027",
            "end_date": "",
        },
        follow_redirects=False,
    )

    assert response.status_code == 422

    assert (
        "Start date is not a valid calendar date."
        in response.text
    )

    seasons = list(
        db_session.scalars(
            select(Season)
        ).all()
    )

    teams = list(
        db_session.scalars(
            select(Team)
        ).all()
    )

    assert seasons == []
    assert teams == []


def test_create_season_preserves_values_after_error(
    authenticated_client,
):
    response = authenticated_client.post(
        "/app/seasons/new",
        data={
            "team_name": (
                "Jordan Christian Preparatory"
            ),
            "name": "2030-2031",
            "start_date": "13/01/2030",
            "end_date": "",
        },
        follow_redirects=False,
    )

    assert response.status_code == 422

    assert (
        'value="Jordan Christian Preparatory"'
        in response.text
    )

    assert (
        'value="2030-2031"'
        in response.text
    )

    assert (
        'value="13/01/2030"'
        in response.text
    )


def test_edit_season_shows_team_read_only(
    logged_in_client,
    db_session,
):
    team = Team(
        name="Jordan Christian Preparatory",
        abbreviation="JCP",
    )

    db_session.add(team)
    db_session.flush()

    season = Season(
        team_id=team.id,
        name="2027-2028",
    )

    db_session.add(season)
    db_session.commit()
    db_session.refresh(season)

    response = logged_in_client.get(
        f"/app/seasons/{season.id}/edit"
    )

    assert response.status_code == 200

    assert (
        "Jordan Christian Preparatory"
        in response.text
    )

    assert 'id="team_display"' in response.text
    assert "readonly" in response.text

    assert 'name="team_id"' not in response.text
    assert 'name="team_name"' not in response.text


def test_setup_roster_page_handles_empty_roster(
    logged_in_client,
    db_session,
):
    team = Team(
        name="Jordan Christian Preparatory",
    )

    db_session.add(team)
    db_session.flush()

    season = Season(
        team_id=team.id,
        name="2027-2028",
    )

    db_session.add(season)
    db_session.commit()
    db_session.refresh(season)

    response = logged_in_client.get(
        (
            f"/app/seasons/"
            f"{season.id}/setup-roster"
        )
    )

    assert response.status_code == 200

    assert "Set Up Roster" in response.text

    assert (
        "Jordan Christian Preparatory"
        in response.text
    )

    assert "2027-2028" in response.text
    assert "No players yet" in response.text
    assert "Add Player" in response.text
    assert "Skip for Now" in response.text

    assert (
        "return_context=season_setup"
        in response.text
    )


def test_setup_roster_page_lists_players(
    logged_in_client,
    db_session,
):
    team = Team(
        name="Jordan Christian Preparatory",
    )

    db_session.add(team)
    db_session.flush()

    season = Season(
        team_id=team.id,
        name="2027-2028",
    )

    db_session.add(season)
    db_session.flush()

    player = Player(
        full_name="Kevin Lans",
        display_name=None,
    )

    db_session.add(player)
    db_session.flush()

    roster = SeasonRoster(
        season_id=season.id,
        player_id=player.id,
        jersey_number=3,
        position="Guard",
        grade_level="12",
        status=RosterStatus.ACTIVE,
    )

    db_session.add(roster)
    db_session.commit()

    response = logged_in_client.get(
        (
            f"/app/seasons/"
            f"{season.id}/setup-roster"
        )
    )

    assert response.status_code == 200

    assert "Kevin Lans" in response.text
    assert "#3" in response.text
    assert "Guard" in response.text
    assert "Finish Setup" in response.text

    assert (
        "Add Another Player"
        in response.text
    )


def test_setup_roster_returns_404_for_missing_season(
    logged_in_client,
):
    response = logged_in_client.get(
        "/app/seasons/999999/setup-roster"
    )

    assert response.status_code == 404


def test_roster_form_from_season_setup_locks_season(
    logged_in_client,
    db_session,
):
    team = Team(
        name="Jordan Christian Preparatory",
    )

    db_session.add(team)
    db_session.flush()

    season = Season(
        team_id=team.id,
        name="2027-2028",
    )

    db_session.add(season)
    db_session.commit()
    db_session.refresh(season)

    response = logged_in_client.get(
        (
            "/app/roster/new?"
            f"season_id={season.id}&"
            "return_context=season_setup"
        )
    )

    assert response.status_code == 200

    assert (
        "2027-2028 — "
        "Jordan Christian Preparatory"
        in response.text
    )

    normalized_html = " ".join(
        response.text.split()
    )

    assert (
        f'name="season_id" '
        f'value="{season.id}"'
        in normalized_html
    )

    assert (
        'name="return_context" '
        'value="season_setup"'
        in normalized_html
    )


def test_add_roster_player_from_setup_returns_to_setup(
    authenticated_client,
    db_session,
):
    team = Team(
        name="Jordan Christian Preparatory",
    )

    db_session.add(team)
    db_session.flush()

    season = Season(
        team_id=team.id,
        name="2027-2028",
    )

    db_session.add(season)
    db_session.flush()

    player = Player(
        full_name="Kevin Lans",
        display_name=None,
    )

    db_session.add(player)
    db_session.commit()

    db_session.refresh(season)
    db_session.refresh(player)

    response = authenticated_client.post(
        "/app/roster/new",
        data={
            "season_id": str(season.id),
            "player_id": str(player.id),
            "jersey_number": "3",
            "position": "Guard",
            "grade_level": "12",
            "status": "ACTIVE",
            "return_context": (
                "season_setup"
            ),
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    assert (
        response.headers["location"]
        == (
            f"/app/seasons/"
            f"{season.id}/setup-roster"
        )
    )

    roster = db_session.scalar(
        select(SeasonRoster).where(
            SeasonRoster.season_id
            == season.id,
            SeasonRoster.player_id
            == player.id,
        )
    )

    assert roster is not None
    assert roster.jersey_number == 3
    assert roster.position == "Guard"