"""seed the public demo account and repair invalid conversation titles

Revision ID: 20260923_0002
Revises: 20260825_0001
Create Date: 2026-09-23 23:20:00.000000
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260923_0002"
down_revision: str | None = "20260825_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


DEMO_EMAIL = "demo@ticketragagent.dev"
DEMO_PASSWORD_HASH = "$2b$12$RcS2e73pgQZZlfC5KKRU8.llLVn4FBjHMuo.Vdp9NGHBFDL.qr2Da"


def upgrade() -> None:
    """Repair sentinel titles and create deterministic public demo content."""
    op.execute(
        """
        UPDATE conversations AS conversation
        SET
            title = COALESCE(
                (
                    SELECT CASE
                        WHEN length(replace(message.content, E'\n', ' ')) > 60
                            THEN left(replace(message.content, E'\n', ' '), 57) || '...'
                        ELSE replace(message.content, E'\n', ' ')
                    END
                    FROM conversation_messages AS message
                    WHERE message.conversation_id = conversation.id
                      AND message.role = 'user'
                    ORDER BY message.sequence
                    LIMIT 1
                ),
                'New Chat'
            ),
            updated_at = now()
        WHERE lower(btrim(conversation.title)) IN (
            'none', 'null', 'undefined', 'n/a', 'na'
        )
        """
    )

    op.execute(
        f"""
        INSERT INTO users (
            id, email, hashed_password, display_name, is_active, is_superuser,
            created_at, updated_at
        ) VALUES (
            '00000000-0000-4000-8000-000000000100',
            '{DEMO_EMAIL}',
            '{DEMO_PASSWORD_HASH}',
            'Demo User', true, false, now(), now()
        )
        ON CONFLICT (email) DO UPDATE SET
            hashed_password = EXCLUDED.hashed_password,
            display_name = EXCLUDED.display_name,
            is_active = true,
            updated_at = now()
        """
    )

    op.execute(
        f"""
        INSERT INTO conversations (
            id, user_id, title, last_message_preview, created_at, updated_at
        ) VALUES
        (
            '00000000-0000-4000-8000-000000000201',
            (SELECT id FROM users WHERE email = '{DEMO_EMAIL}'),
            'Damaged coffee maker replacement',
            'We will arrange a replacement and provide recycling instructions.',
            now(), now()
        ),
        (
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
            '00000000-0000-4000-8000-000000001001',
            '00000000-0000-4000-8000-000000000201',
            'user', 'completed', 1,
            'My coffee maker arrived damaged. What should support do?',
            now(), now()
        ),
        (
            '00000000-0000-4000-8000-000000001002',
            '00000000-0000-4000-8000-000000000201',
            'assistant', 'completed', 2,
            'We will arrange a replacement shipment and provide instructions for recycling the damaged unit.',
            now(), now()
        ),
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
    """Remove seeded conversations while preserving the shared user account."""
    op.execute(
        """
        DELETE FROM conversation_messages
        WHERE id IN (
            '00000000-0000-4000-8000-000000001001',
            '00000000-0000-4000-8000-000000001002',
            '00000000-0000-4000-8000-000000001003',
            '00000000-0000-4000-8000-000000001004'
        )
        """
    )
    op.execute(
        """
        DELETE FROM conversations
        WHERE id IN (
            '00000000-0000-4000-8000-000000000201',
            '00000000-0000-4000-8000-000000000202'
        )
        """
    )
