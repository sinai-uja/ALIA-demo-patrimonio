from dataclasses import replace

from src.domain.rag.entities.retrieved_chunk import RetrievedChunk

# Default lexical weight that preserves the legacy RAG ranking behavior.
# The previous implementation used a fixed ``text_weight=1.5`` for the
# text-search contribution while vector contributions used weight ``1.0``.
# That is equivalent — after the final RRF normalization — to splitting a
# unit weight as ``lexical=0.6`` / ``semantic=0.4`` (ratio 1.5). Existing
# callers that do not pass ``lexical_weight`` (notably the RAG use case)
# therefore keep their previous ranking unchanged.
_LEGACY_LEXICAL_WEIGHT = 0.6


class HybridSearchService:
    """Fuses vector and full-text search results using Reciprocal Rank Fusion.

    The relative weight between lexical (text) and semantic (vector) signals
    is parameterised per call via ``lexical_weight`` in ``[0.0, 1.0]``:

    - ``lexical_weight=0.0`` → ranking driven entirely by vector results.
    - ``lexical_weight=1.0`` → ranking driven entirely by text results.
    - ``lexical_weight=0.5`` → balanced fusion.

    ``semantic_weight = 1.0 - lexical_weight``.

    Output scores are normalized against the **theoretical maximum** RRF a
    chunk could obtain (rank 0 in both lists, with the full unit weight), not
    against the batch maximum. This avoids the misleading "every #1 looks
    100% relevant" effect of relative normalization and yields scores that
    actually reflect retrieval confidence (weak matches end up with high
    cosine-distance-like scores). ``score = 1 - min(1, rrf / theoretical_max)``.
    """

    def __init__(self, k_param: int = 60) -> None:
        self._k = k_param

    def fuse(
        self,
        vector_results: list[RetrievedChunk],
        text_results: list[RetrievedChunk],
        top_k: int,
        lexical_weight: float = _LEGACY_LEXICAL_WEIGHT,
    ) -> list[RetrievedChunk]:
        """Combine two ranked lists via weighted RRF, return top_k results."""
        # Clamp defensively in domain — outer layers should already validate,
        # but this keeps the formula well-defined under any input.
        if lexical_weight < 0.0:
            lexical_weight = 0.0
        elif lexical_weight > 1.0:
            lexical_weight = 1.0
        semantic_weight = 1.0 - lexical_weight

        rrf_scores: dict[str, float] = {}
        chunk_map: dict[str, RetrievedChunk] = {}

        for rank, chunk in enumerate(vector_results):
            rrf_scores[chunk.chunk_id] = rrf_scores.get(chunk.chunk_id, 0.0)
            rrf_scores[chunk.chunk_id] += semantic_weight / (self._k + rank + 1)
            chunk_map[chunk.chunk_id] = chunk

        for rank, chunk in enumerate(text_results):
            rrf_scores[chunk.chunk_id] = rrf_scores.get(chunk.chunk_id, 0.0)
            rrf_scores[chunk.chunk_id] += lexical_weight / (self._k + rank + 1)
            if chunk.chunk_id not in chunk_map:
                chunk_map[chunk.chunk_id] = chunk

        if not rrf_scores:
            return []

        # Sort by RRF score descending (higher = more relevant).
        sorted_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)

        # Theoretical maximum: a chunk that ranks #1 in BOTH lists with the
        # full unit weight (semantic + lexical = 1). Using this absolute
        # anchor — instead of the batch maximum — prevents the top-ranked
        # result from always scoring ~100% even when retrieval is weak.
        theoretical_max = (semantic_weight + lexical_weight) / (self._k + 1)

        results = []
        for chunk_id in sorted_ids[:top_k]:
            chunk = chunk_map[chunk_id]
            if theoretical_max > 0:
                relevance = min(1.0, rrf_scores[chunk_id] / theoretical_max)
            else:
                relevance = 0.0
            results.append(replace(chunk, score=1.0 - relevance))

        return results
