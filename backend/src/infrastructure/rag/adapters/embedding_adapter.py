import httpx

from src.config import settings
from src.domain.rag.ports.embedding_port import EmbeddingPort


class HttpEmbeddingAdapter(EmbeddingPort):
    """Calls the internal embedding service via HTTP to generate embeddings."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = base_url or settings.embedding_service_url

    async def embed(self, texts: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self._base_url}/embed",
                json={"texts": texts},
            )
            response.raise_for_status()
            data = response.json()
            return data["embeddings"]
