from abc import ABC, abstractmethod


class RAGPort(ABC):
    """Port for RAG retrieval queries, independent of the RAG bounded context."""

    @abstractmethod
    async def query(
        self,
        question: str,
        top_k: int,
        heritage_type_filter: str | None = None,
        province_filter: str | None = None,
    ) -> tuple[str, list[dict]]:
        """Execute a RAG query and return (answer, list of source chunk dicts).

        Each source dict contains: title, url, heritage_type, province,
        municipality, content, score.
        """
        ...
