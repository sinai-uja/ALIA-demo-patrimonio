from sqlalchemy.ext.asyncio import AsyncSession

from src.application.rag.services.rag_application_service import RAGApplicationService
from src.application.rag.use_cases.rag_query_use_case import RAGQueryUseCase
from src.composition.token_provider_composition import build_token_provider
from src.config import settings
from src.domain.rag.services.context_assembly_service import ContextAssemblyService
from src.domain.rag.services.hybrid_search_service import HybridSearchService
from src.domain.rag.services.neural_reranking_service import NeuralRerankingService
from src.domain.rag.services.relevance_filter_service import RelevanceFilterService
from src.domain.rag.services.reranking_service import RerankingService
from src.infrastructure.rag.adapters.embedding_adapter import HttpEmbeddingAdapter
from src.infrastructure.rag.adapters.gemini_llm_adapter import GeminiRAGAdapter
from src.infrastructure.rag.adapters.llm_adapter import VLLMAdapter
from src.infrastructure.rag.adapters.reranker_adapter import HttpRerankerAdapter
from src.infrastructure.rag.adapters.text_search_adapter import PgTextSearchAdapter
from src.infrastructure.rag.adapters.vector_search_adapter import PgVectorSearchAdapter

# Module-level singletons — these adapters don't depend on the DB session
_embedding_adapter = HttpEmbeddingAdapter(
    token_provider=build_token_provider(settings.embedding_service_url),
)
_llm_adapter = (
    GeminiRAGAdapter() if settings.llm_provider == "gemini"
    else VLLMAdapter(
        token_provider=build_token_provider(settings.llm_service_url),
    )
)
_context_assembly_service = ContextAssemblyService()
_hybrid_search_service = HybridSearchService()

if settings.reranker_enabled:
    _reranker_adapter = HttpRerankerAdapter(
        token_provider=build_token_provider(settings.reranker_service_url),
    )
    _reranking_service = NeuralRerankingService(
        reranker_port=_reranker_adapter,
        instruction=settings.reranker_instruction,
        top_n=settings.reranker_top_n,
    )
else:
    _reranking_service = RerankingService()


def build_rag_application_service(db: AsyncSession) -> RAGApplicationService:
    """Wire all RAG adapters and return the application service."""
    # Per-request (need DB session)
    vector_search_adapter = PgVectorSearchAdapter(db)
    text_search_adapter = PgTextSearchAdapter(db)
    relevance_filter_service = RelevanceFilterService(
        score_threshold=settings.rag_score_threshold,
    )

    use_case = RAGQueryUseCase(
        embedding_port=_embedding_adapter,
        vector_search_port=vector_search_adapter,
        text_search_port=text_search_adapter,
        llm_port=_llm_adapter,
        context_assembly_service=_context_assembly_service,
        relevance_filter_service=relevance_filter_service,
        hybrid_search_service=_hybrid_search_service,
        reranking_service=_reranking_service,
        retrieval_k=settings.rag_retrieval_k,
        similarity_only=settings.rag_similarity_only,
        similarity_threshold=settings.rag_similarity_threshold,
        reranker_enabled=settings.reranker_enabled,
    )

    return RAGApplicationService(rag_query_use_case=use_case)
