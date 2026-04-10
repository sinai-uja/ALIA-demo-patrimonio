from fastapi import APIRouter, Depends

from src.api.v1.endpoints.accessibility.deps import get_accessibility_service
from src.api.v1.endpoints.accessibility.schemas import SimplifyRequest, SimplifyResponse
from src.api.v1.endpoints.auth.deps import get_current_user
from src.application.accessibility.dto.accessibility_dto import SimplifyTextDTO
from src.application.accessibility.services.accessibility_application_service import (
    AccessibilityApplicationService,
)
from src.domain.auth.entities.user import User

router = APIRouter()


@router.post("/simplify", response_model=SimplifyResponse)
async def simplify_text(
    request: SimplifyRequest,
    user: User = Depends(get_current_user),
    service: AccessibilityApplicationService = Depends(get_accessibility_service),
) -> SimplifyResponse:
    """Simplify heritage text following Lectura Facil guidelines."""
    dto = SimplifyTextDTO(
        text=request.text,
        level=request.level,
        document_id=request.document_id,
    )

    result = await service.simplify_text(dto)

    return SimplifyResponse(
        original_text=result.original_text,
        simplified_text=result.simplified_text,
        level=result.level,
        document_id=result.document_id,
    )
