from src.domain.rag.entities.retrieved_chunk import RetrievedChunk


class RelevanceFilterService:
    """Filters retrieved chunks by cosine distance score threshold."""

    def __init__(self, score_threshold: float) -> None:
        self._score_threshold = score_threshold

    def filter(
        self,
        chunks: list[RetrievedChunk],
        override_threshold: float | None = None,
    ) -> list[RetrievedChunk]:
        """Return only chunks with cosine distance <= threshold (lower = more relevant).

        ``override_threshold`` lets callers (per-request) override the cutoff
        configured at construction time without rebuilding the service.
        """
        threshold = (
            override_threshold if override_threshold is not None
            else self._score_threshold
        )
        return [c for c in chunks if c.score <= threshold]

    def has_sufficient_evidence(
        self,
        chunks: list[RetrievedChunk],
        override_threshold: float | None = None,
    ) -> bool:
        return len(self.filter(chunks, override_threshold=override_threshold)) > 0
