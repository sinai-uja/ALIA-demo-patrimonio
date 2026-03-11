"""Health endpoint tests."""

from httpx import ASGITransport, AsyncClient

from src.main import app


async def test_health_returns_200():
    """GET /health returns 200 with status ok."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


async def test_health_includes_service_name():
    """GET /health response contains the project name."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/health")

    body = resp.json()
    assert "service" in body
    assert isinstance(body["service"], str)
    assert len(body["service"]) > 0
