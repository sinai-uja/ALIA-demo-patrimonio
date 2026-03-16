from src.application.heritage.dto.heritage_dto import (
    HeritageAssetDTO,
    HeritageAssetListDTO,
)
from src.application.heritage.use_cases.get_asset import GetAssetUseCase
from src.application.heritage.use_cases.list_assets import ListAssetsUseCase


class HeritageApplicationService:
    """Application service that exposes heritage asset operations."""

    def __init__(
        self,
        get_asset_use_case: GetAssetUseCase,
        list_assets_use_case: ListAssetsUseCase,
    ) -> None:
        self._get_asset = get_asset_use_case
        self._list_assets = list_assets_use_case

    async def get_asset(self, asset_id: str) -> HeritageAssetDTO | None:
        return await self._get_asset.execute(asset_id)

    async def list_assets(
        self,
        heritage_type: str | None = None,
        province: str | None = None,
        municipality: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> HeritageAssetListDTO:
        return await self._list_assets.execute(
            heritage_type=heritage_type,
            province=province,
            municipality=municipality,
            limit=limit,
            offset=offset,
        )
