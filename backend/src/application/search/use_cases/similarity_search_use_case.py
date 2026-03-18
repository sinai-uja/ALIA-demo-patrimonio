import logging

from src.application.search.dto.search_dto import (
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
        retrieval_k: int = 20,
    ) -> None:
        self._embedding_port = embedding_port
        self._vector_search_port = vector_search_port
        self._text_search_port = text_search_port
        self._hybrid_search_service = hybrid_search_service
        self._relevance_filter_service = relevance_filter_service
        self._reranking_service = reranking_service
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

        # 2. Vector search with filters
        vector_chunks = await self._vector_search_port.search(
            query_embedding=query_embedding,
            top_k=self._retrieval_k,
            heritage_type=dto.heritage_type_filter,
            province=dto.province_filter,
            municipality=dto.municipality_filter,
        )

        # 3. Text search with same filters
        text_chunks = await self._text_search_port.search(
            query=dto.query,
            top_k=self._retrieval_k,
            heritage_type=dto.heritage_type_filter,
            province=dto.province_filter,
            municipality=dto.municipality_filter,
        )

        # 4. Fuse via Reciprocal Rank Fusion
        fused_chunks = self._hybrid_search_service.fuse(
            vector_results=vector_chunks,
            text_results=text_chunks,
            top_k=self._retrieval_k,
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

        # 6. Rerank and keep top_k
        final_chunks = self._reranking_service.rerank(
            query=dto.query,
            chunks=filtered_chunks,
            top_k=dto.top_k,
        )

        # 7. Map RetrievedChunk -> SearchResultDTO
        results = [
            SearchResultDTO(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                title=chunk.title,
                heritage_type=chunk.heritage_type,
                province=chunk.province,
                municipality=chunk.municipality,
                url=chunk.url,
                content=chunk.content,
                score=chunk.score,
            )
            for chunk in final_chunks
        ]

        logger.info(
            "Similarity search complete: %d results", len(results),
        )

        return SimilaritySearchResponseDTO(
            results=results,
            query=dto.query,
            total_results=len(results),
        )
