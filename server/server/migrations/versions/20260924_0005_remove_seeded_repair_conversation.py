"""remove the mistakenly seeded repair conversation

Revision ID: 20260924_0005
Revises: 20260924_0004
Create Date: 2026-09-24 08:15:00.000000
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260924_0005"
down_revision: str | None = "20260924_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Remove the fixed conversation; the knowledge-base row remains in the CSV."""
    op.execute(
        """
        DELETE FROM conversation_messages
        WHERE conversation_id = '00000000-0000-4000-8000-000000000202'
        """
    )
    op.execute(
        """
        DELETE FROM conversations
        WHERE id = '00000000-0000-4000-8000-000000000202'
        """
    )


def downgrade() -> None:
    """Do not recreate content that should only exist in the knowledge base."""
