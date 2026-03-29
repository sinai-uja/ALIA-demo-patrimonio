import uuid

import bcrypt
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from src.domain.auth.entities.user import User, UserProfileType
from src.domain.auth.ports.auth_port import AuthPort, ProfileTypeInUseError
from src.infrastructure.auth.models import UserModel, UserProfileTypeModel


class DbAuthAdapter(AuthPort):
    """Database-backed authentication adapter using synchronous SQLAlchemy."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def authenticate(self, username: str, password: str) -> User | None:
        with self._session_factory() as session:
            row = session.execute(
                select(UserModel).where(UserModel.username == username)
            ).scalar_one_or_none()
            if row is None:
                return None
            if not bcrypt.checkpw(password.encode(), row.password_hash.encode()):
                return None
            return self._to_domain(row)

    def get_user_by_username(self, username: str) -> User | None:
        with self._session_factory() as session:
            row = session.execute(
                select(UserModel).where(UserModel.username == username)
            ).scalar_one_or_none()
            if row is None:
                return None
            return self._to_domain(row)

    def update_profile_type(self, user_id: uuid.UUID, profile_type_name: str) -> User:
        with self._session_factory() as session:
            pt = session.execute(
                select(UserProfileTypeModel)
                .where(UserProfileTypeModel.name == profile_type_name)
            ).scalar_one_or_none()
            if pt is None:
                raise ValueError(f"Profile type '{profile_type_name}' not found")

            user = session.execute(
                select(UserModel).where(UserModel.id == user_id)
            ).scalar_one_or_none()
            if user is None:
                raise ValueError("User not found")

            user.profile_type_id = pt.id
            session.commit()
            session.refresh(user)
            return self._to_domain(user)

    def list_profile_types(self) -> list[UserProfileType]:
        with self._session_factory() as session:
            rows = session.execute(
                select(UserProfileTypeModel).order_by(UserProfileTypeModel.name)
            ).scalars().all()
            return [
                UserProfileType(id=r.id, name=r.name)
                for r in rows
            ]

    def list_users(self) -> list[User]:
        with self._session_factory() as session:
            rows = session.execute(
                select(UserModel).order_by(UserModel.username)
            ).scalars().all()
            return [self._to_domain(row) for row in rows]

    def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        with self._session_factory() as session:
            row = session.execute(
                select(UserModel).where(UserModel.id == user_id)
            ).scalar_one_or_none()
            if row is None:
                return None
            return self._to_domain(row)

    def create_user(
        self, username: str, password: str, profile_type_name: str | None,
    ) -> User:
        with self._session_factory() as session:
            existing = session.execute(
                select(UserModel).where(UserModel.username == username)
            ).scalar_one_or_none()
            if existing is not None:
                raise ValueError(f"Username '{username}' already exists")

            profile_type_id = None
            if profile_type_name is not None:
                pt = session.execute(
                    select(UserProfileTypeModel)
                    .where(UserProfileTypeModel.name == profile_type_name)
                ).scalar_one_or_none()
                if pt is None:
                    raise ValueError(f"Profile type '{profile_type_name}' not found")
                profile_type_id = pt.id

            pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            user = UserModel(
                id=uuid.uuid4(),
                username=username,
                password_hash=pw_hash,
                profile_type_id=profile_type_id,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            return self._to_domain(user)

    def update_user(
        self,
        user_id: uuid.UUID,
        *,
        password: str | None,
        profile_type_name: str | None,
    ) -> User:
        with self._session_factory() as session:
            user = session.execute(
                select(UserModel).where(UserModel.id == user_id)
            ).scalar_one_or_none()
            if user is None:
                raise ValueError("User not found")

            if password is not None:
                user.password_hash = bcrypt.hashpw(
                    password.encode(), bcrypt.gensalt()
                ).decode()

            if profile_type_name is not None:
                pt = session.execute(
                    select(UserProfileTypeModel)
                    .where(UserProfileTypeModel.name == profile_type_name)
                ).scalar_one_or_none()
                if pt is None:
                    raise ValueError(f"Profile type '{profile_type_name}' not found")
                user.profile_type_id = pt.id

            session.commit()
            session.refresh(user)
            return self._to_domain(user)

    def delete_user(self, user_id: uuid.UUID) -> None:
        with self._session_factory() as session:
            user = session.execute(
                select(UserModel).where(UserModel.id == user_id)
            ).scalar_one_or_none()
            if user is None:
                raise ValueError("User not found")
            session.delete(user)
            session.commit()

    def list_profile_types_with_counts(self) -> list[tuple[UserProfileType, int]]:
        with self._session_factory() as session:
            rows = session.execute(
                select(
                    UserProfileTypeModel,
                    func.count(UserModel.id).label("user_count"),
                )
                .outerjoin(UserModel, UserModel.profile_type_id == UserProfileTypeModel.id)
                .group_by(UserProfileTypeModel.id)
                .order_by(UserProfileTypeModel.name)
            ).all()
            return [
                (
                    UserProfileType(id=r.UserProfileTypeModel.id, name=r.UserProfileTypeModel.name),
                    r.user_count,
                )
                for r in rows
            ]

    def create_profile_type(self, name: str) -> UserProfileType:
        with self._session_factory() as session:
            existing = session.execute(
                select(UserProfileTypeModel).where(UserProfileTypeModel.name == name)
            ).scalar_one_or_none()
            if existing is not None:
                raise ValueError(f"El tipo de perfil '{name}' ya existe")
            pt = UserProfileTypeModel(id=uuid.uuid4(), name=name)
            session.add(pt)
            session.commit()
            session.refresh(pt)
            return UserProfileType(id=pt.id, name=pt.name)

    def rename_profile_type(self, profile_type_id: uuid.UUID, new_name: str) -> UserProfileType:
        with self._session_factory() as session:
            pt = session.execute(
                select(UserProfileTypeModel).where(UserProfileTypeModel.id == profile_type_id)
            ).scalar_one_or_none()
            if pt is None:
                raise ValueError("Tipo de perfil no encontrado")
            conflict = session.execute(
                select(UserProfileTypeModel).where(
                    UserProfileTypeModel.name == new_name,
                    UserProfileTypeModel.id != profile_type_id,
                )
            ).scalar_one_or_none()
            if conflict is not None:
                raise ValueError(f"El tipo de perfil '{new_name}' ya existe")
            pt.name = new_name
            session.commit()
            session.refresh(pt)
            return UserProfileType(id=pt.id, name=pt.name)

    def delete_profile_type(self, profile_type_id: uuid.UUID) -> None:
        with self._session_factory() as session:
            pt = session.execute(
                select(UserProfileTypeModel).where(UserProfileTypeModel.id == profile_type_id)
            ).scalar_one_or_none()
            if pt is None:
                raise ValueError("Tipo de perfil no encontrado")
            session.delete(pt)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                raise ProfileTypeInUseError(
                    f"El tipo de perfil '{pt.name}' está asignado a uno o más usuarios"
                    " y no puede eliminarse"
                )

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
