"""SQLAlchemy async Unit of Work adapter."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.shared.ports.unit_of_work import UnitOfWork


class SqlAlchemyUnitOfWork(UnitOfWork):
    """Concrete UoW backed by an AsyncSession.

    Commits on clean exit of the `async with` block, rolls back if an
    exception propagates. The session lifecycle itself is managed by the
    caller (typically the FastAPI dependency).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def __aenter__(self) -> "SqlAlchemyUnitOfWork":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if exc_type is not None:
            await self._session.rollback()
            return
        await self._session.commit()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
