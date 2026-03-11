import httpx

from src.config import settings
from src.domain.documents.ports.embedding_port import EmbeddingPort


class HttpEmbeddingAdapter(EmbeddingPort):
    """HTTP client adapter for the MrBERT embedding service."""

    def __init__(self) -> None:
        self._base_url = settings.embedding_service_url

    async def embed(self, texts: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self._base_url}/embed",
                json={"texts": texts},
            )
            response.raise_for_status()
            data = response.json()
            return data["embeddings"]
