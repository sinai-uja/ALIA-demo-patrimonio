from abc import ABC, abstractmethod


class FilterMetadataPort(ABC):
    """Port for retrieving distinct filter values from the document store."""

    @abstractmethod
    async def get_distinct_provinces(self) -> list[str]: ...

    @abstractmethod
    async def get_distinct_municipalities(
        self, provinces: list[str] | None = None,
    ) -> list[str]: ...

    @abstractmethod
    async def get_distinct_heritage_types(self) -> list[str]: ...
