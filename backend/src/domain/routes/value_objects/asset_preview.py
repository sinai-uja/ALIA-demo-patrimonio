from dataclasses import dataclass


@dataclass(frozen=True)
class AssetPreview:
    """Lightweight preview data for a heritage asset used in route stops."""

    id: str
    image_url: str | None = None
    latitude: float | None = None
    longitude: float | None = None
