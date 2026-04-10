from dataclasses import asdict

from fastapi import APIRouter, Depends, Query

from src.api.v1.endpoints.auth.deps import get_current_user
from src.api.v1.endpoints.heritage.deps import get_heritage_service
from src.api.v1.endpoints.heritage.schemas import (
    HeritageAssetSchema,
    HeritageAssetSummaryListSchema,
    HeritageAssetSummarySchema,
)
from src.application.heritage.services.heritage_application_service import (
    HeritageApplicationService,
)
from src.application.shared.exceptions import ResourceNotFoundError
from src.domain.auth.entities.user import User

router = APIRouter()


@router.get("", response_model=HeritageAssetSummaryListSchema)
async def list_assets(
    heritage_type: str | None = Query(
        None, description="Filter: inmueble, mueble, inmaterial, paisaje",
    ),
    province: str | None = Query(None, description="Filter by province"),
    municipality: str | None = Query(
        None, description="Filter by municipality",
    ),
    limit: int = Query(50, ge=1, le=200, description="Page size"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    user: User = Depends(get_current_user),
    service: HeritageApplicationService = Depends(get_heritage_service),
) -> HeritageAssetSummaryListSchema:
    """List heritage assets with optional filters and pagination."""
    result = await service.list_assets(
        heritage_type=heritage_type,
        province=province,
        municipality=municipality,
        limit=limit,
        offset=offset,
    )
    return HeritageAssetSummaryListSchema(
        items=[
            HeritageAssetSummarySchema(
                id=a.id,
                heritage_type=a.heritage_type,
                denomination=a.denomination,
                province=a.province,
                municipality=a.municipality,
                latitude=a.latitude,
                longitude=a.longitude,
                image_url=a.image_url,
                protection=a.protection,
            )
            for a in result.items
        ],
        total=result.total,
        limit=result.limit,
        offset=result.offset,
    )


@router.get("/{asset_id}", response_model=HeritageAssetSchema)
async def get_asset(
    asset_id: str,
    user: User = Depends(get_current_user),
    service: HeritageApplicationService = Depends(get_heritage_service),
) -> HeritageAssetSchema:
    """Get a heritage asset by ID with full typed details."""
    result = await service.get_asset(asset_id)
    if result is None:
        raise ResourceNotFoundError("Asset not found")

    details_dict = asdict(result.details) if result.details else None

    return HeritageAssetSchema(
        id=result.id,
        heritage_type=result.heritage_type,
        denomination=result.denomination,
        province=result.province,
        municipality=result.municipality,
        latitude=result.latitude,
        longitude=result.longitude,
        image_url=result.image_url,
        image_ids=result.image_ids,
        protection=result.protection,
        details=details_dict,
    )
