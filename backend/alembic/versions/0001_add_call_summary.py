"""add call summary columns

Revision ID: 0001_add_call_summary
Revises:
Create Date: 2026-07-09

"""
from alembic import op
import sqlalchemy as sa

revision = "0001_add_call_summary"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # batch_alter_table is required for SQLite, which can't ALTER TABLE
    # directly; on Postgres/MySQL this runs as a normal ALTER TABLE.
    with op.batch_alter_table("calls") as batch_op:
        batch_op.add_column(sa.Column("summary", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("summary_generated_at", sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table("calls") as batch_op:
        batch_op.drop_column("summary_generated_at")
        batch_op.drop_column("summary")
