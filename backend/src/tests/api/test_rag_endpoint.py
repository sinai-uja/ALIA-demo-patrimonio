"""Integration tests for the RAG query endpoint with mocked application service."""

import uuid
from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient

from src.application.rag.dto.rag_dto import RAGResponseDTO, SourceDTO
from src.domain.auth.entities.user import User, UserProfileType
from src.main import app

_FAKE_USER = User(
    id=uuid.uuid4(),
    username="testuser",
    password_hash="hashed",
    profile_type=UserProfileType(id=uuid.uuid4(), name="investigador"),
)


def _mock_rag_response() -> RAGResponseDTO:
    return RAGResponseDTO(
        answer="Jaen cuenta con un rico patrimonio historico.",
        sources=[
            SourceDTO(
                title="Catedral de Jaen",
                url="https://guiadigital.iaph.es/catedral-jaen",
                score=0.92,
                heritage_type="patrimonio_inmueble",
                province="Jaen",
            ),
        ],
        query="patrimonio de Jaen",
    )


def _install_overrides(mock_service: AsyncMock) -> None:
    from src.api.v1.endpoints.auth.deps import get_current_user
    from src.api.v1.endpoints.rag.deps import get_rag_service

    app.dependency_overrides[get_rag_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = lambda: _FAKE_USER


class TestRAGQueryEndpoint:
    async def test_query_returns_200_with_expected_fields(self):
        mock_service = AsyncMock()
        mock_service.query.return_value = _mock_rag_response()
        _install_overrides(mock_service)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/rag/query",
                    json={"query": "patrimonio de Jaen"},
                )
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 200
        body = resp.json()
        assert "answer" in body
        assert "sources" in body
        assert "query" in body
        assert body["query"] == "patrimonio de Jaen"
        assert body["answer"] == "Jaen cuenta con un rico patrimonio historico."

    async def test_query_sources_contain_expected_fields(self):
        mock_service = AsyncMock()
        mock_service.query.return_value = _mock_rag_response()
        _install_overrides(mock_service)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/rag/query",
                    json={"query": "patrimonio de Jaen"},
                )
        finally:
            app.dependency_overrides.clear()

        sources = resp.json()["sources"]
        assert len(sources) == 1
        source = sources[0]
        assert source["title"] == "Catedral de Jaen"
        assert source["url"] == "https://guiadigital.iaph.es/catedral-jaen"
        assert source["score"] == 0.92
        assert source["heritage_type"] == "patrimonio_inmueble"
        assert source["province"] == "Jaen"

    async def test_query_with_empty_string_returns_422(self):
        """QueryRequest.query has min_length=1, so empty string is rejected."""
        mock_service = AsyncMock()
        _install_overrides(mock_service)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/rag/query",
                    json={"query": ""},
                )
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 422

    async def test_query_with_missing_body_returns_422(self):
        mock_service = AsyncMock()
        _install_overrides(mock_service)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post("/api/v1/rag/query")
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 422

    async def test_query_with_optional_filters(self):
        mock_service = AsyncMock()
        mock_service.query.return_value = _mock_rag_response()
        _install_overrides(mock_service)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/rag/query",
                    json={
                        "query": "patrimonio de Jaen",
                        "top_k": 3,
                        "heritage_type_filter": "patrimonio_inmueble",
                        "province_filter": "Jaen",
                    },
                )
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 200
