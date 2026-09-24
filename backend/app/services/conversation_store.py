"""ORCA Marine Intelligence - Conversation Context Store

Maintains explicit, structured conversation sessions isolated by conversation_id.
Avoids dumping raw chat history; stores typed, validated multi-turn state.
"""

import threading
from typing import Dict, Optional
from datetime import datetime, timezone

from app.models.schemas import ConversationContext
from app.services.storage import storage_repo


class ConversationStore:
    """Thread-safe persistent store for multi-turn structured conversation contexts."""

    def __init__(self):
        self._lock = threading.RLock()
        self._contexts: Dict[str, ConversationContext] = {}

    def get_context(self, conversation_id: str) -> Optional[ConversationContext]:
        """Retrieve existing structured context for a conversation session."""
        with self._lock:
            ctx = self._contexts.get(conversation_id)
            if ctx:
                return ctx.model_copy(deep=True)
            # Rehydrate from persistent storage
            persisted = storage_repo.get_conversation(conversation_id)
            if persisted:
                try:
                    rehydrated = ConversationContext(**persisted)
                    self._contexts[conversation_id] = rehydrated
                    return rehydrated.model_copy(deep=True)
                except Exception:
                    pass
            return None

    def get_or_create(self, conversation_id: str) -> ConversationContext:
        """Retrieve existing context or instantiate an unpopulated initial context."""
        with self._lock:
            ctx = self.get_context(conversation_id)
            if ctx:
                return ctx
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
            storage_repo.save_conversation(conversation_id, new_ctx.model_dump())
            return new_ctx.model_copy(deep=True)

    def save_context(self, context: ConversationContext) -> None:
        """Persist updated context for a conversation session."""
        with self._lock:
            context.updated_at = datetime.now(timezone.utc).isoformat()
            self._contexts[context.conversation_id] = context.model_copy(deep=True)
            try:
                storage_repo.save_conversation(context.conversation_id, context.model_dump())
            except Exception:
                pass

    def clear_context(self, conversation_id: str) -> None:
        """Remove conversation session context."""
        with self._lock:
            self._contexts.pop(conversation_id, None)
            try:
                storage_repo.delete_conversation(conversation_id)
            except Exception:
                pass

    def has_context(self, conversation_id: str) -> bool:
        """Check whether a session exists."""
        with self._lock:
            if conversation_id in self._contexts:
                return True
            return storage_repo.get_conversation(conversation_id) is not None


# Singleton instance
conversation_store = ConversationStore()
