from datetime import UTC, datetime

from src.application.accessibility.dto.accessibility_dto import SimplifiedTextDTO, SimplifyTextDTO
from src.domain.accessibility.ports.llm_port import LLMPort
from src.domain.accessibility.value_objects.simplification_level import SimplificationLevel


class SimplifyTextUseCase:
    """Orchestrates text simplification using the LLM port."""

    def __init__(self, llm_port: LLMPort) -> None:
        self._llm_port = llm_port

    async def execute(self, dto: SimplifyTextDTO) -> SimplifiedTextDTO:
        # 1. Validate level maps to SimplificationLevel enum
        try:
            level = SimplificationLevel(dto.level)
        except ValueError:
            valid = [lvl.value for lvl in SimplificationLevel]
            msg = f"Invalid simplification level '{dto.level}'. Valid levels: {valid}"
            raise ValueError(msg)

        # 2. Call LLM port to simplify
        simplified = await self._llm_port.simplify(dto.text, level)

        # 3. Return result DTO
        return SimplifiedTextDTO(
            original_text=dto.text,
            simplified_text=simplified,
            level=level.value,
            document_id=dto.document_id,
            created_at=datetime.now(UTC).isoformat(),
        )
