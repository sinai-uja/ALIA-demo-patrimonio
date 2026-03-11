from src.application.rag.dto.rag_dto import RAGQueryDTO, RAGResponseDTO, SourceDTO
from src.domain.rag.ports.embedding_port import EmbeddingPort
from src.domain.rag.ports.llm_port import LLMPort
from src.domain.rag.ports.vector_search_port import VectorSearchPort
from src.domain.rag.prompts import SYSTEM_PROMPT, build_user_prompt
from src.domain.rag.services.context_assembly_service import ContextAssemblyService


class RAGQueryUseCase:
    """Orchestrates the full RAG pipeline: embed -> search -> assemble -> generate."""

    def __init__(
        self,
        embedding_port: EmbeddingPort,
        vector_search_port: VectorSearchPort,
        llm_port: LLMPort,
        context_assembly_service: ContextAssemblyService,
    ) -> None:
        self._embedding_port = embedding_port
        self._vector_search_port = vector_search_port
        self._llm_port = llm_port
        self._context_assembly_service = context_assembly_service

    async def execute(self, dto: RAGQueryDTO) -> RAGResponseDTO:
        # 1. Embed the user query
        embeddings = await self._embedding_port.embed([dto.query])
        query_embedding = embeddings[0]

        # 2. Vector similarity search with optional filters
        chunks = await self._vector_search_port.search(
            query_embedding=query_embedding,
            top_k=dto.top_k,
            heritage_type=dto.heritage_type_filter,
            province=dto.province_filter,
        )

        # 3. Assemble context from retrieved chunks
        context = self._context_assembly_service.assemble(chunks)

        # 4. Build prompts
        user_prompt = build_user_prompt(dto.query, context)

        # 5. Generate answer via LLM
        answer = await self._llm_port.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            context_chunks=chunks,
        )

        # 6. Map to response DTO
        sources = [
            SourceDTO(
                title=chunk.title,
                url=chunk.url,
                score=chunk.score,
                heritage_type=chunk.heritage_type,
                province=chunk.province,
            )
            for chunk in chunks
        ]

        return RAGResponseDTO(
            answer=answer,
            sources=sources,
            query=dto.query,
        )
