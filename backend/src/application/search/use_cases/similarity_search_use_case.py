import logging
import time
from collections import defaultdict
from uuid import uuid4

from src.application.search.dto.search_dto import (
    ChunkHitDTO,
    SearchResultDTO,
    SimilaritySearchDTO,
    SimilaritySearchResponseDTO,
)
from src.config import settings
from src.domain.shared.ports.embedding_port import EmbeddingPort
from src.domain.rag.ports.text_search_port import TextSearchPort
from src.domain.rag.ports.vector_search_port import VectorSearchPort
from src.domain.rag.services.hybrid_search_service import HybridSearchService
from src.domain.rag.services.query_instruction_service import wrap_query_for_embedding
from src.domain.rag.services.relevance_filter_service import RelevanceFilterService
from src.domain.rag.services.reranking_service import RerankingService
from src.domain.search.ports.heritage_asset_lookup_port import (
    HeritageAssetLookupPort,
)

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
        self._similarity_filter = RelevanceFilterService(
            score_threshold=similarity_threshold,
        )

    async def execute(
        self, dto: SimilaritySearchDTO,
    ) -> SimilaritySearchResponseDTO:
        search_id = str(uuid4())
        t0 = time.monotonic()
        user_label = dto.user_id or "anonymous"
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
        embeddings = await self._embedding_port.embed([query_text])
        query_embedding = embeddings[0]

        # Over-fetch chunks so that after grouping by document we still
        # have enough unique assets to fill all requested pages.
        max_docs = dto.page * dto.page_size
        chunk_multiplier = 3
        retrieval_k = max(self._retrieval_k, max_docs) * chunk_multiplier

        # 2. Retrieve and score chunks — pure similarity or full hybrid pipeline
        vector_chunks = await self._vector_search_port.search(
            query_embedding=query_embedding,
            top_k=retrieval_k,
            heritage_type=dto.heritage_type_filter,
            province=dto.province_filter,
            municipality=dto.municipality_filter,
        )

        if self._similarity_only:
            # Pure similarity: vector search only, no fusion or reranking
            filtered_chunks = self._similarity_filter.filter(vector_chunks)
            logger.info(
                "Search results (similarity-only): search_id=%s vector=%d, filtered=%d,"
                " threshold=%.3f",
                search_id, len(vector_chunks), len(filtered_chunks),
                self._similarity_filter._score_threshold,
            )
            if self._reranker_enabled and filtered_chunks:
                # Neural reranking on similarity-only candidates
                final_chunks = await self._reranking_service.rerank(
                    query=search_query, chunks=filtered_chunks,
                    top_k=len(filtered_chunks),
                )
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
            text_chunks = await self._text_search_port.search(
                query=search_query,
                top_k=retrieval_k,
                heritage_type=dto.heritage_type_filter,
                province=dto.province_filter,
                municipality=dto.municipality_filter,
            )
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

        return SimilaritySearchResponseDTO(
            results=page_results,
            query=dto.query,
            total_results=total_results,
            page=dto.page,
            page_size=dto.page_size,
            total_pages=total_pages,
            search_id=search_id,
        )
