"""Orchestrate Elexon ingestion, normalization and forecast-accuracy analysis."""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from time import monotonic

from app.services.analytics import AccuracyAnalysis, calculate_accuracy, select_forecast_vintages
from app.services.elexon_client import ElexonClient
from app.services.normalization import (
    HourlyActualAggregationResult,
    NormalizationResult,
    aggregate_actuals_to_hourly,
    normalize_actuals,
    normalize_forecasts,
)

JANUARY_2026_START = date(2026, 1, 1)
JANUARY_2026_END = date(2026, 1, 31)
FORECAST_LOOKBACK = timedelta(days=2)


@dataclass(frozen=True)
class DataQualitySummary:
    normalized_forecasts: int
    normalized_actuals: int
    rejected_forecasts: int
    rejected_actuals: int
    duplicate_forecasts_removed: int
    duplicate_actuals_removed: int
    incomplete_actual_hours: int


@dataclass(frozen=True)
class AnalysisPayload:
    period_start: datetime
    period_end_exclusive: datetime
    cutoff: str
    analysis: AccuracyAnalysis
    data_quality: DataQualitySummary


@dataclass(frozen=True)
class _CacheEntry:
    expires_at: float
    payload: AnalysisPayload


class AnalysisService:
    """Build and cache historical analyses for the fixed assignment period."""

    def __init__(
        self,
        client_factory: Callable[[], ElexonClient] = ElexonClient,
        cache_ttl_seconds: float = 300,
        max_cache_entries: int = 8,
    ) -> None:
        self._client_factory = client_factory
        self._cache_ttl_seconds = cache_ttl_seconds
        self._max_cache_entries = max_cache_entries
        self._cache: OrderedDict[tuple[date, date, str], _CacheEntry] = OrderedDict()
        self._cache_lock = asyncio.Lock()

    async def analyze(
        self,
        start_date: date,
        end_date: date,
        cutoff: str = "24h",
    ) -> AnalysisPayload:
        self._validate_period(start_date, end_date)
        lead_time = _parse_cutoff(cutoff)
        cache_key = (start_date, end_date, cutoff)
        cached = await self._get_cached(cache_key)
        if cached is not None:
            return cached

        period_start = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
        period_end_exclusive = datetime.combine(
            end_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc
        )
        publish_from = period_start - (lead_time or timedelta(0)) - FORECAST_LOOKBACK
        publish_to = period_end_exclusive - (lead_time or timedelta(0))

        client = self._client_factory()
        try:
            raw_forecasts, raw_actuals = await asyncio.gather(
                client.fetch_wind_forecasts(publish_from, publish_to),
                client.fetch_wind_actuals(start_date, end_date),
            )
        finally:
            await client.aclose()

        normalized_forecasts = normalize_forecasts(raw_forecasts)
        normalized_actuals = normalize_actuals(raw_actuals)
        period_forecasts = [
            forecast
            for forecast in normalized_forecasts.records
            if period_start <= forecast.delivery_time < period_end_exclusive
        ]
        hourly_actuals = aggregate_actuals_to_hourly(normalized_actuals.records)
        period_actuals = [
            actual
            for actual in hourly_actuals.records
            if period_start <= actual.delivery_time < period_end_exclusive
        ]
        selected_forecasts = select_forecast_vintages(period_forecasts, lead_time)
        expected_hours = _expected_hourly_intervals(period_start, period_end_exclusive)
        analysis = calculate_accuracy(selected_forecasts, period_actuals, expected_hours)

        payload = AnalysisPayload(
            period_start=period_start,
            period_end_exclusive=period_end_exclusive,
            cutoff=cutoff,
            analysis=analysis,
            data_quality=DataQualitySummary(
                normalized_forecasts=len(period_forecasts),
                normalized_actuals=len(normalized_actuals.records),
                rejected_forecasts=len(normalized_forecasts.issues),
                rejected_actuals=len(normalized_actuals.issues),
                duplicate_forecasts_removed=normalized_forecasts.duplicate_records_removed,
                duplicate_actuals_removed=normalized_actuals.duplicate_records_removed,
                incomplete_actual_hours=len(hourly_actuals.incomplete_hours),
            ),
        )
        await self._store_cached(cache_key, payload)
        return payload

    def _validate_period(self, start_date: date, end_date: date) -> None:
        if start_date > end_date:
            raise ValueError("start_date must not be after end_date")
        if start_date < JANUARY_2026_START or end_date > JANUARY_2026_END:
            raise ValueError("only dates in January 2026 are supported")

    async def _get_cached(
        self, cache_key: tuple[date, date, str]
    ) -> AnalysisPayload | None:
        async with self._cache_lock:
            entry = self._cache.get(cache_key)
            if entry is None:
                return None
            if entry.expires_at <= monotonic():
                del self._cache[cache_key]
                return None
            self._cache.move_to_end(cache_key)
            return entry.payload

    async def _store_cached(
        self, cache_key: tuple[date, date, str], payload: AnalysisPayload
    ) -> None:
        async with self._cache_lock:
            self._cache[cache_key] = _CacheEntry(
                expires_at=monotonic() + self._cache_ttl_seconds,
                payload=payload,
            )
            self._cache.move_to_end(cache_key)
            while len(self._cache) > self._max_cache_entries:
                self._cache.popitem(last=False)


def _parse_cutoff(cutoff: str) -> timedelta | None:
    options = {
        "24h": timedelta(hours=24),
        "12h": timedelta(hours=12),
        "6h": timedelta(hours=6),
        "latest": None,
    }
    try:
        return options[cutoff]
    except KeyError as exc:
        raise ValueError("cutoff must be one of: 24h, 12h, 6h, latest") from exc


def _expected_hourly_intervals(
    period_start: datetime, period_end_exclusive: datetime
) -> list[datetime]:
    intervals: list[datetime] = []
    current = period_start
    while current < period_end_exclusive:
        intervals.append(current)
        current += timedelta(hours=1)
    return intervals
