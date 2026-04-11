from abc import ABC, abstractmethod


class RAGPort(ABC):
    """Port for RAG retrieval queries, independent of the RAG bounded context."""

    @abstractmethod
    async def query(
        self,
        question: str,
        top_k: int,
        heritage_type_filter: list[str] | None = None,
        province_filter: list[str] | None = None,
        municipality_filter: list[str] | None = None,
    ) -> tuple[str, list[dict], list[dict]]:
        """Execute a RAG query and return (answer, sources, pipeline_steps).

        Each source dict contains: title, url, heritage_type, province,
        municipality, content, score.
        pipeline_steps contains granular tracing info (embedding, vector_search, etc.).
        """
        ...
