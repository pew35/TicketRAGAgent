"""preserve the deployed migration chain

Revision ID: 20260924_0004
Revises: 20260923_0003
Create Date: 2026-09-24 08:00:00.000000
"""

from collections.abc import Sequence


revision: str = "20260924_0004"
down_revision: str | None = "20260923_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Retain this applied revision without seeding additional demo content."""


def downgrade() -> None:
    """Retain this migration as a no-op in both directions."""
