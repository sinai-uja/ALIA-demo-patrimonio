from src.application.accessibility.dto.accessibility_dto import SimplifiedTextDTO, SimplifyTextDTO
from src.application.accessibility.use_cases.simplify_text_use_case import SimplifyTextUseCase


class AccessibilityApplicationService:
    """Application service that exposes accessibility operations to the API layer."""

    def __init__(self, simplify_text_use_case: SimplifyTextUseCase) -> None:
        self._simplify_text_use_case = simplify_text_use_case

    async def simplify_text(self, dto: SimplifyTextDTO) -> SimplifiedTextDTO:
        return await self._simplify_text_use_case.execute(dto)
