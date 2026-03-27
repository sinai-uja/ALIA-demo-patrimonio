from abc import ABC, abstractmethod

from src.domain.feedback.entities.feedback import Feedback


class FeedbackRepository(ABC):
    """Port for persisting and retrieving user feedback."""

    @abstractmethod
    async def upsert(self, feedback: Feedback) -> Feedback: ...

    @abstractmethod
    async def delete(
        self, user_id: str, target_type: str, target_id: str,
    ) -> bool: ...

    @abstractmethod
    async def get(
        self, user_id: str, target_type: str, target_id: str,
    ) -> Feedback | None: ...

    @abstractmethod
    async def get_batch(
        self, user_id: str, target_type: str, target_ids: list[str],
    ) -> list[Feedback]: ...
