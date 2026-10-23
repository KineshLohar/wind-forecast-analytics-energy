import asyncio
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.api.routes.analysis import get_analysis_service
from app.main import app
from app.services.analysis_service import AnalysisService


class FakeElexonClient:
    def __init__(self):
        self.forecast_requests = 0
        self.actual_requests = 0

    async def fetch_wind_forecasts(self, publish_from, publish_to):
        self.forecast_requests += 1
        return [
            {
                "startTime": "2026-01-01T00:00:00Z",
                "publishTime": "2025-12-30T23:00:00Z",
                "generation": 90,
            },
            {
                "startTime": "2026-01-01T00:00:00Z",
                "publishTime": "2025-12-31T00:00:00Z",
                "generation": 110,
            },
        ]

    async def fetch_wind_actuals(self, start_date, end_date):
        self.actual_requests += 1
        return [
            {"fuelType": "WIND", "startTime": "2026-01-01T00:00:00Z", "generation": 100},
            {"fuelType": "WIND", "startTime": "2026-01-01T00:30:00Z", "generation": 120},
        ]

    async def aclose(self):
        return None


def build_service(client):
    return AnalysisService(client_factory=lambda: client, cache_ttl_seconds=300)


def test_analysis_service_runs_full_pipeline_and_caches_result():
    client = FakeElexonClient()
    service = build_service(client)

    first = asyncio.run(service.analyze(date(2026, 1, 1), date(2026, 1, 1), "24h"))
    second = asyncio.run(service.analyze(date(2026, 1, 1), date(2026, 1, 1), "24h"))

    assert first == second
    assert client.forecast_requests == 1
    assert client.actual_requests == 1
    assert first.analysis.metrics.expected_intervals == 24
    assert first.analysis.metrics.matched_intervals == 1
    assert first.analysis.metrics.coverage_percent == pytest.approx(100 / 24)
    assert first.analysis.observations[0].forecast_mw == 110
    assert first.analysis.observations[0].actual_mw == 110
    assert first.data_quality.incomplete_actual_hours == 0


def test_analysis_service_restricts_scope_to_january_2026():
    with pytest.raises(ValueError, match="January 2026"):
        asyncio.run(build_service(FakeElexonClient()).analyze(date(2026, 2, 1), date(2026, 2, 1)))


def test_analysis_route_returns_chart_ready_response():
    client = FakeElexonClient()
    app.dependency_overrides[get_analysis_service] = lambda: build_service(client)
    try:
        response = TestClient(app).get(
            "/api/analysis?start_date=2026-01-01&end_date=2026-01-01&cutoff=24h"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["cutoff"] == "24h"
    assert body["metrics"]["matched_intervals"] == 1
    assert body["metrics"]["expected_intervals"] == 24
    assert body["observations"][0]["actual_mw"] == 110


def test_analysis_route_rejects_unsupported_month_without_fetching_data():
    client = FakeElexonClient()
    app.dependency_overrides[get_analysis_service] = lambda: build_service(client)
    try:
        response = TestClient(app).get(
            "/api/analysis?start_date=2026-02-01&end_date=2026-02-01"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert "January 2026" in response.json()["detail"]
    assert client.forecast_requests == 0
