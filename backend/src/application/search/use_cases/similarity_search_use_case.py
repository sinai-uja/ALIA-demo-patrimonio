from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from src.application.search.dto.search_dto import (
    ChunkHitDTO,
    SearchResultDTO,
    SimilaritySearchDTO,
    SimilaritySearchResponseDTO,
)
from src.config import settings
from src.domain.rag.entities.retrieved_chunk import RetrievedChunk
from src.domain.rag.ports.text_search_port import TextSearchPort
from src.domain.rag.ports.vector_search_port import VectorSearchPort
from src.domain.rag.services.hybrid_search_service import HybridSearchService
from src.domain.rag.services.query_instruction_service import wrap_query_for_embedding
from src.domain.rag.services.relevance_filter_service import RelevanceFilterService
from src.domain.rag.services.reranking_service import RerankingService
from src.domain.search.ports.heritage_asset_lookup_port import (
    HeritageAssetLookupPort,
)
from src.domain.shared.ports.embedding_port import EmbeddingPort

if TYPE_CHECKING:
    from src.domain.shared.ports.trace_repository import TraceRepository

logger = logging.getLogger("iaph.search.similarity_search")


def _normalize_text_scores(
    chunks: list[RetrievedChunk],
) -> list[RetrievedChunk]:
    """Convert raw FTS ranks (higher=better) into a cosine-distance-like score
    (lower=better) so the downstream relevance filter works uniformly.
    """
    if not chunks:
        return []
    # Text adapter already orders by score DESC, but be defensive.
    sorted_chunks = sorted(chunks, key=lambda c: c.score, reverse=True)
    max_score = sorted_chunks[0].score if sorted_chunks[0].score > 0 else 1.0
    return [
        replace(c, score=1.0 - (c.score / max_score) if max_score > 0 else 1.0)
        for c in sorted_chunks
    ]


