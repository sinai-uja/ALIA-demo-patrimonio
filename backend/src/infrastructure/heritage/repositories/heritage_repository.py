from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.heritage.entities.heritage_asset import HeritageAsset
from src.domain.heritage.ports.heritage_repository import HeritageRepository
from src.domain.heritage.value_objects.raw_data import parse_raw_data
from src.infrastructure.heritage.models import HeritageAssetModel


class SqlAlchemyHeritageRepository(HeritageRepository):
    """Async SQLAlchemy implementation of the HeritageRepository port."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_asset(self, asset_id: str) -> HeritageAsset | None:
        stmt = select(HeritageAssetModel).where(
            HeritageAssetModel.id == asset_id,
        )
        result = await self._db.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    async def list_assets(
        self,
        heritage_type: str | None = None,
        province: str | None = None,
        municipality: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[HeritageAsset]:
        stmt = select(HeritageAssetModel)
        stmt = self._apply_filters(stmt, heritage_type, province, municipality)
        stmt = stmt.order_by(HeritageAssetModel.denomination).limit(limit)
        if offset:
            stmt = stmt.offset(offset)
        result = await self._db.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_assets(
        self,
        heritage_type: str | None = None,
        province: str | None = None,
        municipality: str | None = None,
    ) -> int:
        stmt = select(func.count(HeritageAssetModel.id))
        stmt = self._apply_filters(stmt, heritage_type, province, municipality)
        result = await self._db.execute(stmt)
        return result.scalar() or 0

    @staticmethod
    def _apply_filters(stmt, heritage_type, province, municipality):
        if heritage_type:
            stmt = stmt.where(
                HeritageAssetModel.heritage_type == heritage_type,
            )
        if province:
            stmt = stmt.where(HeritageAssetModel.province == province)
        if municipality:
            stmt = stmt.where(
                HeritageAssetModel.municipality == municipality,
            )
        return stmt

    @staticmethod
    def _to_entity(model: HeritageAssetModel) -> HeritageAsset:
        details = parse_raw_data(
            model.raw_data or {},
            model.heritage_type,
        )
        return HeritageAsset(
            id=model.id,
            heritage_type=model.heritage_type,
            denomination=model.denomination,
            province=model.province,
            municipality=model.municipality,
            latitude=model.latitude,
            longitude=model.longitude,
            image_url=model.image_url,
            image_ids=model.image_ids or [],
            protection=model.protection,
            details=details,
        )
