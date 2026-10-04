"""add message_metrics table

Revision ID: a1b2c3d4e5f6
Revises: 4969d0d3f8ab
Create Date: 2026-10-04

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "4969d0d3f8ab"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "message_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("llm_model", sa.String(length=255), nullable=True),
        sa.Column("rag_strategy", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id"),
    )
    op.create_index(op.f("ix_message_metrics_message_id"), "message_metrics", ["message_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_message_metrics_message_id"), table_name="message_metrics")
    op.drop_table("message_metrics")
