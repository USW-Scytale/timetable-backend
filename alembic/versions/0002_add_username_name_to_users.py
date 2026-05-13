"""add username and name to users

Revision ID: 0002_add_username_name
Revises: 0001_baseline
Create Date: 2026-05-13
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_add_username_name"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(100), nullable=True))
    op.add_column("users", sa.Column("name", sa.String(100), nullable=True))
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    # email is no longer required for new accounts
    op.alter_column("users", "email", nullable=True)


def downgrade() -> None:
    op.alter_column("users", "email", nullable=False)
    op.drop_index("ix_users_username", table_name="users")
    op.drop_column("users", "name")
    op.drop_column("users", "username")
