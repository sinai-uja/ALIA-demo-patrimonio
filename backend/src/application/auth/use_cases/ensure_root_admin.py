"""Idempotent bootstrap of the root admin user and its profile type."""

from __future__ import annotations

import logging

from src.domain.auth.ports.auth_port import AuthPort
from src.domain.shared.ports.unit_of_work import UnitOfWork

logger = logging.getLogger("iaph.auth.ensure_root_admin")

_ADMIN_PROFILE_TYPE_NAME = "admin"


class EnsureRootAdminUseCase:
    """Ensure the root admin profile type and user exist.

    This use case is idempotent: it can be safely invoked on every
    application startup. It relies exclusively on the ``AuthPort``
    abstraction, so it is independent from the concrete persistence or
    password-hashing implementation. Writes are delimited by the
    injected Unit of Work.
    """

    def __init__(self, auth_port: AuthPort, unit_of_work: UnitOfWork) -> None:
        self._auth_port = auth_port
        self._uow = unit_of_work

    async def execute(self, username: str, password: str) -> None:
        existing_user = await self._auth_port.get_user_by_username(username)
        if existing_user is not None:
            if (
                existing_user.profile_type is None
                or existing_user.profile_type.name != _ADMIN_PROFILE_TYPE_NAME
            ):
                async with self._uow:
                    await self._auth_port.update_profile_type(
                        existing_user.id, _ADMIN_PROFILE_TYPE_NAME
                    )
                logger.info(
                    "Root admin '%s' reattached to '%s' profile type",
                    username,
                    _ADMIN_PROFILE_TYPE_NAME,
                )
            else:
                logger.info("Root admin '%s' already exists", username)
            return

        async with self._uow:
            # Ensure the admin profile type exists before creating the user.
            profile_types = {
                pt.name for pt in await self._auth_port.list_profile_types()
            }
            if _ADMIN_PROFILE_TYPE_NAME not in profile_types:
                await self._auth_port.create_profile_type(
                    _ADMIN_PROFILE_TYPE_NAME
                )
                logger.info(
                    "Created '%s' profile type", _ADMIN_PROFILE_TYPE_NAME
                )

            await self._auth_port.create_user(
                username=username,
                password=password,
                profile_type_name=_ADMIN_PROFILE_TYPE_NAME,
            )
        logger.info("Root admin '%s' created", username)
