"""add balance_area columns to courses

Revision ID: 0004_balance_area
Revises: 0003_add_username_name
Create Date: 2026-05-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_balance_area"
down_revision = "0003_add_username_name"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("courses", sa.Column("balance_area", sa.String(50), nullable=True))
    op.add_column("courses", sa.Column("balance_area_num", sa.SmallInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("courses", "balance_area_num")
    op.drop_column("courses", "balance_area")
