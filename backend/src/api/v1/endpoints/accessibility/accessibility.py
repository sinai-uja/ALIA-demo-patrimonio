from fastapi import APIRouter, Depends

from src.api.v1.endpoints.accessibility.deps import get_accessibility_service
from src.api.v1.endpoints.accessibility.schemas import SimplifyRequest, SimplifyResponse
from src.application.accessibility.dto.accessibility_dto import SimplifyTextDTO
from src.application.accessibility.services.accessibility_application_service import (
    AccessibilityApplicationService,
)

router = APIRouter()


@router.post("/simplify", response_model=SimplifyResponse)
async def simplify_text(
    request: SimplifyRequest,
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
