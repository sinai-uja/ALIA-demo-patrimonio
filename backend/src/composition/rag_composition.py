from sqlalchemy.ext.asyncio import AsyncSession

from src.application.rag.services.rag_application_service import RAGApplicationService
from src.application.rag.use_cases.rag_query_use_case import RAGQueryUseCase
from src.config import settings
from src.domain.rag.services.context_assembly_service import ContextAssemblyService
from src.domain.rag.services.hybrid_search_service import HybridSearchService
from src.domain.rag.services.relevance_filter_service import RelevanceFilterService
from src.domain.rag.services.reranking_service import RerankingService
from src.infrastructure.rag.adapters.embedding_adapter import HttpEmbeddingAdapter
from src.infrastructure.rag.adapters.llm_adapter import VLLMAdapter
from src.infrastructure.rag.adapters.text_search_adapter import PgTextSearchAdapter
from src.infrastructure.rag.adapters.vector_search_adapter import PgVectorSearchAdapter


def build_rag_application_service(db: AsyncSession) -> RAGApplicationService:
    """Wire all RAG adapters and return the application service."""
    embedding_adapter = HttpEmbeddingAdapter()
    vector_search_adapter = PgVectorSearchAdapter(db)
    text_search_adapter = PgTextSearchAdapter(db)
    llm_adapter = VLLMAdapter()
    context_assembly_service = ContextAssemblyService()
    relevance_filter_service = RelevanceFilterService(
        score_threshold=settings.rag_score_threshold,
    )
    hybrid_search_service = HybridSearchService()
    reranking_service = RerankingService()

    use_case = RAGQueryUseCase(
        embedding_port=embedding_adapter,
        vector_search_port=vector_search_adapter,
        text_search_port=text_search_adapter,
        llm_port=llm_adapter,
        context_assembly_service=context_assembly_service,
        relevance_filter_service=relevance_filter_service,
        hybrid_search_service=hybrid_search_service,
        reranking_service=reranking_service,
        retrieval_k=settings.rag_retrieval_k,
    )

    return RAGApplicationService(rag_query_use_case=use_case)
