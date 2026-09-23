"""ORCA Marine Intelligence - Conversation Context Store

Maintains explicit, structured conversation sessions isolated by conversation_id.
Avoids dumping raw chat history; stores typed, validated multi-turn state.
"""

import threading
from typing import Dict, Optional
from datetime import datetime, timezone

from app.models.schemas import ConversationContext


class ConversationStore:
    """Thread-safe in-memory store for multi-turn structured conversation contexts."""

    def __init__(self):
        self._lock = threading.Lock()
        self._contexts: Dict[str, ConversationContext] = {}

    def get_context(self, conversation_id: str) -> Optional[ConversationContext]:
        """Retrieve existing structured context for a conversation session."""
        with self._lock:
            ctx = self._contexts.get(conversation_id)
            if ctx:
                return ctx.model_copy(deep=True)
            return None

    def get_or_create(self, conversation_id: str) -> ConversationContext:
        """Retrieve existing context or instantiate an unpopulated initial context."""
        with self._lock:
            if conversation_id in self._contexts:
                return self._contexts[conversation_id].model_copy(deep=True)
            new_ctx = ConversationContext(
                conversation_id=conversation_id,
                location=None,
                date=None,
                time_window=None,
                activity=None,
                last_intent=None,
                selected_pfz=None,
                turn_count=0,
                updated_at=datetime.now(timezone.utc).isoformat()
            )
            self._contexts[conversation_id] = new_ctx
            return new_ctx.model_copy(deep=True)

    def save_context(self, context: ConversationContext) -> None:
        """Persist updated context for a conversation session."""
        with self._lock:
            context.updated_at = datetime.now(timezone.utc).isoformat()
            self._contexts[context.conversation_id] = context.model_copy(deep=True)

    def clear_context(self, conversation_id: str) -> None:
        """Remove conversation session context."""
        with self._lock:
            self._contexts.pop(conversation_id, None)

    def has_context(self, conversation_id: str) -> bool:
        """Check whether a session exists."""
        with self._lock:
            return conversation_id in self._contexts


# Singleton instance
conversation_store = ConversationStore()
