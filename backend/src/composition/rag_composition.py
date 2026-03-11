from sqlalchemy.ext.asyncio import AsyncSession

from src.application.rag.services.rag_application_service import RAGApplicationService
from src.application.rag.use_cases.rag_query_use_case import RAGQueryUseCase
from src.domain.rag.services.context_assembly_service import ContextAssemblyService
from src.infrastructure.rag.adapters.embedding_adapter import HttpEmbeddingAdapter
from src.infrastructure.rag.adapters.llm_adapter import VLLMAdapter
from src.infrastructure.rag.adapters.vector_search_adapter import PgVectorSearchAdapter


def build_rag_application_service(db: AsyncSession) -> RAGApplicationService:
    """Wire all RAG adapters and return the application service."""
    embedding_adapter = HttpEmbeddingAdapter()
    vector_search_adapter = PgVectorSearchAdapter(db)
    llm_adapter = VLLMAdapter()
    context_assembly_service = ContextAssemblyService()

    use_case = RAGQueryUseCase(
        embedding_port=embedding_adapter,
        vector_search_port=vector_search_adapter,
        llm_port=llm_adapter,
        context_assembly_service=context_assembly_service,
    )

    return RAGApplicationService(rag_query_use_case=use_case)
