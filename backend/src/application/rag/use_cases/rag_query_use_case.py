import logging

from src.application.rag.dto.rag_dto import RAGQueryDTO, RAGResponseDTO, SourceDTO
from src.domain.rag.ports.embedding_port import EmbeddingPort
from src.domain.rag.ports.llm_port import LLMPort
from src.domain.rag.ports.text_search_port import TextSearchPort
from src.domain.rag.ports.vector_search_port import VectorSearchPort
from src.domain.rag.prompts import SYSTEM_PROMPT, build_user_prompt
from src.domain.rag.services.context_assembly_service import ContextAssemblyService
from src.domain.rag.services.hybrid_search_service import HybridSearchService
from src.domain.rag.services.relevance_filter_service import RelevanceFilterService
from src.domain.rag.services.reranking_service import RerankingService

logger = logging.getLogger("iaph.llm")

ABSTENTION_ANSWER = (
    "No he encontrado informacion suficientemente relevante en la base de datos del IAPH "
    "para responder a tu pregunta. Por favor, reformula tu consulta o proporciona mas detalles."
)


class RAGQueryUseCase:
    """Orchestrates the full RAG pipeline: embed -> hybrid search -> filter -> assemble -> generate.

    """

    def __init__(
        self,
        embedding_port: EmbeddingPort,
        vector_search_port: VectorSearchPort,
        text_search_port: TextSearchPort,
        llm_port: LLMPort,
        context_assembly_service: ContextAssemblyService,
        relevance_filter_service: RelevanceFilterService,
        hybrid_search_service: HybridSearchService,
        reranking_service: RerankingService,
        retrieval_k: int = 20,
    ) -> None:
        self._embedding_port = embedding_port
        self._vector_search_port = vector_search_port
        self._text_search_port = text_search_port
        self._llm_port = llm_port
        self._context_assembly_service = context_assembly_service
        self._relevance_filter_service = relevance_filter_service
        self._hybrid_search_service = hybrid_search_service
        self._reranking_service = reranking_service
        self._retrieval_k = retrieval_k

    async def execute(self, dto: RAGQueryDTO) -> RAGResponseDTO:
        logger.info("RAG pipeline start: query=%s", dto.query[:80])

        # 1. Embed the user query
        embeddings = await self._embedding_port.embed([dto.query])
        query_embedding = embeddings[0]
        logger.info(
            "Query embedded: %d chars → %d-dim vector", len(dto.query), len(query_embedding),
        )

        # 2. Run vector search and full-text search sequentially
        #    (both adapters share the same DB session, so parallel is not safe)
        vector_chunks = await self._vector_search_port.search(
            query_embedding=query_embedding,
            top_k=self._retrieval_k,
            heritage_type=dto.heritage_type_filter,
            province=dto.province_filter,
            municipality=dto.municipality_filter,
        )
        text_chunks = await self._text_search_port.search(
            query=dto.query,
            top_k=self._retrieval_k,
            heritage_type=dto.heritage_type_filter,
            province=dto.province_filter,
            municipality=dto.municipality_filter,
        )

        # 3. Fuse results via Reciprocal Rank Fusion
        fused_chunks = self._hybrid_search_service.fuse(
            vector_results=vector_chunks,
            text_results=text_chunks,
            top_k=self._retrieval_k,
        )

        # 4. Filter by relevance score threshold
        filtered_chunks = self._relevance_filter_service.filter(fused_chunks)

        logger.info(
            "Search results: vector=%d, fts=%d, fused=%d, filtered=%d",
            len(vector_chunks), len(text_chunks), len(fused_chunks), len(filtered_chunks),
        )

        # 5. If no chunks pass the threshold, abstain
        if not filtered_chunks:
            logger.info("Abstaining: no chunks passed relevance threshold")
            return RAGResponseDTO(
                answer=ABSTENTION_ANSWER,
                sources=[],
                query=dto.query,
                abstained=True,
            )

        # 6. Re-rank using heuristic signals and keep top_k
        final_chunks = self._reranking_service.rerank(
            query=dto.query,
            chunks=filtered_chunks,
            top_k=dto.top_k,
        )

        # 6b. If reranking discarded all chunks (no lexical match), abstain
        if not final_chunks:
            logger.info("Abstaining: all chunks discarded by lexical filter")
            return RAGResponseDTO(
                answer=ABSTENTION_ANSWER,
                sources=[],
                query=dto.query,
                abstained=True,
            )

        # 7. Assemble context from retrieved chunks
        context = self._context_assembly_service.assemble(final_chunks)

        # 8. Build prompts
        user_prompt = build_user_prompt(dto.query, context)

        logger.info(
            "Context assembled: %d final chunks, %d context chars, %d prompt chars",
            len(final_chunks), len(context), len(user_prompt),
        )

        # 9. Generate answer via LLM
        answer = await self._llm_port.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            context_chunks=final_chunks,
        )

        # 10. Map to response DTO
        sources = [
            SourceDTO(
                title=chunk.title,
                url=chunk.url,
                score=chunk.score,
                heritage_type=chunk.heritage_type,
                province=chunk.province,
                municipality=chunk.municipality,
                document_id=chunk.document_id,
                content=chunk.content,
                metadata=chunk.metadata,
            )
            for chunk in final_chunks
        ]

        logger.info(
            "RAG pipeline complete: %d chars answer, %d sources",
            len(answer), len(sources),
        )
        logger.debug("RAG LLM answer:\n%s", answer)

        return RAGResponseDTO(
            answer=answer,
            sources=sources,
            query=dto.query,
        )
