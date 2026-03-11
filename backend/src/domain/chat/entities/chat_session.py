from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class ChatSession:
    """A conversation session that groups related messages."""

    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
