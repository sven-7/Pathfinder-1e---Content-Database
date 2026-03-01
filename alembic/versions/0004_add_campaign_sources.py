"""Add campaign_sources junction table for per-campaign source filtering.

Revision ID: 0004
Revises: 0003
Create Date: 2026-02-28

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "campaign_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", sa.Integer, nullable=False),
    )
    op.create_index("idx_campaign_sources_campaign", "campaign_sources", ["campaign_id"])
    op.create_unique_constraint("uq_campaign_source", "campaign_sources", ["campaign_id", "source_id"])


def downgrade() -> None:
    op.drop_table("campaign_sources")
