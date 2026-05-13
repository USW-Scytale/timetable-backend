"""buildings: add campus coords + walk_edges table

Revision ID: 0002_buildings_walk_edges
Revises: 0001_baseline
Create Date: 2026-05-13
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_buildings_walk_edges"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("buildings", sa.Column("x", sa.Float(), nullable=True))
    op.add_column("buildings", sa.Column("y", sa.Float(), nullable=True))
    op.add_column("buildings", sa.Column("elev", sa.Integer(), nullable=True))
    op.add_column("buildings", sa.Column("terrain", sa.String(length=30), nullable=True))
    op.add_column("buildings", sa.Column("aliases", sa.JSON(), nullable=True))

    op.create_table(
        "walk_edges",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("from_building_id", sa.String(length=20), nullable=False),
        sa.Column("to_building_id", sa.String(length=20), nullable=False),
        sa.Column("distance_meters", sa.Integer(), nullable=False),
        sa.Column("profile", sa.String(length=20), nullable=False, server_default="flat"),
        sa.ForeignKeyConstraint(["from_building_id"], ["buildings.building_id"]),
        sa.ForeignKeyConstraint(["to_building_id"], ["buildings.building_id"]),
    )


def downgrade() -> None:
    op.drop_table("walk_edges")
    op.drop_column("buildings", "aliases")
    op.drop_column("buildings", "terrain")
    op.drop_column("buildings", "elev")
    op.drop_column("buildings", "y")
    op.drop_column("buildings", "x")
