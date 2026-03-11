from abc import ABC, abstractmethod


class RAGPort(ABC):
    """Port for invoking the RAG pipeline from the chat context."""

    @abstractmethod
    async def query(
        self,
        question: str,
        top_k: int,
        heritage_type_filter: str | None,
        province_filter: str | None,
    ) -> tuple[str, list[dict]]:
        """Execute a RAG query.

        Returns:
            A tuple of (answer_text, sources_list) where sources is a list of
            dicts with keys: title, url, score, heritage_type, province.
        """
        ...
