from src.application.accessibility.services.accessibility_application_service import (
    AccessibilityApplicationService,
)
from src.application.accessibility.use_cases.simplify_text_use_case import SimplifyTextUseCase
from src.infrastructure.accessibility.adapters.llm_adapter import AccessibilityLLMAdapter


def build_accessibility_application_service() -> AccessibilityApplicationService:
    """Wire all accessibility adapters and return the application service."""
    llm_adapter = AccessibilityLLMAdapter()
    use_case = SimplifyTextUseCase(llm_port=llm_adapter)
    return AccessibilityApplicationService(simplify_text_use_case=use_case)
