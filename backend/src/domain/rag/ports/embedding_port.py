from abc import ABC, abstractmethod


class EmbeddingPort(ABC):
    """Port for text embedding generation."""

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        ...
