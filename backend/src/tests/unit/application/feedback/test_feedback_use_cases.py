"""Tests for feedback use cases (submit, get, get_batch, delete)."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from src.application.feedback.dto.feedback_dto import FeedbackDTO, SubmitFeedbackDTO
from src.application.feedback.use_cases.delete_feedback import DeleteFeedbackUseCase
from src.application.feedback.use_cases.get_feedback import GetFeedbackUseCase
from src.application.feedback.use_cases.get_feedback_batch import GetFeedbackBatchUseCase
from src.application.feedback.use_cases.submit_feedback import SubmitFeedbackUseCase
from src.domain.feedback.entities.feedback import Feedback


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC)
_USER_ID = "user-1"


def _make_feedback_entity():
    return Feedback(
        id=uuid.uuid4(),
        user_id=_USER_ID,
        target_type="search",
        target_id="search-123",
        value=1,
        metadata=None,
        created_at=_NOW,
        updated_at=_NOW,
    )


# ---------------------------------------------------------------------------
# SubmitFeedbackUseCase
# ---------------------------------------------------------------------------


@pytest.fixture
def submit_uc(mock_uow):
    repo = AsyncMock()
    repo.upsert.return_value = _make_feedback_entity()
    return SubmitFeedbackUseCase(feedback_repository=repo, unit_of_work=mock_uow), repo


@pytest.mark.asyncio
async def test_submit_feedback_returns_dto(submit_uc):
    uc, _ = submit_uc
    dto = SubmitFeedbackDTO(target_type="search", target_id="search-123", value=1)
    result = await uc.execute(_USER_ID, dto)
    assert isinstance(result, FeedbackDTO)
    assert result.user_id == _USER_ID
    assert result.value == 1


@pytest.mark.asyncio
async def test_submit_feedback_uow_wraps_write(submit_uc, mock_uow):
    uc, _ = submit_uc
    dto = SubmitFeedbackDTO(target_type="search", target_id="s1", value=-1)
    await uc.execute(_USER_ID, dto)
    mock_uow.__aenter__.assert_awaited()
    mock_uow.__aexit__.assert_awaited()


# ---------------------------------------------------------------------------
# GetFeedbackUseCase
# ---------------------------------------------------------------------------


@pytest.fixture
def get_uc():
    repo = AsyncMock()
    repo.get.return_value = _make_feedback_entity()
    return GetFeedbackUseCase(feedback_repository=repo), repo


@pytest.mark.asyncio
async def test_get_feedback_returns_dto(get_uc):
    uc, _ = get_uc
    result = await uc.execute(_USER_ID, "search", "search-123")
    assert isinstance(result, FeedbackDTO)


@pytest.mark.asyncio
async def test_get_feedback_not_found_returns_none(get_uc):
    uc, repo = get_uc
    repo.get.return_value = None
    result = await uc.execute(_USER_ID, "search", "nonexistent")
    assert result is None


# ---------------------------------------------------------------------------
# GetFeedbackBatchUseCase
# ---------------------------------------------------------------------------


@pytest.fixture
def batch_uc():
    repo = AsyncMock()
    fb = _make_feedback_entity()
    repo.get_batch.return_value = [fb]
    return GetFeedbackBatchUseCase(feedback_repository=repo), repo


@pytest.mark.asyncio
async def test_get_feedback_batch_returns_dict(batch_uc):
    uc, _ = batch_uc
    result = await uc.execute(_USER_ID, "search", ["search-123"])
    assert isinstance(result, dict)
    assert "search-123" in result


# ---------------------------------------------------------------------------
# DeleteFeedbackUseCase
# ---------------------------------------------------------------------------


@pytest.fixture
def delete_uc(mock_uow):
    repo = AsyncMock()
    repo.delete.return_value = True
    return DeleteFeedbackUseCase(feedback_repository=repo, unit_of_work=mock_uow), repo


@pytest.mark.asyncio
async def test_delete_feedback_returns_true(delete_uc):
    uc, _ = delete_uc
    result = await uc.execute(_USER_ID, "search", "search-123")
    assert result is True


@pytest.mark.asyncio
async def test_delete_feedback_returns_false_when_not_found(delete_uc):
    uc, repo = delete_uc
    repo.delete.return_value = False
    result = await uc.execute(_USER_ID, "search", "nonexistent")
    assert result is False


@pytest.mark.asyncio
async def test_delete_feedback_uow_wraps_write(delete_uc, mock_uow):
    uc, _ = delete_uc
    await uc.execute(_USER_ID, "search", "s1")
    mock_uow.__aenter__.assert_awaited()
    mock_uow.__aexit__.assert_awaited()
