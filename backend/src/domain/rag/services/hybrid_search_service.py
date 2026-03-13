from dataclasses import replace

from src.domain.rag.entities.retrieved_chunk import RetrievedChunk


class HybridSearchService:
    """Fuses vector and full-text search results using Reciprocal Rank Fusion (RRF).

    Text search results are weighted higher (1.5x) because exact keyword matches
    are strong relevance signals, especially for proper nouns and specific terms.
    Chunks appearing in both lists receive a bonus from both contributions.
    """

    def __init__(self, k_param: int = 60, text_weight: float = 1.5) -> None:
        self._k = k_param
        self._text_weight = text_weight

    def fuse(
        self,
        vector_results: list[RetrievedChunk],
        text_results: list[RetrievedChunk],
        top_k: int,
    ) -> list[RetrievedChunk]:
        """Combine two ranked lists via weighted RRF, return top_k results."""
        rrf_scores: dict[str, float] = {}
        chunk_map: dict[str, RetrievedChunk] = {}

        for rank, chunk in enumerate(vector_results):
            rrf_scores[chunk.chunk_id] = rrf_scores.get(chunk.chunk_id, 0.0)
            rrf_scores[chunk.chunk_id] += 1.0 / (self._k + rank + 1)
            chunk_map[chunk.chunk_id] = chunk

        for rank, chunk in enumerate(text_results):
            rrf_scores[chunk.chunk_id] = rrf_scores.get(chunk.chunk_id, 0.0)
            rrf_scores[chunk.chunk_id] += self._text_weight / (self._k + rank + 1)
            if chunk.chunk_id not in chunk_map:
                chunk_map[chunk.chunk_id] = chunk

        if not rrf_scores:
            return []

        # Sort by RRF score descending (higher = more relevant)
        sorted_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)

        # Normalize to cosine-distance-like score (0 = best) for compatibility
        max_rrf = rrf_scores[sorted_ids[0]]

        results = []
        for chunk_id in sorted_ids[:top_k]:
            chunk = chunk_map[chunk_id]
            relevance = rrf_scores[chunk_id] / max_rrf if max_rrf > 0 else 0.0
            results.append(replace(chunk, score=1.0 - relevance))

        return results
