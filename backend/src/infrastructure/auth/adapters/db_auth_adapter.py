import uuid

import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from src.domain.auth.entities.user import User, UserProfileType
from src.domain.auth.ports.auth_port import AuthPort
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
        )
