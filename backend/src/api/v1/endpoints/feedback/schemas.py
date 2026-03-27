from typing import Literal

from pydantic import BaseModel


class SubmitFeedbackRequest(BaseModel):
    target_type: Literal["route", "search"]
    target_id: str
    value: Literal[-1, 1]
    metadata: dict | None = None


class FeedbackResponse(BaseModel):
    id: str
    target_type: str
    target_id: str
    value: int
    created_at: str


class FeedbackBatchResponse(BaseModel):
    feedbacks: dict[str, int]
