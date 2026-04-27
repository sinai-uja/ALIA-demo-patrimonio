from sqlalchemy.ext.asyncio import AsyncSession

from src.application.routes.services.routes_application_service import (
    RoutesApplicationService,
)
from src.application.routes.use_cases.add_stop import AddStopUseCase
from src.application.routes.use_cases.delete_route import (
    DeleteRouteUseCase,
)
from src.application.routes.use_cases.generate_route import (
    GenerateRouteUseCase,
)
from src.application.routes.use_cases.generate_route_stream import (
    GenerateRouteStreamUseCase,
)
from src.application.routes.use_cases.get_route import GetRouteUseCase
from src.application.routes.use_cases.guide_query import GuideQueryUseCase
from src.application.routes.use_cases.list_routes import ListRoutesUseCase
from src.application.routes.use_cases.remove_stop import RemoveStopUseCase
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
from src.composition.token_provider_composition import build_token_provider
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
from src.infrastructure.routes.adapters.heritage_asset_lookup_adapter import (
    PgHeritageAssetLookupAdapter,
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
from src.infrastructure.shared.adapters.sqlalchemy_unit_of_work import (
    SqlAlchemyUnitOfWork,
)
from src.infrastructure.shared.repositories.trace_repository import (
    SqlAlchemyTraceRepository,
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
        else VLLMRoutesAdapter(
            token_provider=build_token_provider(settings.llm_service_url),
        )
    )
    route_repository = SqlAlchemyRouteRepository(db)
    uow = SqlAlchemyUnitOfWork(session=db)
    heritage_asset_lookup_adapter = PgHeritageAssetLookupAdapter(db)

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
    trace_repository = SqlAlchemyTraceRepository(db)

    generate_route_use_case = GenerateRouteUseCase(
        rag_port=rag_adapter,
        llm_port=llm_adapter,
        route_repository=route_repository,
        route_builder_service=route_builder_service,
        query_extraction_service=query_extraction_service,
        heritage_asset_lookup_port=heritage_asset_lookup_adapter,
        unit_of_work=uow,
        trace_repository=trace_repository,
    )
    guide_query_use_case = GuideQueryUseCase(
        llm_port=llm_adapter,
        route_repository=route_repository,
        heritage_asset_lookup_port=heritage_asset_lookup_adapter,
    )
    list_routes_use_case = ListRoutesUseCase(
        route_repository=route_repository,
    )
    get_route_use_case = GetRouteUseCase(
        route_repository=route_repository,
    )
    delete_route_use_case = DeleteRouteUseCase(
        route_repository=route_repository,
        unit_of_work=uow,
    )
    route_suggestions_use_case = RouteSuggestionsUseCase(
        entity_detection_port=entity_detection_adapter,
    )
    route_filter_values_use_case = RouteFilterValuesUseCase(
        filter_metadata_port=filter_metadata_adapter,
    )
    remove_stop_use_case = RemoveStopUseCase(
        route_repository=route_repository,
        unit_of_work=uow,
        trace_repository=trace_repository,
    )
    add_stop_use_case = AddStopUseCase(
        route_repository=route_repository,
        heritage_asset_lookup_port=heritage_asset_lookup_adapter,
        llm_port=llm_adapter,
        unit_of_work=uow,
        trace_repository=trace_repository,
    )
    generate_route_stream_use_case = GenerateRouteStreamUseCase(
        rag_port=rag_adapter,
        llm_port=llm_adapter,
        route_repository=route_repository,
        route_builder_service=route_builder_service,
        query_extraction_service=query_extraction_service,
        heritage_asset_lookup_port=heritage_asset_lookup_adapter,
        unit_of_work=uow,
        trace_repository=trace_repository,
    )

    return RoutesApplicationService(
        generate_route_use_case=generate_route_use_case,
        guide_query_use_case=guide_query_use_case,
        list_routes_use_case=list_routes_use_case,
        get_route_use_case=get_route_use_case,
        delete_route_use_case=delete_route_use_case,
        route_suggestions_use_case=route_suggestions_use_case,
        route_filter_values_use_case=route_filter_values_use_case,
        remove_stop_use_case=remove_stop_use_case,
        add_stop_use_case=add_stop_use_case,
        generate_route_stream_use_case=generate_route_stream_use_case,
    )


async def run_add_stop_in_background(
    route_id: str,
    document_id: str,
    position: int | None,
    user_id: str,
    username: str | None = None,
    user_profile_type: str | None = None,
) -> None:
    """Run add_stop in a background task with its own DB session.

    Used by the API layer when ``background=true`` to avoid blocking
    the HTTP response while the LLM generates the narrative.
    """
    from src.infrastructure.shared.persistence.engine import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as session:
            service = build_routes_application_service(session)
            await service.add_stop(
                route_id,
                document_id,
                position,
                user_id=user_id,
                username=username,
                user_profile_type=user_profile_type,
            )
    except Exception:
        import logging

        logging.getLogger("iaph.routes.background").warning(
            "Background add_stop failed: route=%s doc=%s",
            route_id,
            document_id,
            exc_info=True,
        )
