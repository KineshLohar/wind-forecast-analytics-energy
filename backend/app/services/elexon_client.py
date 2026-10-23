"""Small, testable client for the Elexon BMRS datasets used by the app."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx

from app.core.config import Settings, get_settings


class ElexonClientError(Exception):
    """Base exception for an unsuccessful Elexon data request."""


class ElexonRequestError(ElexonClientError):
    """Raised when Elexon cannot be reached or returns an unsuccessful status."""


class ElexonResponseError(ElexonClientError):
    """Raised when Elexon returns a response that is not the expected JSON list."""


class ElexonClient:
    """Retrieve raw WINDFOR and FUELHH records.

    The client deliberately returns source records without changing their shape.
    Timestamp parsing, de-duplication and interval alignment belong in the
    normalization layer that follows this ingestion step.
    """

    forecast_max_window = timedelta(days=7)

    def __init__(
        self,
        settings: Settings | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        settings = settings or get_settings()
        self._base_url = settings.elexon_base_url.rstrip("/")
        self._client = client or httpx.AsyncClient(
            timeout=settings.request_timeout_seconds,
            headers={"Accept": "application/json"},
        )
        self._owns_client = client is None

    async def __aenter__(self) -> "ElexonClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def fetch_wind_forecasts(
        self,
        publish_from: datetime,
        publish_to: datetime,
    ) -> list[dict[str, Any]]:
        """Fetch WINDFOR publications in seven-day-or-smaller windows.

        Elexon limits the publication timestamp window to seven days. Both
        inputs must be timezone-aware, and ``publish_to`` is exclusive.
        """
        self._validate_datetime_range(publish_from, publish_to)

        records: list[dict[str, Any]] = []
        window_start = publish_from
        while window_start < publish_to:
            window_end = min(window_start + self.forecast_max_window, publish_to)
            records.extend(
                await self._get_records(
                    "WINDFOR",
                    {
                        "publishDateTimeFrom": self._format_datetime(window_start),
                        "publishDateTimeTo": self._format_datetime(window_end),
                    },
                )
            )
            window_start = window_end
        return records

    async def fetch_wind_actuals(
        self,
        delivery_date_from: date,
        delivery_date_to: date,
    ) -> list[dict[str, Any]]:
        """Fetch half-hourly WIND generation records from FUELHH."""
        if delivery_date_from > delivery_date_to:
            raise ValueError("delivery_date_from must not be after delivery_date_to")
        return await self._get_records(
            "FUELHH",
            {
                "settlementDateFrom": delivery_date_from.isoformat(),
                "settlementDateTo": delivery_date_to.isoformat(),
                "fuelType": "WIND",
            },
        )

    async def _get_records(
        self,
        dataset: str,
        params: Mapping[str, str],
    ) -> list[dict[str, Any]]:
        try:
            response = await self._client.get(
                f"{self._base_url}/datasets/{dataset}/stream",
                params={**params, "format": "json"},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ElexonRequestError(
                f"Elexon request for {dataset} failed: {exc}"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise ElexonResponseError(
                f"Elexon returned invalid JSON for {dataset}"
            ) from exc

        if not isinstance(payload, list) or not all(
            isinstance(record, dict) for record in payload
        ):
            raise ElexonResponseError(
                f"Elexon returned an unexpected payload for {dataset}"
            )
        return payload

    @staticmethod
    def _validate_datetime_range(start: datetime, end: datetime) -> None:
        if start.tzinfo is None or start.utcoffset() is None:
            raise ValueError("publish_from must be timezone-aware")
        if end.tzinfo is None or end.utcoffset() is None:
            raise ValueError("publish_to must be timezone-aware")
        if start >= end:
            raise ValueError("publish_from must be before publish_to")

    @staticmethod
    def _format_datetime(value: datetime) -> str:
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
