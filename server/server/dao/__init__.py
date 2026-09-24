"""Database access objects for the Ticket RAG server."""

from .agent_run import (
    create_agent_run,
    get_agent_run_by_id,
    mark_agent_run_failed,
    mark_agent_run_success,
)
from .conversation import (
    create_conversation,
    create_message,
    get_conversation_by_id,
    get_next_message_sequence,
    list_conversation_messages,
    list_user_conversations,
    soft_delete_conversation,
    update_conversation_title,
)
from .user import (
    create_user,
    delete_user,
    get_user_by_email,
    get_user_by_id,
    list_users,
    set_user_active,
    update_user,
    update_user_password,
)

__all__ = [
    "create_agent_run",
    "create_conversation",
    "create_message",
    "create_user",
    "delete_user",
    "get_agent_run_by_id",
    "get_conversation_by_id",
    "get_next_message_sequence",
    "get_user_by_email",
    "get_user_by_id",
    "list_users",
    "list_conversation_messages",
    "list_user_conversations",
    "mark_agent_run_failed",
    "mark_agent_run_success",
    "set_user_active",
    "soft_delete_conversation",
    "update_user",
    "update_conversation_title",
    "update_user_password",
]
