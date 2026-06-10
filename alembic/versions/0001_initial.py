"""Initial migration — create all tables

Revision ID: 0001_initial
Revises:
Create Date: 2025-01-01 00:00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id",               sa.Integer(),     nullable=False),
        sa.Column("telegram_id",      sa.BigInteger(),  nullable=False),
        sa.Column("name",             sa.String(100),   nullable=False),
        sa.Column("lang",             sa.String(5),     nullable=False, server_default="de"),
        sa.Column("home_address_id",  sa.Integer(),     nullable=True),
        sa.Column("geofence_radius",  sa.Integer(),     nullable=False, server_default="100"),
        sa.Column("created_at",       sa.DateTime(),    nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at",       sa.DateTime(),    nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_id"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"])

    op.create_table(
        "vehicles",
        sa.Column("id",               sa.Integer(),     nullable=False),
        sa.Column("user_id",          sa.Integer(),     nullable=False),
        sa.Column("make",             sa.String(50),    nullable=False),
        sa.Column("model",            sa.String(50),    nullable=False),
        sa.Column("plate",            sa.String(20),    nullable=False),
        sa.Column("current_mileage",  sa.Float(),       nullable=False, server_default="0"),
        sa.Column("is_active",        sa.Boolean(),     nullable=False, server_default="1"),
        sa.Column("created_at",       sa.DateTime(),    nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at",       sa.DateTime(),    nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vehicles_user_id", "vehicles", ["user_id"])

    op.create_table(
        "addresses",
        sa.Column("id",           sa.Integer(),    nullable=False),
        sa.Column("user_id",      sa.Integer(),    nullable=False),
        sa.Column("label",        sa.String(100),  nullable=False),
        sa.Column("address_str",  sa.String(255),  nullable=False),
        sa.Column("lat",          sa.Float(),      nullable=True),
        sa.Column("lon",          sa.Float(),      nullable=True),
        sa.Column("type",         sa.String(20),   nullable=False, server_default="Sonstiges"),
        sa.Column("created_at",   sa.DateTime(),   nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at",   sa.DateTime(),   nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_addresses_user_id", "addresses", ["user_id"])

    op.create_table(
        "trips",
        sa.Column("id",                 sa.Integer(),    nullable=False),
        sa.Column("user_id",            sa.Integer(),    nullable=False),
        sa.Column("vehicle_id",         sa.Integer(),    nullable=False),
        sa.Column("date",               sa.Date(),       nullable=False),
        sa.Column("start_address_id",   sa.Integer(),    nullable=True),
        sa.Column("end_address_id",     sa.Integer(),    nullable=True),
        sa.Column("start_address_text", sa.String(255),  nullable=True),
        sa.Column("end_address_text",   sa.String(255),  nullable=True),
        sa.Column("start_mileage",      sa.Float(),      nullable=False),
        sa.Column("end_mileage",        sa.Float(),      nullable=False),
        sa.Column("purpose",            sa.String(20),   nullable=False, server_default="geschäftlich"),
        sa.Column("notes",              sa.String(500),  nullable=True),
        sa.Column("is_auto",            sa.Boolean(),    nullable=False, server_default="0"),
        sa.Column("created_at",         sa.DateTime(),   nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at",         sa.DateTime(),   nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"],          ["users.id"],    ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vehicle_id"],        ["vehicles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["start_address_id"], ["addresses.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["end_address_id"],   ["addresses.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trips_user_id", "trips", ["user_id"])

    op.create_table(
        "live_sessions",
        sa.Column("id",               sa.Integer(),   nullable=False),
        sa.Column("user_id",          sa.Integer(),   nullable=False),
        sa.Column("vehicle_id",       sa.Integer(),   nullable=False),
        sa.Column("started_at",       sa.DateTime(),  nullable=False, server_default=sa.func.now()),
        sa.Column("ended_at",         sa.DateTime(),  nullable=True),
        sa.Column("last_lat",         sa.Float(),     nullable=True),
        sa.Column("last_lon",         sa.Float(),     nullable=True),
        sa.Column("last_update",      sa.DateTime(),  nullable=True),
        sa.Column("start_mileage",    sa.Float(),     nullable=False, server_default="0"),
        sa.Column("last_address_id",  sa.Integer(),   nullable=True),
        sa.ForeignKeyConstraint(["user_id"],         ["users.id"],    ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vehicle_id"],       ["vehicles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["last_address_id"], ["addresses.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_live_sessions_user_id", "live_sessions", ["user_id"])


def downgrade() -> None:
    op.drop_table("live_sessions")
    op.drop_table("trips")
    op.drop_table("addresses")
    op.drop_table("vehicles")
    op.drop_table("users")
