"""Integration tests for search API endpoints."""

import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.v1.endpoints.auth.deps import get_current_user
from src.api.v1.endpoints.search.deps import get_search_service
from src.application.search.dto.search_dto import (
    ChunkHitDTO,
    DetectedEntityDTO,
    FilterValuesDTO,
    SearchResultDTO,
    SimilaritySearchResponseDTO,
    SuggestionResponseDTO,
)
from src.domain.auth.entities.user import User, UserProfileType
from src.main import app

_FAKE_USER = User(
    id=uuid.uuid4(),
    username="testuser",
    password_hash="hashed",
    profile_type=UserProfileType(id=uuid.uuid4(), name="investigador"),
)


def _search_response_dto() -> SimilaritySearchResponseDTO:
    return SimilaritySearchResponseDTO(
        results=[
            SearchResultDTO(
                document_id="doc-1",
                title="Catedral de Jaen",
                heritage_type="patrimonio_inmueble",
                province="Jaen",
                municipality="Jaen",
                url="https://example.com/doc-1",
                best_score=0.95,
                chunks=[
                    ChunkHitDTO(
                        chunk_id="chunk-1",
                        content="A chunk of text",
                        score=0.95,
                    )
                ],
            )
        ],
        query="catedral",
        total_results=1,
        page=1,
        page_size=10,
        total_pages=1,
        search_id="search-123",
    )


def _suggestion_response_dto() -> SuggestionResponseDTO:
    return SuggestionResponseDTO(
        query="catedral de jaen",
        search_label="Catedral de Jaen",
        detected_entities=[
            DetectedEntityDTO(
                entity_type="heritage",
                value="catedral",
                display_label="Catedral",
                matched_text="catedral",
            )
        ],
    )


def _filter_values_dto() -> FilterValuesDTO:
    return FilterValuesDTO(
        heritage_types=["patrimonio_inmueble", "patrimonio_mueble"],
        provinces=["Jaen", "Granada"],
        municipalities=["Jaen", "Ubeda"],
    )


@pytest.fixture
def mock_search_service():
    return AsyncMock()


@pytest.fixture
def client(mock_search_service):
    app.dependency_overrides[get_search_service] = lambda: mock_search_service
    app.dependency_overrides[get_current_user] = lambda: _FAKE_USER
    yield AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    )
    app.dependency_overrides.clear()


class TestSearchEndpoints:
    async def test_similarity_search_returns_200(self, client, mock_search_service):
        mock_search_service.similarity_search.return_value = _search_response_dto()
        resp = await client.post(
            "/api/v1/search/similarity",
            json={"query": "catedral"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["query"] == "catedral"
        assert body["total_results"] == 1
        assert len(body["results"]) == 1
        assert body["results"][0]["document_id"] == "doc-1"
        assert body["search_id"] == "search-123"

    async def test_similarity_search_empty_query_returns_422(
        self, client, mock_search_service
    ):
        resp = await client.post(
            "/api/v1/search/similarity",
            json={"query": ""},
        )
        assert resp.status_code == 422

    async def test_similarity_search_missing_body_returns_422(
        self, client, mock_search_service
    ):
        resp = await client.post("/api/v1/search/similarity")
        assert resp.status_code == 422

    async def test_suggestions_returns_200(self, client, mock_search_service):
        mock_search_service.get_suggestions.return_value = _suggestion_response_dto()
        resp = await client.get(
            "/api/v1/search/suggestions", params={"query": "catedral de jaen"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["query"] == "catedral de jaen"
        assert body["search_label"] == "Catedral de Jaen"
        assert len(body["detected_entities"]) == 1

    async def test_filters_returns_200(self, client, mock_search_service):
        mock_search_service.get_filter_values.return_value = _filter_values_dto()
        resp = await client.get("/api/v1/search/filters")
        assert resp.status_code == 200
        body = resp.json()
        assert "heritage_types" in body
        assert "provinces" in body
        assert "municipalities" in body
        assert len(body["heritage_types"]) == 2

    async def test_filters_with_province_param_returns_200(
        self, client, mock_search_service
    ):
        mock_search_service.get_filter_values.return_value = _filter_values_dto()
        resp = await client.get(
            "/api/v1/search/filters", params={"province": "Jaen"}
        )
        assert resp.status_code == 200
