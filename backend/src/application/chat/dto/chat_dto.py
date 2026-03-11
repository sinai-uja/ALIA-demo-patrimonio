from dataclasses import dataclass, field


@dataclass(frozen=True)
class CreateSessionDTO:
    """Input DTO for creating a new chat session."""

    title: str = "Nueva conversación"


@dataclass(frozen=True)
class SessionDTO:
    """Output DTO representing a chat session."""

    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0


@dataclass(frozen=True)
class SendMessageDTO:
    """Input DTO for sending a message in a session."""

    session_id: str
    content: str
    top_k: int = 5
    heritage_type_filter: str | None = None
    province_filter: str | None = None


@dataclass(frozen=True)
class MessageDTO:
    """Output DTO representing a single chat message."""

    id: str
    session_id: str
    role: str
    content: str
    sources: list[dict] = field(default_factory=list)
    created_at: str = ""
