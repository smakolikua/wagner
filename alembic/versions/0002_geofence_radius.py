"""Add geofence_radius to users

Revision ID: 0002_geofence_radius
Revises: 0001_initial
Create Date: 2025-06-01 00:00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0002_geofence_radius"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Додаємо колонку тільки якщо її немає (idempotent)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("users")]
    if "geofence_radius" not in columns:
        op.add_column(
            "users",
            sa.Column("geofence_radius", sa.Integer(), nullable=False, server_default="100"),
        )


def downgrade() -> None:
    op.drop_column("users", "geofence_radius")
