"""translate previously seeded demo content to English

Revision ID: 20260923_0003
Revises: 20260923_0002
Create Date: 2026-09-23 23:45:00.000000
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260923_0003"
down_revision: str | None = "20260923_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Replace the previously deployed localized demo records with English."""
    op.execute(
        """
        UPDATE conversations
        SET
            title = 'Broken appliance repair contact',
            last_message_preview = 'Call the repair technician at 4128889799 to arrange appliance service.',
            updated_at = now()
        WHERE id = '00000000-0000-4000-8000-000000000202'
        """
    )
    op.execute(
        """
        UPDATE conversation_messages
        SET
            content = CASE id
                WHEN '00000000-0000-4000-8000-000000001003'
                    THEN 'My appliance is broken. Who should I call for repairs?'
                WHEN '00000000-0000-4000-8000-000000001004'
                    THEN 'Call the repair technician at 4128889799 to arrange appliance service.'
            END,
            updated_at = now()
        WHERE id IN (
            '00000000-0000-4000-8000-000000001003',
            '00000000-0000-4000-8000-000000001004'
        )
        """
    )


def downgrade() -> None:
    """Keep demo content in English when rolling back this cleanup."""
