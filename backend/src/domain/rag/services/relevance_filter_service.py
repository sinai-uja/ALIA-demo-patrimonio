from src.domain.rag.entities.retrieved_chunk import RetrievedChunk


class RelevanceFilterService:
    """Filters retrieved chunks by cosine distance score threshold."""

    def __init__(self, score_threshold: float) -> None:
        self._score_threshold = score_threshold

    def filter(self, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        """Return only chunks with cosine distance <= threshold (lower = more relevant)."""
        return [c for c in chunks if c.score <= self._score_threshold]

    def has_sufficient_evidence(self, chunks: list[RetrievedChunk]) -> bool:
        return len(self.filter(chunks)) > 0
