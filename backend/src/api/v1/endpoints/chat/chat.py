import logging

from fastapi import APIRouter, Depends

from src.api.v1.endpoints.auth.deps import get_current_user
from src.api.v1.endpoints.chat.deps import get_chat_service
from src.api.v1.endpoints.chat.schemas import (
    CreateSessionRequest,
    MessageResponse,
    SendMessageRequest,
    SessionResponse,
    UpdateSessionRequest,
)
from src.application.chat.dto.chat_dto import CreateSessionDTO, SendMessageDTO, UpdateSessionDTO
from src.application.chat.dto.source_dto import SourceDTO
from src.application.chat.services.chat_application_service import ChatApplicationService
from src.domain.auth.entities.user import User


def _source_dto_to_dict(source: SourceDTO) -> dict:
    return {
        "title": source.title,
        "url": source.url,
        "score": source.score,
        "heritage_type": source.heritage_type,
        "province": source.province,
        "municipality": source.municipality,
        "metadata": source.metadata,
    }

logger = logging.getLogger("iaph.chat.router")

router = APIRouter()


@router.post("/sessions", response_model=SessionResponse, status_code=201)
async def create_session(
    request: CreateSessionRequest,
    user: User = Depends(get_current_user),
    service: ChatApplicationService = Depends(get_chat_service),
) -> SessionResponse:
    """Create a new chat session."""
    dto = CreateSessionDTO(title=request.title, user_id=str(user.id))
    result = await service.create_session(dto)
    return SessionResponse(
        id=result.id,
        title=result.title,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    user: User = Depends(get_current_user),
    service: ChatApplicationService = Depends(get_chat_service),
) -> list[SessionResponse]:
    """List all chat sessions ordered by most recently updated."""
    results = await service.list_sessions(user_id=str(user.id))
    return [
        SessionResponse(
            id=s.id,
            title=s.title,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in results
    ]


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    user: User = Depends(get_current_user),
    service: ChatApplicationService = Depends(get_chat_service),
) -> None:
    """Delete a chat session and all its messages."""
    await service.delete_session(session_id, user_id=str(user.id))


@router.patch("/sessions/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    request: UpdateSessionRequest,
    user: User = Depends(get_current_user),
    service: ChatApplicationService = Depends(get_chat_service),
) -> SessionResponse:
    """Update a chat session title."""
    dto = UpdateSessionDTO(session_id=session_id, title=request.title, user_id=str(user.id))
    result = await service.update_session_title(dto)
    return SessionResponse(
        id=result.id,
        title=result.title,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.get("/sessions/{session_id}/messages", response_model=list[MessageResponse])
async def get_session_messages(
    session_id: str,
    user: User = Depends(get_current_user),
    service: ChatApplicationService = Depends(get_chat_service),
) -> list[MessageResponse]:
    """Get all messages for a chat session."""
    results = await service.get_history(session_id, user_id=str(user.id))
    return [
        MessageResponse(
            id=m.id,
            role=m.role,
            content=m.content,
            sources=[_source_dto_to_dict(s) for s in m.sources],
            created_at=m.created_at,
        )
        for m in results
    ]


@router.post(
    "/sessions/{session_id}/messages",
    response_model=MessageResponse,
    status_code=201,
)
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    user: User = Depends(get_current_user),
    service: ChatApplicationService = Depends(get_chat_service),
) -> MessageResponse:
    """Send a user message, trigger RAG pipeline, and return assistant response."""
    logger.info(
        "POST /chat/sessions/%s/messages content=%r",
        session_id, request.content[:80],
    )

    dto = SendMessageDTO(
        session_id=session_id,
        content=request.content,
        top_k=request.top_k,
        heritage_type_filter=request.heritage_type_filter,
        province_filter=request.province_filter,
        user_id=str(user.id),
    )

    result = await service.send_message(dto)

    logger.info(
        "Response: %d chars, %d sources",
        len(result.content), len(result.sources),
    )

    return MessageResponse(
        id=result.id,
        role=result.role,
        content=result.content,
        sources=[_source_dto_to_dict(s) for s in result.sources],
        created_at=result.created_at,
    )
