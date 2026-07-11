"""add conversation memory columns

Revision ID: 0002_add_memory_columns
Revises: 0001_add_call_summary
Create Date: 2026-07-10

"""
from alembic import op
import sqlalchemy as sa

revision = "0002_add_memory_columns"
down_revision = "0001_add_call_summary"
branch_labels = None
depends_on = None


def upgrade():
    # batch_alter_table is required for SQLite, which can't ALTER TABLE
    # directly; on Postgres/MySQL this runs as a normal ALTER TABLE.
    with op.batch_alter_table("calls") as batch_op:
        batch_op.add_column(sa.Column("memory_summary", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "memory_summary_turns_covered",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )


def downgrade():
    with op.batch_alter_table("calls") as batch_op:
        batch_op.drop_column("memory_summary_turns_covered")
        batch_op.drop_column("memory_summary")