"""Admin-facing user DTO.

Used by the admin use cases to expose user data without leaking the
domain ``User`` entity (which carries the password hash) to the API
layer.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UserDTO:
    """Immutable projection of a ``User`` entity for admin responses."""

    id: str
    username: str
    profile_type: str | None
    created_at: str | None
