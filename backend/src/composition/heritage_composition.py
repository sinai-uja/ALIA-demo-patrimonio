from sqlalchemy.ext.asyncio import AsyncSession

from src.application.heritage.services.heritage_application_service import (
    HeritageApplicationService,
)
from src.application.heritage.use_cases.get_asset import GetAssetUseCase
from src.application.heritage.use_cases.list_assets import ListAssetsUseCase
from src.infrastructure.heritage.repositories.heritage_repository import (
    SqlAlchemyHeritageRepository,
)


def build_heritage_application_service(
    db: AsyncSession,
) -> HeritageApplicationService:
    """Wire all heritage adapters and return the application service."""
    repository = SqlAlchemyHeritageRepository(db)
    return HeritageApplicationService(
        get_asset_use_case=GetAssetUseCase(repository),
        list_assets_use_case=ListAssetsUseCase(repository),
    )
