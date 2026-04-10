import logging
import uuid

import bcrypt
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.auth.exceptions import (
    ProfileTypeAlreadyExistsError,
    ProfileTypeInUseError,
    ProfileTypeNotFoundError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from src.application.shared.exceptions import ExternalServiceUnavailableError
from src.domain.auth.entities.user import User, UserProfileType
from src.domain.auth.ports.auth_port import AuthPort
from src.infrastructure.auth.models import UserModel, UserProfileTypeModel

logger = logging.getLogger("iaph.auth.adapter")


class DbAuthAdapter(AuthPort):
    """Database-backed authentication adapter using async SQLAlchemy.

    The adapter never commits: transaction boundaries are owned by the
    application layer through the injected Unit of Work.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def authenticate(self, username: str, password: str) -> User | None:
        try:
            result = await self._session.execute(
                select(UserModel).where(UserModel.username == username)
            )
        except Exception as exc:
            logger.error(
                "Database error during authentication for user=%r",
                username, exc_info=True,
            )
            raise ExternalServiceUnavailableError(
                "Authentication service temporarily unavailable",
            ) from exc
        row = result.scalar_one_or_none()
        if row is None:
            logger.debug("Authentication failed: user %r not found", username)
            return None
        if not bcrypt.checkpw(password.encode(), row.password_hash.encode()):
            logger.debug("Authentication failed: wrong password for user %r", username)
            return None
        logger.debug("Authentication succeeded for user %r", username)
        return self._to_domain(row)

    async def get_user_by_username(self, username: str) -> User | None:
        try:
            result = await self._session.execute(
                select(UserModel).where(UserModel.username == username)
            )
        except Exception as exc:
            logger.error(
                "Database error in get_user_by_username username=%r",
                username, exc_info=True,
            )
            raise ExternalServiceUnavailableError("Auth service temporarily unavailable") from exc
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._to_domain(row)

    async def update_profile_type(
        self, user_id: uuid.UUID, profile_type_name: str
    ) -> User:
        try:
            pt_result = await self._session.execute(
                select(UserProfileTypeModel)
                .where(UserProfileTypeModel.name == profile_type_name)
            )
        except Exception as exc:
            logger.error(
                "Database error in update_profile_type looking up profile_type=%r",
                profile_type_name, exc_info=True,
            )
            raise ExternalServiceUnavailableError("Auth service temporarily unavailable") from exc
        pt = pt_result.scalar_one_or_none()
        if pt is None:
            raise ProfileTypeNotFoundError(
                f"Profile type '{profile_type_name}' not found"
            )

        try:
            user_result = await self._session.execute(
                select(UserModel).where(UserModel.id == user_id)
            )
        except Exception as exc:
            logger.error(
                "Database error in update_profile_type looking up user_id=%s",
                user_id, exc_info=True,
            )
            raise ExternalServiceUnavailableError("Auth service temporarily unavailable") from exc
        user = user_result.scalar_one_or_none()
        if user is None:
            raise UserNotFoundError("User not found")

        user.profile_type_id = pt.id
        try:
            await self._session.flush()
            await self._session.refresh(user)
        except Exception as exc:
            logger.error(
                "Database error in update_profile_type flush user_id=%s",
                user_id, exc_info=True,
            )
            raise ExternalServiceUnavailableError("Auth service temporarily unavailable") from exc
        return self._to_domain(user)

    async def list_profile_types(self) -> list[UserProfileType]:
        try:
            result = await self._session.execute(
                select(UserProfileTypeModel).order_by(UserProfileTypeModel.name)
            )
        except Exception as exc:
            logger.error("Database error in list_profile_types", exc_info=True)
            raise ExternalServiceUnavailableError("Auth service temporarily unavailable") from exc
        rows = result.scalars().all()
        return [UserProfileType(id=r.id, name=r.name) for r in rows]

    async def list_users(self) -> list[User]:
        try:
            result = await self._session.execute(
                select(UserModel).order_by(UserModel.username)
            )
        except Exception as exc:
            logger.error("Database error in list_users", exc_info=True)
            raise ExternalServiceUnavailableError("Auth service temporarily unavailable") from exc
        rows = result.scalars().all()
        return [self._to_domain(row) for row in rows]

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        try:
            result = await self._session.execute(
                select(UserModel).where(UserModel.id == user_id)
            )
        except Exception as exc:
            logger.error("Database error in get_user_by_id user_id=%s", user_id, exc_info=True)
            raise ExternalServiceUnavailableError("Auth service temporarily unavailable") from exc
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._to_domain(row)

    async def create_user(
        self, username: str, password: str, profile_type_name: str | None,
    ) -> User:
        try:
            existing_result = await self._session.execute(
                select(UserModel).where(UserModel.username == username)
            )
        except Exception as exc:
            logger.error(
                "Database error in create_user checking existing username=%r",
                username, exc_info=True,
            )
            raise ExternalServiceUnavailableError("Auth service temporarily unavailable") from exc
        if existing_result.scalar_one_or_none() is not None:
            raise UserAlreadyExistsError(
                f"Username '{username}' already exists"
            )

        profile_type_id = None
        if profile_type_name is not None:
            try:
                pt_result = await self._session.execute(
                    select(UserProfileTypeModel)
                    .where(UserProfileTypeModel.name == profile_type_name)
                )
            except Exception as exc:
                logger.error(
                    "Database error in create_user looking up profile_type=%r",
                    profile_type_name, exc_info=True,
                )
                raise ExternalServiceUnavailableError(
                    "Auth service temporarily unavailable",
                ) from exc
            pt = pt_result.scalar_one_or_none()
            if pt is None:
                raise ProfileTypeNotFoundError(
                    f"Profile type '{profile_type_name}' not found"
                )
            profile_type_id = pt.id

        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        user = UserModel(
            id=uuid.uuid4(),
            username=username,
            password_hash=pw_hash,
            profile_type_id=profile_type_id,
        )
        self._session.add(user)
        try:
            await self._session.flush()
            await self._session.refresh(user)
        except Exception as exc:
            logger.error(
                "Database error in create_user flush username=%r",
                username, exc_info=True,
            )
            raise ExternalServiceUnavailableError("Auth service temporarily unavailable") from exc
        return self._to_domain(user)

    async def update_user(
        self,
        user_id: uuid.UUID,
        *,
        password: str | None,
        profile_type_name: str | None,
    ) -> User:
        try:
            user_result = await self._session.execute(
                select(UserModel).where(UserModel.id == user_id)
            )
        except Exception as exc:
            logger.error(
                "Database error in update_user looking up user_id=%s",
                user_id, exc_info=True,
            )
            raise ExternalServiceUnavailableError("Auth service temporarily unavailable") from exc
        user = user_result.scalar_one_or_none()
        if user is None:
            raise UserNotFoundError("User not found")

        if password is not None:
            user.password_hash = bcrypt.hashpw(
                password.encode(), bcrypt.gensalt()
            ).decode()

        if profile_type_name is not None:
            try:
                pt_result = await self._session.execute(
                    select(UserProfileTypeModel)
                    .where(UserProfileTypeModel.name == profile_type_name)
                )
            except Exception as exc:
                logger.error(
                    "Database error in update_user looking up profile_type=%r",
                    profile_type_name, exc_info=True,
                )
                raise ExternalServiceUnavailableError(
                    "Auth service temporarily unavailable",
                ) from exc
            pt = pt_result.scalar_one_or_none()
            if pt is None:
                raise ProfileTypeNotFoundError(
                    f"Profile type '{profile_type_name}' not found"
                )
            user.profile_type_id = pt.id

        try:
            await self._session.flush()
            await self._session.refresh(user)
        except Exception as exc:
            logger.error(
                "Database error in update_user flush user_id=%s",
                user_id, exc_info=True,
            )
            raise ExternalServiceUnavailableError("Auth service temporarily unavailable") from exc
        return self._to_domain(user)

    async def delete_user(self, user_id: uuid.UUID) -> None:
        try:
            user_result = await self._session.execute(
                select(UserModel).where(UserModel.id == user_id)
            )
        except Exception as exc:
            logger.error(
                "Database error in delete_user looking up user_id=%s",
                user_id, exc_info=True,
            )
            raise ExternalServiceUnavailableError("Auth service temporarily unavailable") from exc
        user = user_result.scalar_one_or_none()
        if user is None:
            raise UserNotFoundError("User not found")
        await self._session.delete(user)
        try:
            await self._session.flush()
        except Exception as exc:
            logger.error(
                "Database error in delete_user flush user_id=%s",
                user_id, exc_info=True,
            )
            raise ExternalServiceUnavailableError("Auth service temporarily unavailable") from exc

    async def list_profile_types_with_counts(
        self,
    ) -> list[tuple[UserProfileType, int]]:
        try:
            result = await self._session.execute(
                select(
                    UserProfileTypeModel,
                    func.count(UserModel.id).label("user_count"),
                )
                .outerjoin(
                    UserModel, UserModel.profile_type_id == UserProfileTypeModel.id
                )
                .group_by(UserProfileTypeModel.id)
                .order_by(UserProfileTypeModel.name)
            )
        except Exception as exc:
            logger.error("Database error in list_profile_types_with_counts", exc_info=True)
            raise ExternalServiceUnavailableError("Auth service temporarily unavailable") from exc
        rows = result.all()
        return [
            (
                UserProfileType(
                    id=r.UserProfileTypeModel.id,
                    name=r.UserProfileTypeModel.name,
                ),
                r.user_count,
            )
            for r in rows
        ]

    async def create_profile_type(self, name: str) -> UserProfileType:
        try:
            existing_result = await self._session.execute(
                select(UserProfileTypeModel).where(UserProfileTypeModel.name == name)
            )
        except Exception as exc:
            logger.error(
                "Database error in create_profile_type checking existing name=%r",
                name, exc_info=True,
            )
            raise ExternalServiceUnavailableError("Auth service temporarily unavailable") from exc
        if existing_result.scalar_one_or_none() is not None:
            raise ProfileTypeAlreadyExistsError(
                f"El tipo de perfil '{name}' ya existe"
            )
        pt = UserProfileTypeModel(id=uuid.uuid4(), name=name)
        self._session.add(pt)
        try:
            await self._session.flush()
            await self._session.refresh(pt)
        except Exception as exc:
            logger.error("Database error in create_profile_type flush name=%r", name, exc_info=True)
            raise ExternalServiceUnavailableError("Auth service temporarily unavailable") from exc
        return UserProfileType(id=pt.id, name=pt.name)

    async def rename_profile_type(
        self, profile_type_id: uuid.UUID, new_name: str
    ) -> UserProfileType:
        try:
            pt_result = await self._session.execute(
                select(UserProfileTypeModel).where(
                    UserProfileTypeModel.id == profile_type_id
                )
            )
        except Exception as exc:
            logger.error(
                "Database error in rename_profile_type looking up id=%s",
                profile_type_id, exc_info=True,
            )
            raise ExternalServiceUnavailableError("Auth service temporarily unavailable") from exc
        pt = pt_result.scalar_one_or_none()
        if pt is None:
            raise ProfileTypeNotFoundError("Tipo de perfil no encontrado")
        try:
            conflict_result = await self._session.execute(
                select(UserProfileTypeModel).where(
                    UserProfileTypeModel.name == new_name,
                    UserProfileTypeModel.id != profile_type_id,
                )
            )
        except Exception as exc:
            logger.error(
                "Database error in rename_profile_type checking conflict name=%r",
                new_name, exc_info=True,
            )
            raise ExternalServiceUnavailableError("Auth service temporarily unavailable") from exc
        if conflict_result.scalar_one_or_none() is not None:
            raise ProfileTypeAlreadyExistsError(
                f"El tipo de perfil '{new_name}' ya existe"
            )
        pt.name = new_name
        try:
            await self._session.flush()
            await self._session.refresh(pt)
        except Exception as exc:
            logger.error(
                "Database error in rename_profile_type flush id=%s",
                profile_type_id, exc_info=True,
            )
            raise ExternalServiceUnavailableError("Auth service temporarily unavailable") from exc
        return UserProfileType(id=pt.id, name=pt.name)

    async def delete_profile_type(self, profile_type_id: uuid.UUID) -> None:
        try:
            pt_result = await self._session.execute(
                select(UserProfileTypeModel).where(
                    UserProfileTypeModel.id == profile_type_id
                )
            )
        except Exception as exc:
            logger.error(
                "Database error in delete_profile_type looking up id=%s",
                profile_type_id, exc_info=True,
            )
            raise ExternalServiceUnavailableError("Auth service temporarily unavailable") from exc
        pt = pt_result.scalar_one_or_none()
        if pt is None:
            raise ProfileTypeNotFoundError("Tipo de perfil no encontrado")
        pt_name = pt.name
        await self._session.delete(pt)
        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            raise ProfileTypeInUseError(
                f"El tipo de perfil '{pt_name}' está asignado a uno o más usuarios"
                " y no puede eliminarse"
            )
        except Exception as exc:
            logger.error(
                "Database error in delete_profile_type flush id=%s",
                profile_type_id, exc_info=True,
            )
            raise ExternalServiceUnavailableError("Auth service temporarily unavailable") from exc

    @staticmethod
    def _to_domain(row: UserModel) -> User:
        pt = None
        if row.profile_type is not None:
            pt = UserProfileType(id=row.profile_type.id, name=row.profile_type.name)
        return User(
            id=row.id,
            username=row.username,
            password_hash=row.password_hash,
            profile_type=pt,
            created_at=row.created_at,
        )
