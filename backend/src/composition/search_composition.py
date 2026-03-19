from sqlalchemy.ext.asyncio import AsyncSession

from src.application.search.services.search_application_service import (
    SearchApplicationService,
)
from src.application.search.use_cases.filter_values_use_case import (
    FilterValuesUseCase,
)
from src.application.search.use_cases.similarity_search_use_case import (
    SimilaritySearchUseCase,
)
from src.application.search.use_cases.suggestion_use_case import (
    SuggestionUseCase,
)
from src.config import settings
from src.domain.rag.services.hybrid_search_service import HybridSearchService
from src.domain.rag.services.relevance_filter_service import (
    RelevanceFilterService,
)
from src.domain.rag.services.reranking_service import RerankingService
from src.domain.search.services.entity_detection_service import (
    EntityDetectionService,
)
from src.infrastructure.rag.adapters.embedding_adapter import (
    HttpEmbeddingAdapter,
)
from src.infrastructure.rag.adapters.text_search_adapter import (
    PgTextSearchAdapter,
)
from src.infrastructure.rag.adapters.vector_search_adapter import (
    PgVectorSearchAdapter,
)
from src.infrastructure.search.adapters.filter_metadata_adapter import (
    PgFilterMetadataAdapter,
)
from src.infrastructure.search.adapters.heritage_asset_lookup_adapter import (
    PgHeritageAssetLookupAdapter,
)


def build_search_application_service(
    db: AsyncSession,
) -> SearchApplicationService:
    """Wire all search adapters and return the application service."""
    # Reuse RAG infrastructure adapters
    embedding_adapter = HttpEmbeddingAdapter()
    vector_search_adapter = PgVectorSearchAdapter(db)
    text_search_adapter = PgTextSearchAdapter(db)

    # Reuse RAG domain services
    hybrid_search_service = HybridSearchService()
    relevance_filter_service = RelevanceFilterService(
        score_threshold=settings.search_score_threshold,
    )
    reranking_service = RerankingService(
        weight_base=0.6,
        weight_title=0.2,
        weight_coverage=0.15,
        weight_position=0.05,
    )

    # Search-specific adapters and services
    filter_metadata_adapter = PgFilterMetadataAdapter(db)
    heritage_asset_lookup_adapter = PgHeritageAssetLookupAdapter(db)
    entity_detection_service = EntityDetectionService()

    # Wire use cases
    similarity_use_case = SimilaritySearchUseCase(
        embedding_port=embedding_adapter,
        vector_search_port=vector_search_adapter,
        text_search_port=text_search_adapter,
        hybrid_search_service=hybrid_search_service,
        relevance_filter_service=relevance_filter_service,
        reranking_service=reranking_service,
        heritage_asset_lookup_port=heritage_asset_lookup_adapter,
        retrieval_k=settings.search_retrieval_k,
    )

    suggestion_use_case = SuggestionUseCase(
        filter_metadata_port=filter_metadata_adapter,
        entity_detection_service=entity_detection_service,
    )

    filter_values_use_case = FilterValuesUseCase(
        filter_metadata_port=filter_metadata_adapter,
    )

    return SearchApplicationService(
        similarity_use_case=similarity_use_case,
        suggestion_use_case=suggestion_use_case,
        filter_values_use_case=filter_values_use_case,
    )
