"""add external games

Revision ID: 839e29af1f2b
Revises: 33dfba39c302
Create Date: 2026-09-04 18:40:16.335936

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "839e29af1f2b"
down_revision: Union[
    str,
    Sequence[str],
    None,
] = "33dfba39c302"
branch_labels: Union[
    str,
    Sequence[str],
    None,
] = None
depends_on: Union[
    str,
    Sequence[str],
    None,
] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "external_games",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(),
            nullable=False,
        ),
        sa.Column(
            "opponent_team_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "game_date",
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            "venue_type",
            postgresql.ENUM(
                "HOME",
                "AWAY",
                "NEUTRAL",
                name="venue_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "opponent_score",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "DRAFT",
                "COMPLETED",
                name="game_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "notes",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "btrim(name) <> ''",
            name=(
                "ck_external_games_"
                "name_not_blank"
            ),
        ),
        sa.CheckConstraint(
            (
                "opponent_score IS NULL "
                "OR opponent_score >= 0"
            ),
            name=(
                "ck_external_games_"
                "opponent_score_nonnegative"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["opponent_team_id"],
            ["teams.id"],
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
    )

    op.create_table(
        "external_game_player_stats",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "external_game_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "player_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "participation_status",
            postgresql.ENUM(
                "PLAYED",
                "DID_NOT_PLAY",
                name="participation_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "three_point_attempts",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "three_point_makes",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "two_point_attempts",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "two_point_makes",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "free_throw_attempts",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "free_throw_makes",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "turnovers",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "assists",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "offensive_rebounds",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "defensive_rebounds",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "steals",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "deflections",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "personal_fouls",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            """
            participation_status <> 'DID_NOT_PLAY'
            OR (
                three_point_attempts = 0 AND
                three_point_makes = 0 AND
                two_point_attempts = 0 AND
                two_point_makes = 0 AND
                free_throw_attempts = 0 AND
                free_throw_makes = 0 AND
                turnovers = 0 AND
                assists = 0 AND
                offensive_rebounds = 0 AND
                defensive_rebounds = 0 AND
                steals = 0 AND
                deflections = 0 AND
                personal_fouls = 0
            )
            """,
            name=(
                "ck_external_game_player_stats_"
                "dnp_zero_stats"
            ),
        ),
        sa.CheckConstraint(
            """
            three_point_attempts >= 0 AND
            three_point_makes >= 0 AND
            two_point_attempts >= 0 AND
            two_point_makes >= 0 AND
            free_throw_attempts >= 0 AND
            free_throw_makes >= 0 AND
            turnovers >= 0 AND
            assists >= 0 AND
            offensive_rebounds >= 0 AND
            defensive_rebounds >= 0 AND
            steals >= 0 AND
            deflections >= 0 AND
            personal_fouls >= 0
            """,
            name=(
                "ck_external_game_player_stats_"
                "nonnegative"
            ),
        ),
        sa.CheckConstraint(
            (
                "free_throw_makes "
                "<= free_throw_attempts"
            ),
            name=(
                "ck_external_game_player_stats_"
                "ftm_lte_fta"
            ),
        ),
        sa.CheckConstraint(
            (
                "three_point_makes "
                "<= three_point_attempts"
            ),
            name=(
                "ck_external_game_player_stats_"
                "3pm_lte_3pa"
            ),
        ),
        sa.CheckConstraint(
            (
                "two_point_makes "
                "<= two_point_attempts"
            ),
            name=(
                "ck_external_game_player_stats_"
                "2pm_lte_2pa"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["external_game_id"],
            ["external_games.id"],
        ),
        sa.ForeignKeyConstraint(
            ["player_id"],
            ["players.id"],
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
        sa.UniqueConstraint(
            "external_game_id",
            "player_id",
            name=(
                "uq_external_game_player_stats_"
                "game_player"
            ),
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_table(
        "external_game_player_stats"
    )
    op.drop_table(
        "external_games"
    )