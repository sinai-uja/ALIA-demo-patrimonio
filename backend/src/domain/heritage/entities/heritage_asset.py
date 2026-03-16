from dataclasses import dataclass, field

from src.domain.heritage.value_objects.raw_data import (
    InmaterialRawData,
    InmuebleRawData,
    MuebleRawData,
    PaisajeRawData,
)


@dataclass(frozen=True)
class HeritageAsset:
    """Domain entity for an enriched heritage asset from the IAPH API."""

    id: str
    heritage_type: str
    denomination: str | None = None
    province: str | None = None
    municipality: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    image_url: str | None = None
    image_ids: list[str] = field(default_factory=list)
    protection: str | None = None
    details: (
        InmuebleRawData | MuebleRawData | InmaterialRawData | PaisajeRawData
        | None
    ) = None
