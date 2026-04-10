from abc import ABC, abstractmethod


class EmbeddingPort(ABC):
    """Port for generating text embeddings via an external encoder service."""

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
