"""Tests for SimplifyTextUseCase — accessibility context."""

from unittest.mock import AsyncMock

import pytest

from src.application.accessibility.dto.accessibility_dto import SimplifiedTextDTO, SimplifyTextDTO
from src.application.accessibility.use_cases.simplify_text_use_case import SimplifyTextUseCase
from src.application.shared.exceptions import LLMUnavailableError, ValidationError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def llm_port():
    port = AsyncMock()
    port.simplify.return_value = "simplified text"
    return port


@pytest.fixture
def use_case(llm_port):
    return SimplifyTextUseCase(llm_port=llm_port)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_happy_path_basic_level(use_case):
    dto = SimplifyTextDTO(text="complex text", level="basic")
    result = await use_case.execute(dto)
    assert isinstance(result, SimplifiedTextDTO)
    assert result.simplified_text == "simplified text"
    assert result.level == "basic"
    assert result.original_text == "complex text"


@pytest.mark.asyncio
async def test_happy_path_intermediate_level(use_case):
    dto = SimplifyTextDTO(text="complex text", level="intermediate")
    result = await use_case.execute(dto)
    assert result.level == "intermediate"


@pytest.mark.asyncio
async def test_invalid_level_raises_validation_error(use_case):
    dto = SimplifyTextDTO(text="text", level="invalid_level")
    with pytest.raises(ValidationError, match="Invalid simplification level"):
        await use_case.execute(dto)


@pytest.mark.asyncio
async def test_llm_failure_propagates(use_case, llm_port):
    llm_port.simplify.side_effect = LLMUnavailableError("LLM down")
    dto = SimplifyTextDTO(text="text", level="basic")
    with pytest.raises(LLMUnavailableError):
        await use_case.execute(dto)
