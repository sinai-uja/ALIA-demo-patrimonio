import logging
from collections import defaultdict

from src.application.search.dto.search_dto import (
    ChunkHitDTO,
    SearchResultDTO,
    SimilaritySearchDTO,
    SimilaritySearchResponseDTO,
)
from src.domain.rag.ports.embedding_port import EmbeddingPort
from src.domain.rag.ports.text_search_port import TextSearchPort
from src.domain.rag.ports.vector_search_port import VectorSearchPort
from src.domain.rag.services.hybrid_search_service import HybridSearchService
from src.domain.rag.services.relevance_filter_service import (
    RelevanceFilterService,
)
from src.domain.rag.services.reranking_service import RerankingService
from src.domain.search.ports.heritage_asset_lookup_port import (
    HeritageAssetLookupPort,
)

logger = logging.getLogger("iaph.search")


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
    ) -> None:
        self._embedding_port = embedding_port
        self._vector_search_port = vector_search_port
        self._text_search_port = text_search_port
        self._hybrid_search_service = hybrid_search_service
        self._relevance_filter_service = relevance_filter_service
        self._reranking_service = reranking_service
        self._heritage_asset_lookup_port = heritage_asset_lookup_port
        self._retrieval_k = retrieval_k

    async def execute(
        self, dto: SimilaritySearchDTO,
    ) -> SimilaritySearchResponseDTO:
        logger.info(
            "Similarity search start: query=%s", dto.query[:80],
        )

        # 1. Embed the user query
        embeddings = await self._embedding_port.embed([dto.query])
        query_embedding = embeddings[0]

        # Over-fetch chunks so that after grouping by document we still
        # have enough unique assets to fill all requested pages.
        max_docs = dto.page * dto.page_size
        chunk_multiplier = 3
        retrieval_k = max(self._retrieval_k, max_docs) * chunk_multiplier

        # 2. Vector search with filters
        vector_chunks = await self._vector_search_port.search(
            query_embedding=query_embedding,
            top_k=retrieval_k,
            heritage_type=dto.heritage_type_filter,
            province=dto.province_filter,
            municipality=dto.municipality_filter,
        )

        # 3. Text search with same filters
        text_chunks = await self._text_search_port.search(
            query=dto.query,
            top_k=retrieval_k,
            heritage_type=dto.heritage_type_filter,
            province=dto.province_filter,
            municipality=dto.municipality_filter,
        )

        # 4. Fuse via Reciprocal Rank Fusion
        fused_chunks = self._hybrid_search_service.fuse(
            vector_results=vector_chunks,
            text_results=text_chunks,
            top_k=retrieval_k,
        )

        # 5. Filter by relevance score threshold
        filtered_chunks = self._relevance_filter_service.filter(
            fused_chunks,
        )

        logger.info(
            "Search results: vector=%d, fts=%d, fused=%d, filtered=%d",
            len(vector_chunks),
            len(text_chunks),
            len(fused_chunks),
            len(filtered_chunks),
        )

        # 6. Rerank all filtered chunks (pagination happens after grouping)
        final_chunks = self._reranking_service.rerank(
            query=dto.query,
            chunks=filtered_chunks,
            top_k=len(filtered_chunks),
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

        logger.info(
            "Similarity search complete: %d total, page %d/%d (%d chunks)",
            total_results,
            dto.page,
            total_pages,
            len(final_chunks),
        )

        return SimilaritySearchResponseDTO(
            results=page_results,
            query=dto.query,
            total_results=total_results,
            page=dto.page,
            page_size=dto.page_size,
            total_pages=total_pages,
        )
