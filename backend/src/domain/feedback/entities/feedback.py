from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Feedback:
    """Domain entity representing user feedback on a target."""

    id: UUID
    user_id: str
    target_type: str  # 'route' | 'search'
    target_id: str  # route UUID or search hash
    value: int  # +1 or -1
    metadata: dict | None
    created_at: datetime
    updated_at: datetime
