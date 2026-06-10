"""Add user account roles

Revision ID: 0009_user_account_roles
Revises: 0008_audit_logs
Create Date: 2026-06-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0009_user_account_roles"
down_revision: Union[str, None] = "0008_audit_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("user_accounts") as batch_op:
        batch_op.add_column(sa.Column("role", sa.String(length=20), nullable=True))
    op.execute("UPDATE user_accounts SET role = 'owner' WHERE role IS NULL")
    with op.batch_alter_table("user_accounts") as batch_op:
        batch_op.alter_column("role", nullable=False, server_default="driver")


def downgrade() -> None:
    with op.batch_alter_table("user_accounts") as batch_op:
        batch_op.drop_column("role")
