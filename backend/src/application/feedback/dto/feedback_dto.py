from dataclasses import dataclass


@dataclass(frozen=True)
class SubmitFeedbackDTO:
    """Input DTO for submitting feedback."""

    target_type: str
    target_id: str
    value: int
    metadata: dict | None = None


@dataclass(frozen=True)
class FeedbackDTO:
    """Output DTO representing persisted feedback."""

    id: str
    user_id: str
    target_type: str
    target_id: str
    value: int
    created_at: str
    updated_at: str
