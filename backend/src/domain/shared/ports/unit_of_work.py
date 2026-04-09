"""Unit of Work port: explicit transaction boundary abstraction.

Domain/application code uses `async with uow:` to delimit a transactional
scope. Implementations commit on clean exit and roll back on exception.
The port deliberately exposes ONLY the async context manager protocol;
commit/rollback are implementation details, not part of the public API.
"""

from abc import ABC, abstractmethod


class UnitOfWork(ABC):
    """Abstract asynchronous Unit of Work.

    Implementations encapsulate the underlying session lifecycle and
    translate scope exit into commit/rollback semantics. Callers MUST
    use `async with` and MUST NOT attempt to commit or rollback manually.
    """

    @abstractmethod
    async def __aenter__(self) -> "UnitOfWork": ...

    @abstractmethod
    async def __aexit__(self, exc_type, exc, tb) -> None: ...
