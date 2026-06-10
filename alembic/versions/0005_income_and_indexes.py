"""Add incomes table + receipt indexes

Revision ID: 0005_income_and_indexes
Revises: 0004_new_tables_check
Create Date: 2025-06-03
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0005_income_and_indexes"
down_revision: Union[str, None] = "0004_new_tables_check"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "incomes",
        sa.Column("id",                   sa.Integer(),    nullable=False),
        sa.Column("user_id",              sa.Integer(),    nullable=False),
        sa.Column("date",                 sa.Date(),       nullable=False),
        sa.Column("amount",               sa.Float(),      nullable=False),
        sa.Column("vat_amount",           sa.Float(),      nullable=False, server_default="0"),
        sa.Column("vat_rate",             sa.Integer(),    nullable=False, server_default="0"),
        sa.Column("description",          sa.String(500),  nullable=True),
        sa.Column("invoice_number",       sa.String(100),  nullable=True),
        sa.Column("client_name",          sa.String(200),  nullable=True),
        sa.Column("is_kleinunternehmer",  sa.Boolean(),    nullable=False, server_default="0"),
        sa.Column("created_at",           sa.DateTime(),   nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at",           sa.DateTime(),   nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_incomes_user_id", "incomes", ["user_id"])
    op.create_index("ix_incomes_date",    "incomes", ["date"])

    # Додаємо індекси для фільтрації чеків по даті і категорії
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = [idx["name"] for idx in inspector.get_indexes("receipts")]
    if "ix_receipts_date" not in existing:
        op.create_index("ix_receipts_date",        "receipts", ["date"])
    if "ix_receipts_category_id" not in existing:
        op.create_index("ix_receipts_category_id", "receipts", ["category_id"])
    if "ix_receipts_is_business" not in existing:
        op.create_index("ix_receipts_is_business", "receipts", ["is_business"])


def downgrade() -> None:
    op.drop_table("incomes")
    op.drop_index("ix_receipts_date",        table_name="receipts")
    op.drop_index("ix_receipts_category_id", table_name="receipts")
    op.drop_index("ix_receipts_is_business", table_name="receipts")
