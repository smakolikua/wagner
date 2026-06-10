"""Idempotent check — new tables already created by 0003

Revision ID: 0004_new_tables_check
Revises: 0003_receipts_and_taxes
Create Date: 2025-06-02
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_new_tables_check"
down_revision = "0003_receipts_and_taxes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Перевіряємо що всі колонки присутні (idempotent)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    for tbl in ["categories", "receipts", "tax_periods"]:
        if tbl not in tables:
            raise Exception(f"Table {tbl} missing — run migration 0003 first")


def downgrade() -> None:
    pass
