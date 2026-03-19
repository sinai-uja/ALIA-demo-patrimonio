from sqlalchemy.ext.asyncio import AsyncSession

from src.application.routes.services.routes_application_service import (
    RoutesApplicationService,
)
from src.application.routes.use_cases.generate_route import (
    GenerateRouteUseCase,
)
from src.application.routes.use_cases.get_route import GetRouteUseCase
from src.application.routes.use_cases.guide_query import GuideQueryUseCase
from src.application.routes.use_cases.list_routes import ListRoutesUseCase
from src.application.routes.use_cases.route_filter_values import (
    RouteFilterValuesUseCase,
)
from src.application.routes.use_cases.route_suggestions import (
    RouteSuggestionsUseCase,
)
from src.composition.rag_composition import (
    build_rag_application_service,
)
from src.composition.search_composition import (
    build_search_application_service,
)
from src.config import settings
from src.domain.routes.services.query_extraction_service import (
    QueryExtractionService,
)
from src.domain.routes.services.route_builder_service import (
    RouteBuilderService,
)
from src.infrastructure.routes.adapters.entity_detection_adapter import (
    InProcessEntityDetectionAdapter,
)
from src.infrastructure.routes.adapters.gemini_llm_adapter import (
    GeminiRoutesAdapter,
)
from src.infrastructure.routes.adapters.llm_adapter import (
    VLLMRoutesAdapter,
)
from src.infrastructure.routes.adapters.rag_adapter import (
    InProcessRAGAdapter,
)
from src.infrastructure.routes.repositories.route_repository import (
    SqlAlchemyRouteRepository,
)
from src.infrastructure.search.adapters.filter_metadata_adapter import (
    PgFilterMetadataAdapter,
)


def build_routes_application_service(
    db: AsyncSession,
) -> RoutesApplicationService:
    """Wire all routes adapters and return the application service."""
    # Infrastructure adapters
    rag_service = build_rag_application_service(db)
    rag_adapter = InProcessRAGAdapter(rag_service)
    llm_adapter = (
        GeminiRoutesAdapter() if settings.llm_provider == "gemini"
        else VLLMRoutesAdapter()
    )
    route_repository = SqlAlchemyRouteRepository(db)

    # Cross-context adapters
    search_service = build_search_application_service(db)
    entity_detection_adapter = InProcessEntityDetectionAdapter(
        search_service,
    )
    filter_metadata_adapter = PgFilterMetadataAdapter(db)

    # Domain services
    route_builder_service = RouteBuilderService()
    query_extraction_service = QueryExtractionService()

    # Use cases
    generate_route_use_case = GenerateRouteUseCase(
        rag_port=rag_adapter,
        llm_port=llm_adapter,
        route_repository=route_repository,
        route_builder_service=route_builder_service,
        query_extraction_service=query_extraction_service,
    )
    guide_query_use_case = GuideQueryUseCase(
        rag_port=rag_adapter,
        llm_port=llm_adapter,
        route_repository=route_repository,
    )
    list_routes_use_case = ListRoutesUseCase(
        route_repository=route_repository,
    )
    get_route_use_case = GetRouteUseCase(
        route_repository=route_repository,
    )
    route_suggestions_use_case = RouteSuggestionsUseCase(
        entity_detection_port=entity_detection_adapter,
    )
    route_filter_values_use_case = RouteFilterValuesUseCase(
        filter_metadata_port=filter_metadata_adapter,
    )

    return RoutesApplicationService(
        generate_route_use_case=generate_route_use_case,
        guide_query_use_case=guide_query_use_case,
        list_routes_use_case=list_routes_use_case,
        get_route_use_case=get_route_use_case,
        route_suggestions_use_case=route_suggestions_use_case,
        route_filter_values_use_case=route_filter_values_use_case,
    )
