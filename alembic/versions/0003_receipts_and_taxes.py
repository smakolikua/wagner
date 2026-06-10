"""Add receipts, categories, tax_periods

Revision ID: 0003_receipts_and_taxes
Revises: 0002_geofence_radius
Create Date: 2025-06-01 00:00:01
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0003_receipts_and_taxes"
down_revision: Union[str, None] = "0002_geofence_radius"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id",          sa.Integer(),    nullable=False),
        sa.Column("user_id",     sa.Integer(),    nullable=True),
        sa.Column("name",        sa.String(100),  nullable=False),
        sa.Column("tax_code",    sa.String(50),   nullable=False, server_default="Sonstige BA"),
        sa.Column("description", sa.String(255),  nullable=True),
        sa.Column("is_default",  sa.Boolean(),    nullable=False, server_default="0"),
        sa.Column("sort_order",  sa.Integer(),    nullable=False, server_default="0"),
        sa.Column("created_at",  sa.DateTime(),   nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at",  sa.DateTime(),   nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_categories_user_id", "categories", ["user_id"])

    op.create_table(
        "receipts",
        sa.Column("id",              sa.Integer(),    nullable=False),
        sa.Column("user_id",         sa.Integer(),    nullable=False),
        sa.Column("category_id",     sa.Integer(),    nullable=True),
        sa.Column("trip_id",         sa.Integer(),    nullable=True),
        sa.Column("date",            sa.Date(),       nullable=False),
        sa.Column("amount_gross",    sa.Float(),      nullable=False),
        sa.Column("amount_net",      sa.Float(),      nullable=True),
        sa.Column("vat_amount",      sa.Float(),      nullable=True),
        sa.Column("vat_rate",        sa.Integer(),    nullable=False, server_default="0"),
        sa.Column("vendor",          sa.String(200),  nullable=True),
        sa.Column("description",     sa.String(500),  nullable=True),
        sa.Column("photo_file_id",   sa.String(255),  nullable=True),
        sa.Column("raw_ocr_text",    sa.Text(),       nullable=True),
        sa.Column("ai_confidence",   sa.Float(),      nullable=True),
        sa.Column("is_business",     sa.Boolean(),    nullable=False, server_default="1"),
        sa.Column("is_verified",     sa.Boolean(),    nullable=False, server_default="0"),
        sa.Column("created_at",      sa.DateTime(),   nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at",      sa.DateTime(),   nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"],     ["users.id"],      ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["trip_id"],     ["trips.id"],      ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_receipts_user_id", "receipts", ["user_id"])
    op.create_index("ix_receipts_trip_id", "receipts", ["trip_id"])

    op.create_table(
        "tax_periods",
        sa.Column("id",             sa.Integer(),   nullable=False),
        sa.Column("user_id",        sa.Integer(),   nullable=False),
        sa.Column("year",           sa.Integer(),   nullable=False),
        sa.Column("quarter",        sa.Integer(),   nullable=True),
        sa.Column("total_income",   sa.Float(),     nullable=False, server_default="0"),
        sa.Column("total_expenses", sa.Float(),     nullable=False, server_default="0"),
        sa.Column("vat_collected",  sa.Float(),     nullable=False, server_default="0"),
        sa.Column("vat_paid",       sa.Float(),     nullable=False, server_default="0"),
        sa.Column("vat_to_pay",     sa.Float(),     nullable=False, server_default="0"),
        sa.Column("status",         sa.String(20),  nullable=False, server_default="draft"),
        sa.Column("notes",          sa.String(500), nullable=True),
        sa.Column("created_at",     sa.DateTime(),  nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at",     sa.DateTime(),  nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tax_periods_user_id", "tax_periods", ["user_id"])


def downgrade() -> None:
    op.drop_table("tax_periods")
    op.drop_table("receipts")
    op.drop_table("categories")
