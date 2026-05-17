"""index balance_area columns on courses

Revision ID: 0005_index_balance_area
Revises: 0004_balance_area
Create Date: 2026-05-17
"""
from alembic import op

revision = "0005_index_balance_area"
down_revision = "0004_balance_area"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_courses_balance_area", "courses", ["balance_area"])
    op.create_index("ix_courses_balance_area_num", "courses", ["balance_area_num"])


def downgrade() -> None:
    op.drop_index("ix_courses_balance_area_num", table_name="courses")
    op.drop_index("ix_courses_balance_area", table_name="courses")
