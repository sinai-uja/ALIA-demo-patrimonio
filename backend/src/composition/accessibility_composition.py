from src.application.accessibility.services.accessibility_application_service import (
    AccessibilityApplicationService,
)
from src.application.accessibility.use_cases.simplify_text_use_case import SimplifyTextUseCase
from src.composition.token_provider_composition import build_token_provider
from src.config import settings
from src.infrastructure.accessibility.adapters.llm_adapter import AccessibilityLLMAdapter


def build_accessibility_application_service() -> AccessibilityApplicationService:
    """Wire all accessibility adapters and return the application service."""
    llm_adapter = AccessibilityLLMAdapter(
        token_provider=build_token_provider(settings.llm_service_url),
    )
    use_case = SimplifyTextUseCase(llm_port=llm_adapter)
    return AccessibilityApplicationService(simplify_text_use_case=use_case)
