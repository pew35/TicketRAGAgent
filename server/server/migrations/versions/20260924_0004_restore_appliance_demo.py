"""restore the English appliance repair demo conversation

Revision ID: 20260924_0004
Revises: 20260923_0003
Create Date: 2026-09-24 08:00:00.000000
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260924_0004"
down_revision: str | None = "20260923_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


DEMO_EMAIL = "demo@ticketragagent.dev"


def upgrade() -> None:
    """Restore the fixed demo case and keep all public content in English."""
    op.execute(
        f"""
        INSERT INTO conversations (
            id, user_id, title, last_message_preview, created_at, updated_at
        ) VALUES (
            '00000000-0000-4000-8000-000000000202',
            (SELECT id FROM users WHERE email = '{DEMO_EMAIL}'),
            'Broken appliance repair contact',
            'Call the repair technician at 4128889799 to arrange appliance service.',
            now(), now()
        )
        ON CONFLICT (id) DO UPDATE SET
            user_id = EXCLUDED.user_id,
            title = EXCLUDED.title,
            last_message_preview = EXCLUDED.last_message_preview,
            deleted_at = NULL,
            updated_at = now()
        """
    )
    op.execute(
        """
        INSERT INTO conversation_messages (
            id, conversation_id, role, status, sequence, content,
            created_at, updated_at
        ) VALUES
        (
            '00000000-0000-4000-8000-000000001003',
            '00000000-0000-4000-8000-000000000202',
            'user', 'completed', 1,
            'My appliance is broken. Who should I call for repairs?',
            now(), now()
        ),
        (
            '00000000-0000-4000-8000-000000001004',
            '00000000-0000-4000-8000-000000000202',
            'assistant', 'completed', 2,
            'Call the repair technician at 4128889799 to arrange appliance service.',
            now(), now()
        )
        ON CONFLICT (id) DO UPDATE SET
            conversation_id = EXCLUDED.conversation_id,
            role = EXCLUDED.role,
            status = EXCLUDED.status,
            sequence = EXCLUDED.sequence,
            content = EXCLUDED.content,
            updated_at = now()
        """
    )


def downgrade() -> None:
    """Leave the public demo records intact when rolling back."""
