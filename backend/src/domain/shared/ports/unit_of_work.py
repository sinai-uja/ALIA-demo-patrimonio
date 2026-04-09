"""Unit of Work port: explicit transaction boundary abstraction.

Domain/application code uses `async with uow:` to delimit a transactional
scope. Commits on successful exit, rolls back on exception.
"""

from abc import ABC, abstractmethod


class UnitOfWork(ABC):
    """Abstract asynchronous Unit of Work.

    Implementations encapsulate the underlying session lifecycle and
    translate scope exit into commit/rollback semantics.
    """

    @abstractmethod
    async def __aenter__(self) -> "UnitOfWork": ...

    @abstractmethod
    async def __aexit__(self, exc_type, exc, tb) -> None: ...

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...
