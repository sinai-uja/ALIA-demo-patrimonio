from uuid import UUID

from src.application.chat.dto.chat_dto import MessageDTO
from src.application.chat.dto.source_dto import SourceDTO
from src.domain.chat.ports.chat_repository import ChatRepository


def _source_dict_to_dto(source: dict) -> SourceDTO:
    return SourceDTO(
        title=source.get("title", ""),
        url=source.get("url", ""),
        score=float(source.get("score", 0.0)),
        heritage_type=source.get("heritage_type", ""),
        province=source.get("province", ""),
        municipality=source.get("municipality"),
        metadata=source.get("metadata"),
    )


class GetSessionHistoryUseCase:
    """Retrieves all messages for a given chat session."""

    def __init__(self, chat_repository: ChatRepository) -> None:
        self._chat_repository = chat_repository

    async def execute(self, session_id: str) -> list[MessageDTO]:
        messages = await self._chat_repository.get_messages(UUID(session_id))
        return [
            MessageDTO(
                id=str(msg.id),
                session_id=str(msg.session_id),
                role=msg.role.value,
                content=msg.content,
                sources=[_source_dict_to_dto(s) for s in msg.sources],
                created_at=msg.created_at.isoformat(),
            )
            for msg in messages
        ]
