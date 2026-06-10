"""Add user_accounts for multi-user profile logins

Revision ID: 0007_user_accounts
Revises: 0006_user_access_pin
Create Date: 2026-06-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007_user_accounts"
down_revision: Union[str, None] = "0006_user_access_pin"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_id"),
    )
    op.create_index("ix_user_accounts_user_id", "user_accounts", ["user_id"])
    op.create_index("ix_user_accounts_telegram_id", "user_accounts", ["telegram_id"], unique=True)

    op.execute(
        """
        INSERT INTO user_accounts (user_id, telegram_id, created_at, updated_at)
        SELECT id, telegram_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        FROM users
        """
    )


def downgrade() -> None:
    op.drop_index("ix_user_accounts_telegram_id", table_name="user_accounts")
    op.drop_index("ix_user_accounts_user_id", table_name="user_accounts")
    op.drop_table("user_accounts")
