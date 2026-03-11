from fastapi import APIRouter, Depends, HTTPException

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

    try:
        result = await service.simplify_text(dto)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Simplification service error: {exc}"
        ) from exc

    return SimplifyResponse(
        original_text=result.original_text,
        simplified_text=result.simplified_text,
        level=result.level,
        document_id=result.document_id,
    )
