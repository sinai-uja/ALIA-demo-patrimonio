from src.application.heritage.dto.heritage_dto import (
    HeritageAssetListDTO,
)
from src.application.heritage.use_cases._mapper import entity_to_dto
from src.domain.heritage.ports.heritage_repository import HeritageRepository


class ListAssetsUseCase:
    def __init__(self, repository: HeritageRepository) -> None:
        self._repo = repository

    async def execute(
        self,
        heritage_type: str | None = None,
        province: str | None = None,
        municipality: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> HeritageAssetListDTO:
        items = await self._repo.list_assets(
            heritage_type=heritage_type,
            province=province,
            municipality=municipality,
            limit=limit,
            offset=offset,
        )
        total = await self._repo.count_assets(
            heritage_type=heritage_type,
            province=province,
            municipality=municipality,
        )
        return HeritageAssetListDTO(
            items=[entity_to_dto(e) for e in items],
            total=total,
            limit=limit,
            offset=offset,
        )
