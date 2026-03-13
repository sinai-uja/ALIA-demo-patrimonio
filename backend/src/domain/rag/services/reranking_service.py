import logging
import re
from dataclasses import replace

from src.domain.rag.entities.retrieved_chunk import RetrievedChunk

logger = logging.getLogger("iaph.llm")


class RerankingService:
    """Lightweight heuristic re-ranker combining multiple lexical signals.

    Combines: base relevance score, title match boost, query term coverage,
    and chunk position signal. No GPU required.
    """

    def __init__(
        self,
        weight_base: float = 0.4,
        weight_title: float = 0.3,
        weight_coverage: float = 0.2,
        weight_position: float = 0.1,
    ) -> None:
        self._w_base = weight_base
        self._w_title = weight_title
        self._w_coverage = weight_coverage
        self._w_position = weight_position

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int,
    ) -> list[RetrievedChunk]:
        if not chunks:
            return []

        query_terms = self._tokenize(query)
        if not query_terms:
            return chunks[:top_k]

        scored = []
        for chunk in chunks:
            base_score = 1.0 - chunk.score  # Convert distance to relevance (0=worst, 1=best)
            title_score = self._title_match_score(query_terms, chunk.title)
            coverage_score = self._coverage_score(query_terms, chunk.content)
            position_score = self._position_score(chunk)

            final = (
                self._w_base * base_score
                + self._w_title * title_score
                + self._w_coverage * coverage_score
                + self._w_position * position_score
            )
            scored.append((chunk, final, base_score, title_score, coverage_score, position_score))

        scored.sort(key=lambda x: x[1], reverse=True)

        # Normalize back to distance-like score (0 = best)
        max_score = scored[0][1] if scored else 1.0

        results = []
        for i, (chunk, final, base, title, cov, pos) in enumerate(scored[:top_k]):
            normalized = 1.0 - (final / max_score) if max_score > 0 else 1.0
            results.append(replace(chunk, score=normalized))
            logger.info(
                "Reranked #%d: %.3f (base=%.2f title=%.2f cov=%.2f pos=%.2f)"
                " | %s (%s, %s)",
                i + 1, final, base, title, cov, pos,
                chunk.title[:50], chunk.heritage_type or "-", chunk.province or "-",
            )

        return results

    def _tokenize(self, text: str) -> set[str]:
        """Extract lowercase alphanumeric tokens, filtering stopwords."""
        words = re.findall(r"\w+", text.lower())
        stopwords = {
            "de", "del", "la", "el", "los", "las", "un", "una", "en", "y", "a",
            "que", "es", "por", "con", "para", "al", "se", "lo", "como", "sobre",
            "dame", "hablame", "dime", "informacion", "información",
        }
        return {w for w in words if w not in stopwords and len(w) > 1}

    def _title_match_score(self, query_terms: set[str], title: str) -> float:
        """Fraction of query terms found in the chunk title."""
        title_lower = title.lower()
        matches = sum(1 for t in query_terms if t in title_lower)
        return matches / len(query_terms) if query_terms else 0.0

    def _coverage_score(self, query_terms: set[str], content: str) -> float:
        """Fraction of query terms found anywhere in the chunk content."""
        content_lower = content.lower()
        matches = sum(1 for t in query_terms if t in content_lower)
        return matches / len(query_terms) if query_terms else 0.0

    def _position_score(self, chunk: RetrievedChunk) -> float:
        """Prefer earlier chunks in a document (chunk_index closer to 0)."""
        # We don't have chunk_index in RetrievedChunk, so return neutral
        return 0.5
