from src.application.search.dto.search_dto import (
    FilterValuesDTO,
    SimilaritySearchDTO,
    SimilaritySearchResponseDTO,
    SuggestionResponseDTO,
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


class SearchApplicationService:
    """Facade that exposes search operations to the API layer."""

    def __init__(
        self,
        similarity_use_case: SimilaritySearchUseCase,
        suggestion_use_case: SuggestionUseCase,
        filter_values_use_case: FilterValuesUseCase,
    ) -> None:
        self._similarity_use_case = similarity_use_case
        self._suggestion_use_case = suggestion_use_case
        self._filter_values_use_case = filter_values_use_case

    async def similarity_search(
        self, dto: SimilaritySearchDTO,
    ) -> SimilaritySearchResponseDTO:
        return await self._similarity_use_case.execute(dto)

    async def get_suggestions(
        self, query: str,
    ) -> SuggestionResponseDTO:
        return await self._suggestion_use_case.execute(query)

    async def get_filter_values(
        self, provinces: list[str] | None = None,
    ) -> FilterValuesDTO:
        return await self._filter_values_use_case.execute(provinces)
