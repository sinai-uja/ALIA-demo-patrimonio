from abc import ABC, abstractmethod

from src.domain.heritage.entities.heritage_asset import HeritageAsset


class HeritageRepository(ABC):
    """Port for retrieving heritage assets."""

    @abstractmethod
    async def get_asset(self, asset_id: str) -> HeritageAsset | None:
        ...

    @abstractmethod
    async def list_assets(
        self,
        heritage_type: str | None = None,
        province: str | None = None,
        municipality: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[HeritageAsset]:
        ...

    @abstractmethod
    async def count_assets(
        self,
        heritage_type: str | None = None,
        province: str | None = None,
        municipality: str | None = None,
    ) -> int:
        ...
