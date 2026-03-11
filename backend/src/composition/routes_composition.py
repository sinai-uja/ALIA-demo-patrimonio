from sqlalchemy.ext.asyncio import AsyncSession

from src.application.routes.services.routes_application_service import (
    RoutesApplicationService,
)
from src.application.routes.use_cases.generate_route import GenerateRouteUseCase
from src.application.routes.use_cases.get_route import GetRouteUseCase
from src.application.routes.use_cases.guide_query import GuideQueryUseCase
from src.application.routes.use_cases.list_routes import ListRoutesUseCase
from src.composition.rag_composition import build_rag_application_service
from src.domain.routes.services.route_builder_service import RouteBuilderService
from src.infrastructure.routes.adapters.llm_adapter import VLLMRoutesAdapter
from src.infrastructure.routes.adapters.rag_adapter import InProcessRAGAdapter
from src.infrastructure.routes.repositories.route_repository import (
    SqlAlchemyRouteRepository,
)


def build_routes_application_service(db: AsyncSession) -> RoutesApplicationService:
    """Wire all routes adapters and return the application service."""
    # Infrastructure adapters
    rag_service = build_rag_application_service(db)
    rag_adapter = InProcessRAGAdapter(rag_service)
    llm_adapter = VLLMRoutesAdapter()
    route_repository = SqlAlchemyRouteRepository(db)

    # Domain services
    route_builder_service = RouteBuilderService()

    # Use cases
    generate_route_use_case = GenerateRouteUseCase(
        rag_port=rag_adapter,
        llm_port=llm_adapter,
        route_repository=route_repository,
        route_builder_service=route_builder_service,
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

    return RoutesApplicationService(
        generate_route_use_case=generate_route_use_case,
        guide_query_use_case=guide_query_use_case,
        list_routes_use_case=list_routes_use_case,
        get_route_use_case=get_route_use_case,
    )
