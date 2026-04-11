from __future__ import annotations

import logging
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

from src.application.search.dto.search_dto import (
    ChunkHitDTO,
    SearchResultDTO,
    SimilaritySearchDTO,
    SimilaritySearchResponseDTO,
)
from src.config import settings
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


class SimilaritySearchUseCase:
    """Orchestrates RAG steps 1-6 (embed, search, fuse, filter, rerank)
    without LLM generation, returning ranked document chunks."""

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
        self._trace_repo = trace_repository
        self._similarity_filter = RelevanceFilterService(
            score_threshold=similarity_threshold,
        )

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
        logger.info(
            "Similarity search start: search_id=%s user=%s query=%s filters=%s",
            search_id, user_label, dto.query[:80], filter_str,
        )

        # 1. Embed the user query (with instruction prefix for Qwen3)
        # Normalize to lowercase for consistent embedding/reranking regardless of casing
        search_query = dto.query.lower()
        query_text = wrap_query_for_embedding(search_query, settings.embedding_query_instruction)
        t_embed = time.perf_counter()
        embeddings = await self._embedding_port.embed([query_text])
        embed_ms = (time.perf_counter() - t_embed) * 1000
        query_embedding = embeddings[0]

        # Over-fetch chunks so that after grouping by document we still
        # have enough unique assets to fill all requested pages.
        max_docs = dto.page * dto.page_size
        chunk_multiplier = 3
        retrieval_k = max(self._retrieval_k, max_docs) * chunk_multiplier

        # 2. Retrieve and score chunks — pure similarity or full hybrid pipeline
        t_vsearch = time.perf_counter()
        vector_chunks = await self._vector_search_port.search(
            query_embedding=query_embedding,
            top_k=retrieval_k,
            heritage_type=dto.heritage_type_filter,
            province=dto.province_filter,
            municipality=dto.municipality_filter,
        )

        vsearch_ms = (time.perf_counter() - t_vsearch) * 1000
        trace_steps: list[dict] = []
        text_chunks_count = 0
        reranker_used = False

        if self._similarity_only:
            # Pure similarity: vector search only, no fusion or reranking
            filtered_chunks = self._similarity_filter.filter(vector_chunks)
            logger.info(
                "Search results (similarity-only): search_id=%s vector=%d, filtered=%d,"
                " threshold=%.3f",
                search_id, len(vector_chunks), len(filtered_chunks),
                self._similarity_filter._score_threshold,
            )
            reranker_ms = 0.0
            if self._reranker_enabled and filtered_chunks:
                # Neural reranking on similarity-only candidates
                t_rerank = time.perf_counter()
                final_chunks = await self._reranking_service.rerank(
                    query=search_query, chunks=filtered_chunks,
                    top_k=len(filtered_chunks),
                )
                reranker_ms = (time.perf_counter() - t_rerank) * 1000
                reranker_used = True
            else:
                final_chunks = sorted(filtered_chunks, key=lambda c: c.score)
            for i, chunk in enumerate(final_chunks[:20], 1):
                logger.info(
                    "Similarity #%d: search_id=%s score=%.4f | title: %s"
                    " | type: %s | province: %s",
                    i, search_id, chunk.score, chunk.title[:60],
                    chunk.heritage_type, chunk.province,
                )
        else:
            # Full hybrid pipeline: text search + RRF fusion + reranking
            t_tsearch = time.perf_counter()
            text_chunks = await self._text_search_port.search(
                query=search_query,
                top_k=retrieval_k,
                heritage_type=dto.heritage_type_filter,
                province=dto.province_filter,
                municipality=dto.municipality_filter,
            )
            tsearch_ms = (time.perf_counter() - t_tsearch) * 1000
            text_chunks_count = len(text_chunks)
            fused_chunks = self._hybrid_search_service.fuse(
                vector_results=vector_chunks,
                text_results=text_chunks,
                top_k=retrieval_k,
            )
            filtered_chunks = self._relevance_filter_service.filter(fused_chunks)
            logger.info(
                "Search results: search_id=%s vector=%d, fts=%d, fused=%d, filtered=%d",
                search_id, len(vector_chunks), len(text_chunks),
                len(fused_chunks), len(filtered_chunks),
            )
            t_rerank = time.perf_counter()
            if self._reranker_enabled:
                final_chunks = await self._reranking_service.rerank(
                    query=search_query,
                    chunks=filtered_chunks,
                    top_k=len(filtered_chunks),
                )
            else:
                final_chunks = self._reranking_service.rerank(
                    query=search_query,
                    chunks=filtered_chunks,
                    top_k=len(filtered_chunks),
                )
            reranker_ms = (time.perf_counter() - t_rerank) * 1000
            reranker_used = True
            for i, chunk in enumerate(final_chunks[:20], 1):
                logger.info(
                    "Hybrid #%d: search_id=%s score=%.4f | title: %s"
                    " | type: %s | province: %s",
                    i, search_id, chunk.score, chunk.title[:60],
                    chunk.heritage_type, chunk.province,
                )

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
            "Similarity search complete: search_id=%s user=%s %d total, page %d/%d"
            " (%d chunks) %.0fms",
            search_id,
            user_label,
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

        # --- Trace instrumentation ---
        if self._trace_repo:
            try:
                from src.domain.shared.entities.execution_trace import ExecutionTrace

                pipeline_mode = "similarity-only" if self._similarity_only else "hybrid"
                trace_steps = [
                    {
                        "step": "embedding",
                        "input": {"text": dto.query[:80], "chars": len(dto.query)},
                        "output": {"dim": len(query_embedding)},
                        "elapsed_ms": round(embed_ms, 1),
                    },
                    {
                        "step": "vector_search",
                        "input": {"top_k": retrieval_k, "filters": filter_str},
                        "output": {
                            "count": len(vector_chunks),
                            "top_score": round(vector_chunks[0].score, 4) if vector_chunks else None,
                        },
                        "results": [
                            {"rank": i, "score": round(c.score, 4), "title": c.title[:60],
                             "type": c.heritage_type, "document_id": c.document_id}
                            for i, c in enumerate(vector_chunks[:15], 1)
                        ],
                        "elapsed_ms": round(vsearch_ms, 1),
                    },
                ]
                if not self._similarity_only:
                    trace_steps.append({
                        "step": "text_search",
                        "input": {"query": search_query[:80], "top_k": retrieval_k},
                        "output": {"count": text_chunks_count},
                        "elapsed_ms": round(tsearch_ms, 1),
                    })
                    trace_steps.append({
                        "step": "fusion",
                        "input": {"vector": len(vector_chunks), "text": text_chunks_count},
                        "output": {"fused": len(fused_chunks), "filtered": len(filtered_chunks)},
                    })
                if reranker_used:
                    trace_steps.append({
                        "step": "reranker",
                        "input": {"candidates": len(filtered_chunks)},
                        "output": {
                            "count": len(final_chunks),
                            "top_score": round(final_chunks[0].score, 4) if final_chunks else None,
                        },
                        "results": [
                            {"rank": i, "score": round(c.score, 4), "title": c.title[:60],
                             "type": c.heritage_type, "document_id": c.document_id}
                            for i, c in enumerate(final_chunks[:10], 1)
                        ],
                        "elapsed_ms": round(reranker_ms, 1),
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
                    },
                    feedback_value=None,
                    status="success",
                    created_at=datetime.now(timezone.utc),
                )
                await self._trace_repo.save(trace)
            except Exception:
                logger.warning("Failed to save execution trace", exc_info=True)

        return response