class SimilaritySearchUseCase:
    """Orchestrates RAG steps 1-6 (embed, search, fuse, filter, rerank)
    without LLM generation, returning ranked document chunks.

    The retrieval mode is selected per request via
    ``SimilaritySearchDTO.lexical_weight`` (or the configured server default
    when omitted):

    - ``effective_weight == 0.0`` → semantic-only (vector + optional rerank).
    - ``effective_weight == 1.0`` → lexical-only (text search only).
    - ``effective_weight in (0.0, 1.0)`` → hybrid (vector + optional rerank
      applied to the vector lane only, then RRF-fused with text results).

    The reranker — when enabled — is intentionally applied *before* fusion,
    only over the vector lane. This is what resolves the "Zurbarán" 1-token
    case where the cross-encoder would otherwise penalise strong lexical
    matches that lack a semantic signal.
    """

    def __init__(
        self,
        embedding_port: EmbeddingPort,
        vector_search_port: VectorSearchPort,
        text_search_port: TextSearchPort,
        hybrid_search_service: HybridSearchService,
        relevance_filter_service: RelevanceFilterService,
        reranking_service: RerankingService,
        heritage_asset_lookup_port: HeritageAssetLookupPort,
        retrieval_k: int = 20,
        similarity_only: bool = False,
        similarity_threshold: float = 0.25,
        reranker_enabled: bool = False,
        default_lexical_weight: float = 0.5,
        trace_repository: TraceRepository | None = None,
    ) -> None:
        self._embedding_port = embedding_port
        self._vector_search_port = vector_search_port
        self._text_search_port = text_search_port
        self._hybrid_search_service = hybrid_search_service
        self._relevance_filter_service = relevance_filter_service
        self._reranking_service = reranking_service
        self._heritage_asset_lookup_port = heritage_asset_lookup_port
        self._retrieval_k = retrieval_k
        self._similarity_only = similarity_only
        self._reranker_enabled = reranker_enabled
        self._default_lexical_weight = default_lexical_weight
        self._trace_repo = trace_repository
        self._similarity_filter = RelevanceFilterService(
            score_threshold=similarity_threshold,
        )

    def _resolve_effective_weight(self, dto: SimilaritySearchDTO) -> float:
        """Resolve the effective lexical weight for this request.

        Priority:
        1. If the request carries an explicit ``lexical_weight`` → use it
           (user intent always wins).
        2. Else, if the server is configured in similarity-only mode →
           force 0.0 (pure semantic).
        3. Else → fall back to the configured server default.
        """
        if dto.lexical_weight is not None:
            return dto.lexical_weight
        if self._similarity_only:
            return 0.0
        return self._default_lexical_weight

    async def execute(
        self, dto: SimilaritySearchDTO,
    ) -> SimilaritySearchResponseDTO:
        search_id = str(uuid4())
        t0 = time.monotonic()
        user_label = dto.username or "anonymous"
        filters = []
        if dto.heritage_type_filter:
            filters.append(f"type={dto.heritage_type_filter}")
        if dto.province_filter:
            filters.append(f"province={dto.province_filter}")
        if dto.municipality_filter:
            filters.append(f"municipality={dto.municipality_filter}")
        filter_str = " ".join(filters) if filters else "none"

        # Decide retrieval mode from the slider value.
        effective_weight = self._resolve_effective_weight(dto)
        if effective_weight <= 0.0:
            pipeline_mode = "semantic-only"
        elif effective_weight >= 1.0:
            pipeline_mode = "lexical-only"
        else:
            pipeline_mode = "hybrid"

        logger.info(
            "Similarity search start: search_id=%s user=%s query=%s "
            "filters=%s mode=%s lexical_weight=%.3f (request=%s, default=%.3f)",
            search_id, user_label, dto.query[:80], filter_str,
            pipeline_mode, effective_weight,
            "yes" if dto.lexical_weight is not None else "no",
            self._default_lexical_weight,
        )

        # Normalize query for consistent embedding/reranking regardless of casing.
        search_query = dto.query.lower()

        # Over-fetch chunks so that after grouping by document we still
        # have enough unique assets to fill all requested pages.
        max_docs = dto.page * dto.page_size
        chunk_multiplier = 3
        retrieval_k = max(self._retrieval_k, max_docs) * chunk_multiplier

        # State tracked for the trace step at the end.
        embed_ms = 0.0
        vsearch_ms = 0.0
        tsearch_ms = 0.0
        reranker_ms = 0.0
        query_embedding: list[float] = []
        vector_chunks: list[RetrievedChunk] = []
        text_chunks: list[RetrievedChunk] = []
        fused_chunks: list[RetrievedChunk] = []
        reranked_chunks: list[RetrievedChunk] = []
        reranker_used = False

        # --- Pipeline branches -----------------------------------------------
        if pipeline_mode == "lexical-only":
            # Lexical-only: no embedding, no vector search, no rerank.
            # Use the relevance filter on normalized FTS scores.
            t_tsearch = time.perf_counter()
            text_chunks = await self._text_search_port.search(
                query=search_query,
                top_k=retrieval_k,
                heritage_type=dto.heritage_type_filter,
                province=dto.province_filter,
                municipality=dto.municipality_filter,
            )
            tsearch_ms = (time.perf_counter() - t_tsearch) * 1000

            normalized_text = _normalize_text_scores(text_chunks)
            filtered_chunks = self._relevance_filter_service.filter(
                normalized_text, override_threshold=dto.score_threshold,
            )
            final_chunks = sorted(filtered_chunks, key=lambda c: c.score)
            effective_threshold = (
                dto.score_threshold
                if dto.score_threshold is not None
                else self._relevance_filter_service._score_threshold
            )
            logger.info(
                "Search results (lexical-only): search_id=%s text=%d, "
                "filtered=%d, threshold=%.3f",
                search_id, len(text_chunks),
                len(final_chunks), effective_threshold,
            )
            for i, chunk in enumerate(final_chunks[:20], 1):
                logger.info(
                    "Lexical #%d: search_id=%s score=%.4f | title: %s"
                    " | type: %s | province: %s",
                    i, search_id, chunk.score, chunk.title[:60],
                    chunk.heritage_type, chunk.province,
                )

        elif pipeline_mode == "semantic-only":
            # Semantic-only: embed → vector search → optional rerank → filter.
            query_text = wrap_query_for_embedding(
                search_query, settings.embedding_query_instruction,
            )
            t_embed = time.perf_counter()
            embeddings = await self._embedding_port.embed([query_text])
            embed_ms = (time.perf_counter() - t_embed) * 1000
            query_embedding = embeddings[0]

            t_vsearch = time.perf_counter()
            vector_chunks = await self._vector_search_port.search(
                query_embedding=query_embedding,
                top_k=retrieval_k,
                heritage_type=dto.heritage_type_filter,
                province=dto.province_filter,
                municipality=dto.municipality_filter,
            )
            vsearch_ms = (time.perf_counter() - t_vsearch) * 1000

            if self._reranker_enabled and vector_chunks:
                t_rerank = time.perf_counter()
                reranked_chunks = await self._reranking_service.rerank(
                    query=search_query, chunks=vector_chunks,
                    top_k=len(vector_chunks),
                )
                reranker_ms = (time.perf_counter() - t_rerank) * 1000
                reranker_used = True
                filtered_chunks = self._similarity_filter.filter(
                    reranked_chunks, override_threshold=dto.score_threshold,
                )
            else:
                # No reranker: fall back to filtering on raw cosine distance.
                filtered_chunks = self._similarity_filter.filter(
                    vector_chunks, override_threshold=dto.score_threshold,
                )
            effective_threshold = (
                dto.score_threshold
                if dto.score_threshold is not None
                else self._similarity_filter._score_threshold
            )
            final_chunks = sorted(filtered_chunks, key=lambda c: c.score)
            logger.info(
                "Search results (semantic-only): search_id=%s vector=%d,"
                " reranked=%s, filtered=%d, threshold=%.3f",
                search_id, len(vector_chunks),
                "yes" if reranker_used else "no",
                len(final_chunks), effective_threshold,
            )
            for i, chunk in enumerate(final_chunks[:20], 1):
                logger.info(
                    "Semantic #%d: search_id=%s score=%.4f | title: %s"
                    " | type: %s | province: %s",
                    i, search_id, chunk.score, chunk.title[:60],
                    chunk.heritage_type, chunk.province,
                )

        else:
            # Hybrid: embed → vector search → optional rerank (vector lane only)
            #          → text search → RRF fuse → relevance filter.
            #
            # NB: The reranker runs *before* the fusion, only over the semantic
            # lane. That is the architectural fix for the "Zurbarán" case:
            # we never let the cross-encoder shadow a strong lexical match.
            query_text = wrap_query_for_embedding(
                search_query, settings.embedding_query_instruction,
            )
            t_embed = time.perf_counter()
            embeddings = await self._embedding_port.embed([query_text])
            embed_ms = (time.perf_counter() - t_embed) * 1000
            query_embedding = embeddings[0]

            t_vsearch = time.perf_counter()
            vector_chunks = await self._vector_search_port.search(
                query_embedding=query_embedding,
                top_k=retrieval_k,
                heritage_type=dto.heritage_type_filter,
                province=dto.province_filter,
                municipality=dto.municipality_filter,
            )
            vsearch_ms = (time.perf_counter() - t_vsearch) * 1000

            # Rerank the vector lane (semantic only) — never the text lane.
            if self._reranker_enabled and vector_chunks:
                t_rerank = time.perf_counter()
                reranked_chunks = await self._reranking_service.rerank(
                    query=search_query, chunks=vector_chunks,
                    top_k=len(vector_chunks),
                )
                reranker_ms = (time.perf_counter() - t_rerank) * 1000
                reranker_used = True
                vector_lane = reranked_chunks
            else:
                vector_lane = vector_chunks

            t_tsearch = time.perf_counter()
            text_chunks = await self._text_search_port.search(
                query=search_query,
                top_k=retrieval_k,
                heritage_type=dto.heritage_type_filter,
                province=dto.province_filter,
                municipality=dto.municipality_filter,
            )
            tsearch_ms = (time.perf_counter() - t_tsearch) * 1000

            fused_chunks = self._hybrid_search_service.fuse(
                vector_results=vector_lane,
                text_results=text_chunks,
                top_k=retrieval_k,
                lexical_weight=effective_weight,
            )
            filtered_chunks = self._relevance_filter_service.filter(
                fused_chunks, override_threshold=dto.score_threshold,
            )
            effective_threshold = (
                dto.score_threshold
                if dto.score_threshold is not None
                else self._relevance_filter_service._score_threshold
            )
            final_chunks = sorted(filtered_chunks, key=lambda c: c.score)
            logger.info(
                "Search results (hybrid lex=%.2f sem=%.2f): search_id=%s "
                "vector=%d, fts=%d, reranked=%s, fused=%d, filtered=%d, "
                "threshold=%.3f",
                effective_weight, 1.0 - effective_weight,
                search_id, len(vector_chunks), len(text_chunks),
                "yes" if reranker_used else "no",
                len(fused_chunks), len(final_chunks), effective_threshold,
            )
            for i, chunk in enumerate(final_chunks[:20], 1):
                logger.info(
                    "Hybrid #%d: search_id=%s score=%.4f | title: %s"
                    " | type: %s | province: %s",
                    i, search_id, chunk.score, chunk.title[:60],
                    chunk.heritage_type, chunk.province,
                )

        # --- Shared enrichment / grouping / pagination ----------------------
        # 7. Enrich with heritage asset data
        unique_doc_ids = list({c.document_id for c in final_chunks})
        asset_map = await self._heritage_asset_lookup_port.get_summaries_by_ids(
            unique_doc_ids,
        )

        # 8. Group chunks by document_id
        groups: dict[str, list] = defaultdict(list)
        first_chunk: dict[str, object] = {}
        for chunk in final_chunks:
            groups[chunk.document_id].append(chunk)
            if chunk.document_id not in first_chunk:
                first_chunk[chunk.document_id] = chunk

        # 9. Build grouped SearchResultDTOs (one per asset)
        results = []
        for doc_id in first_chunk:
            chunk = first_chunk[doc_id]
            asset = asset_map.get(doc_id)
            chunk_hits = sorted(
                groups[doc_id], key=lambda c: c.score,
            )
            results.append(
                SearchResultDTO(
                    document_id=doc_id,
                    title=chunk.title,
                    heritage_type=chunk.heritage_type,
                    province=(
                        asset.province or chunk.province
                        if asset else chunk.province
                    ),
                    municipality=(
                        asset.municipality or chunk.municipality
                        if asset else chunk.municipality
                    ),
                    url=chunk.url,
                    best_score=chunk_hits[0].score,
                    chunks=[
                        ChunkHitDTO(
                            chunk_id=c.chunk_id,
                            content=c.content,
                            score=c.score,
                        )
                        for c in chunk_hits
                    ],
                    denomination=asset.denomination if asset else None,
                    description=asset.description if asset else None,
                    latitude=asset.latitude if asset else None,
                    longitude=asset.longitude if asset else None,
                    image_url=asset.image_url if asset else None,
                    protection=asset.protection if asset else None,
                ),
            )

        results.sort(key=lambda r: r.best_score)

        # Paginate grouped results
        total_results = len(results)
        total_pages = max(1, -(-total_results // dto.page_size))
        start = (dto.page - 1) * dto.page_size
        page_results = results[start : start + dto.page_size]

        elapsed_ms = (time.monotonic() - t0) * 1000
        logger.info(
            "Similarity search complete: search_id=%s user=%s mode=%s "
            "%d total, page %d/%d (%d chunks) %.0fms",
            search_id,
            user_label,
            pipeline_mode,
            total_results,
            dto.page,
            total_pages,
            len(final_chunks),
            elapsed_ms,
        )

        response = SimilaritySearchResponseDTO(
            results=page_results,
            query=dto.query,
            total_results=total_results,
            page=dto.page,
            page_size=dto.page_size,
            total_pages=total_pages,
            search_id=search_id,
        )

        # --- Trace instrumentation ------------------------------------------
        if self._trace_repo:
            try:
                from src.domain.shared.entities.execution_trace import ExecutionTrace

                trace_steps: list[dict] = []

                if pipeline_mode != "lexical-only":
                    trace_steps.append({
                        "step": "embedding",
                        "input": {"text": dto.query[:80], "chars": len(dto.query)},
                        "output": {"dim": len(query_embedding)},
                        "elapsed_ms": round(embed_ms, 1),
                    })
                    vector_top_score = (
                        round(vector_chunks[0].score, 4) if vector_chunks else None
                    )
                    trace_steps.append({
                        "step": "vector_search",
                        "input": {"top_k": retrieval_k, "filters": filter_str},
                        "output": {
                            "count": len(vector_chunks),
                            "top_score": vector_top_score,
                        },
                        "results": [
                            {"rank": i, "score": round(c.score, 4), "title": c.title[:60],
                             "type": c.heritage_type, "document_id": c.document_id}
                            for i, c in enumerate(vector_chunks[:15], 1)
                        ],
                        "elapsed_ms": round(vsearch_ms, 1),
                    })

                if reranker_used:
                    trace_steps.append({
                        "step": "reranker",
                        "input": {
                            "candidates": len(vector_chunks),
                            "lane": "vector" if pipeline_mode == "hybrid" else "all",
                        },
                        "output": {"count": len(reranked_chunks)},
                        "elapsed_ms": round(reranker_ms, 1),
                    })

                if pipeline_mode in ("hybrid", "lexical-only"):
                    trace_steps.append({
                        "step": "text_search",
                        "input": {"query": search_query[:80], "top_k": retrieval_k},
                        "output": {"count": len(text_chunks)},
                        "elapsed_ms": round(tsearch_ms, 1),
                    })

                if pipeline_mode == "hybrid":
                    trace_steps.append({
                        "step": "fusion",
                        "input": {
                            "vector": len(vector_chunks),
                            "text": len(text_chunks),
                            "lexical_weight": round(effective_weight, 3),
                            "semantic_weight": round(1.0 - effective_weight, 3),
                        },
                        "output": {"fused": len(fused_chunks)},
                    })

                trace_steps.append({
                    "step": "score_filter",
                    "input": {
                        "threshold": effective_threshold,
                        "override": dto.score_threshold,
                    },
                    "output": {
                        "post_filter": len(final_chunks),
                        "top_score": round(final_chunks[0].score, 4) if final_chunks else None,
                    },
                    "results": [
                        {"rank": i, "score": round(c.score, 4), "title": c.title[:60],
                         "type": c.heritage_type, "document_id": c.document_id}
                        for i, c in enumerate(final_chunks[:10], 1)
                    ],
                })
                trace_steps.append({
                    "step": "results",
                    "output": {
                        "total_results": total_results,
                        "page": dto.page,
                        "total_pages": total_pages,
                        "page_size": dto.page_size,
                    },
                    "results": [
                        {"rank": start + i, "score": round(r.best_score, 4), "title": r.title[:60],
                         "type": r.heritage_type, "document_id": r.document_id}
                        for i, r in enumerate(page_results, 1)
                    ],
                })
                top_score = final_chunks[0].score if final_chunks else None
                trace = ExecutionTrace(
                    id=uuid4(),
                    execution_type="search",
                    execution_id=search_id,
                    user_id=dto.user_id,
                    username=dto.username,
                    user_profile_type=dto.user_profile_type,
                    query=dto.query,
                    pipeline_mode=pipeline_mode,
                    steps=trace_steps,
                    summary={
                        "total_results": total_results,
                        "elapsed_ms": round(elapsed_ms, 1),
                        "top_score": round(top_score, 4) if top_score is not None else None,
                        "chunks_retrieved": len(final_chunks),
                        "reranker_enabled": self._reranker_enabled,
                        "score_threshold_effective": round(effective_threshold, 4),
                        "score_threshold_override": (
                            round(dto.score_threshold, 4)
                            if dto.score_threshold is not None
                            else None
                        ),
                        "lexical_weight_effective": round(effective_weight, 4),
                        "lexical_weight_override": (
                            round(dto.lexical_weight, 4)
                            if dto.lexical_weight is not None
                            else None
                        ),
                    },
                    feedback_value=None,
                    status="success",
                    created_at=datetime.now(UTC),
                )
                await self._trace_repo.save(trace)
            except Exception:
                logger.warning("Failed to save execution trace", exc_info=True)

        return response
