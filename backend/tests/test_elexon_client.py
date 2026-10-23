import asyncio
from datetime import date, datetime, timedelta, timezone

import httpx
import pytest

from app.core.config import Settings
from app.services.elexon_client import (
    ElexonClient,
    ElexonRequestError,
    ElexonResponseError,
)


def make_client(handler):
    return ElexonClient(
        settings=Settings(elexon_base_url="https://elexon.example/api/v1"),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )


def test_fetches_wind_actuals_with_wind_filter():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200, json=[{"fuelType": "WIND", "generation": 123}], request=request
        )

    records = asyncio.run(
        make_client(handler).fetch_wind_actuals(date(2026, 1, 1), date(2026, 1, 2))
    )

    assert records == [{"fuelType": "WIND", "generation": 123}]
    assert requests[0].url.path == "/api/v1/datasets/FUELHH/stream"
    assert dict(requests[0].url.params) == {
        "settlementDateFrom": "2026-01-01",
        "settlementDateTo": "2026-01-02",
        "fuelType": "WIND",
        "format": "json",
    }


def test_splits_forecasts_into_seven_day_windows():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=[{"request": len(requests)}], request=request)

    publish_from = datetime(2026, 1, 1, tzinfo=timezone.utc)
    records = asyncio.run(
        make_client(handler).fetch_wind_forecasts(
            publish_from, publish_from + timedelta(days=15)
        )
    )

    assert records == [{"request": 1}, {"request": 2}, {"request": 3}]
    assert [request.url.params["publishDateTimeFrom"] for request in requests] == [
        "2026-01-01T00:00:00Z",
        "2026-01-08T00:00:00Z",
        "2026-01-15T00:00:00Z",
    ]
    assert [request.url.params["publishDateTimeTo"] for request in requests] == [
        "2026-01-08T00:00:00Z",
        "2026-01-15T00:00:00Z",
        "2026-01-16T00:00:00Z",
    ]


def test_returns_empty_responses_unchanged():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[], request=request)

    records = asyncio.run(
        make_client(handler).fetch_wind_actuals(date(2026, 1, 1), date(2026, 1, 1))
    )
    assert records == []


@pytest.mark.parametrize("status_code", [429, 500])
def test_raises_domain_error_for_http_failures(status_code):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, request=request)

    with pytest.raises(ElexonRequestError, match="FUELHH"):
        asyncio.run(
            make_client(handler).fetch_wind_actuals(date(2026, 1, 1), date(2026, 1, 1))
        )


def test_raises_domain_error_for_timeout():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    with pytest.raises(ElexonRequestError, match="FUELHH"):
        asyncio.run(
            make_client(handler).fetch_wind_actuals(date(2026, 1, 1), date(2026, 1, 1))
        )


def test_rejects_malformed_response_shape():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"records": []}, request=request)

    with pytest.raises(ElexonResponseError, match="unexpected payload"):
        asyncio.run(
            make_client(handler).fetch_wind_actuals(date(2026, 1, 1), date(2026, 1, 1))
        )


def test_rejects_naive_or_reversed_forecast_ranges():
    client = make_client(lambda request: httpx.Response(200, json=[], request=request))
    aware = datetime(2026, 1, 1, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="timezone-aware"):
        asyncio.run(client.fetch_wind_forecasts(datetime(2026, 1, 1), aware))
    with pytest.raises(ValueError, match="before"):
        asyncio.run(client.fetch_wind_forecasts(aware, aware))
