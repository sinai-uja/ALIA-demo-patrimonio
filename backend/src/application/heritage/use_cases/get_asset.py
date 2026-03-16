from src.application.heritage.dto.heritage_dto import HeritageAssetDTO
from src.application.heritage.use_cases._mapper import entity_to_dto
from src.domain.heritage.ports.heritage_repository import HeritageRepository


class GetAssetUseCase:
    def __init__(self, repository: HeritageRepository) -> None:
        self._repo = repository

    async def execute(self, asset_id: str) -> HeritageAssetDTO | None:
        entity = await self._repo.get_asset(asset_id)
        if entity is None:
            return None
        return entity_to_dto(entity)
