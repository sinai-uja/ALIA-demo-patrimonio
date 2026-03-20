from abc import ABC, abstractmethod

from src.domain.routes.value_objects.asset_preview import AssetPreview


class HeritageAssetLookupPort(ABC):
    """Port for looking up heritage asset preview data (images, coordinates)."""

    @abstractmethod
    async def get_asset_previews(
        self, asset_ids: list[str],
    ) -> dict[str, AssetPreview]:
        """Return preview data keyed by asset ID for the given IDs."""
