from dataclasses import dataclass


@dataclass(frozen=True)
class RouteStop:
    """A single stop in a virtual heritage route."""

    order: int
    title: str
    heritage_type: str
    province: str
    municipality: str | None
    url: str
    description: str
    heritage_asset_id: str | None = None
    document_id: str | None = None
    narrative_segment: str = ""
    image_url: str | None = None
    latitude: float | None = None
    longitude: float | None = None
