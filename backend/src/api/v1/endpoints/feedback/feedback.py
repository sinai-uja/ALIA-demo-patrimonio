from fastapi import APIRouter, Depends, HTTPException, Query, Response

from src.api.v1.endpoints.auth.deps import get_current_user
from src.api.v1.endpoints.feedback.deps import get_feedback_service
from src.api.v1.endpoints.feedback.schemas import (
    FeedbackBatchResponse,
    FeedbackResponse,
    SubmitFeedbackRequest,
)
from src.application.feedback.dto.feedback_dto import SubmitFeedbackDTO
from src.application.feedback.services.feedback_application_service import (
    FeedbackApplicationService,
)
from src.domain.auth.entities.user import User

router = APIRouter()


@router.put("", response_model=FeedbackResponse)
async def submit_feedback(
    request: SubmitFeedbackRequest,
    user: User = Depends(get_current_user),
    service: FeedbackApplicationService = Depends(get_feedback_service),
) -> FeedbackResponse:
    """Submit or update feedback (thumbs up/down) for a target."""
    dto = SubmitFeedbackDTO(
        target_type=request.target_type,
        target_id=request.target_id,
        value=request.value,
        metadata=request.metadata,
    )
    result = await service.submit_feedback(user.username, dto)
    return FeedbackResponse(
        id=result.id,
        target_type=result.target_type,
        target_id=result.target_id,
        value=result.value,
        created_at=result.created_at,
    )


@router.delete("/{target_type}/{target_id}", status_code=204)
async def delete_feedback(
    target_type: str,
    target_id: str,
    user: User = Depends(get_current_user),
    service: FeedbackApplicationService = Depends(get_feedback_service),
) -> Response:
    """Delete feedback for a specific target."""
    deleted = await service.delete_feedback(user.username, target_type, target_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return Response(status_code=204)


@router.get("/batch", response_model=FeedbackBatchResponse)
async def get_feedback_batch(
    target_type: str,
    target_ids: list[str] = Query(...),
    user: User = Depends(get_current_user),
    service: FeedbackApplicationService = Depends(get_feedback_service),
) -> FeedbackBatchResponse:
    """Get feedback values for multiple targets at once."""
    feedbacks = await service.get_feedback_batch(
        user.username, target_type, target_ids,
    )
    return FeedbackBatchResponse(feedbacks=feedbacks)


@router.get("/{target_type}/{target_id}", response_model=FeedbackResponse)
async def get_feedback(
    target_type: str,
    target_id: str,
    user: User = Depends(get_current_user),
    service: FeedbackApplicationService = Depends(get_feedback_service),
) -> FeedbackResponse:
    """Get feedback for a specific target."""
    result = await service.get_feedback(user.username, target_type, target_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return FeedbackResponse(
        id=result.id,
        target_type=result.target_type,
        target_id=result.target_id,
        value=result.value,
        created_at=result.created_at,
    )
