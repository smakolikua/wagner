"""Add user access PIN hash

Revision ID: 0006_user_access_pin
Revises: 0005_income_and_indexes
Create Date: 2026-06-09
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0006_user_access_pin"
down_revision: Union[str, None] = "0005_income_and_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("access_pin_hash", sa.String(length=64), nullable=True))
        batch_op.create_index("ix_users_access_pin_hash", ["access_pin_hash"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_access_pin_hash")
        batch_op.drop_column("access_pin_hash")
