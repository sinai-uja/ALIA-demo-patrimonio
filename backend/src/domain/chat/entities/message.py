from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from src.domain.chat.entities.message_role import MessageRole


@dataclass
class Message:
    """A single message within a chat session."""

    id: UUID
    session_id: UUID
    role: MessageRole
    content: str
    sources: list[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
