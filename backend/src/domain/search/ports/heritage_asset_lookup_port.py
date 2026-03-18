from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class HeritageAssetSummaryData:
    """Common heritage asset fields for search result enrichment."""

    id: str
    denomination: str | None = None
    province: str | None = None
    municipality: str | None = None
    description: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    image_url: str | None = None
    protection: str | None = None


class HeritageAssetLookupPort(ABC):
    """Port for looking up heritage asset summaries by their IDs."""

    @abstractmethod
    async def get_summaries_by_ids(
        self, ids: list[str],
    ) -> dict[str, HeritageAssetSummaryData]:
        """Return a dict of asset ID -> summary for the given IDs."""
