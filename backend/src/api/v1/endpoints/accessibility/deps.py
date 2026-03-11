from src.application.accessibility.services.accessibility_application_service import (
    AccessibilityApplicationService,
)
from src.composition.accessibility_composition import build_accessibility_application_service


async def get_accessibility_service() -> AccessibilityApplicationService:
    return build_accessibility_application_service()
