"""Forecast-vintage selection and deterministic accuracy calculations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import sqrt
from typing import Iterable

from app.services.normalization import ForecastObservation, HourlyActualObservation


@dataclass(frozen=True)
class SelectedForecast:
    """The newest forecast that was available for one delivery hour."""

    delivery_time: datetime
    publish_time: datetime
    generation_mw: float


@dataclass(frozen=True)
class MatchedObservation:
    delivery_time: datetime
    forecast_publish_time: datetime
    forecast_mw: float
    actual_mw: float
    error_mw: float


@dataclass(frozen=True)
class AccuracyMetrics:
    mae_mw: float | None
    rmse_mw: float | None
    mbe_mw: float | None
    wape_percent: float | None
    coverage_percent: float | None
    expected_intervals: int
    matched_intervals: int
    missing_forecast_intervals: int
    missing_actual_intervals: int


@dataclass(frozen=True)
class AccuracyAnalysis:
    metrics: AccuracyMetrics
    observations: list[MatchedObservation]


def select_forecast_vintages(
    forecasts: Iterable[ForecastObservation],
    lead_time: timedelta | None,
) -> list[SelectedForecast]:
    """Choose the latest forecast available by each delivery interval's cutoff.

    ``lead_time=timedelta(hours=24)`` models a day-ahead decision: a forecast
    published after ``delivery_time - 24h`` is ineligible. Passing ``None``
    selects the latest forecast that existed before delivery, which is useful
    as a non-decision benchmark but should not be used as the day-ahead view.
    """
    if lead_time is not None and lead_time < timedelta(0):
        raise ValueError("lead_time must be zero or positive")

    eligible_by_delivery: dict[datetime, ForecastObservation] = {}
    for forecast in forecasts:
        cutoff = forecast.delivery_time - (lead_time or timedelta(0))
        if forecast.publish_time > cutoff:
            continue

        selected = eligible_by_delivery.get(forecast.delivery_time)
        if selected is None or forecast.publish_time > selected.publish_time:
            eligible_by_delivery[forecast.delivery_time] = forecast

    return [
        SelectedForecast(
            delivery_time=delivery_time,
            publish_time=forecast.publish_time,
            generation_mw=forecast.generation_mw,
        )
        for delivery_time, forecast in sorted(eligible_by_delivery.items())
    ]


def calculate_accuracy(
    forecasts: Iterable[SelectedForecast],
    actuals: Iterable[HourlyActualObservation],
    expected_delivery_times: Iterable[datetime] | None = None,
) -> AccuracyAnalysis:
    """Calculate MW forecast errors without treating missing values as zero.

    Coverage is the share of expected delivery intervals with both a selected
    forecast and an actual. If the caller does not provide expected intervals,
    the union of supplied forecast and actual timestamps is used.
    """
    forecast_by_delivery = _index_by_delivery(forecasts, "forecast")
    actual_by_delivery = _index_by_delivery(actuals, "actual")

    if expected_delivery_times is None:
        expected = set(forecast_by_delivery) | set(actual_by_delivery)
    else:
        expected = set(expected_delivery_times)

    matched_times = sorted(
        expected & set(forecast_by_delivery) & set(actual_by_delivery)
    )
    observations = [
        MatchedObservation(
            delivery_time=delivery_time,
            forecast_publish_time=forecast_by_delivery[delivery_time].publish_time,
            forecast_mw=forecast_by_delivery[delivery_time].generation_mw,
            actual_mw=actual_by_delivery[delivery_time].generation_mw,
            error_mw=(
                forecast_by_delivery[delivery_time].generation_mw
                - actual_by_delivery[delivery_time].generation_mw
            ),
        )
        for delivery_time in matched_times
    ]

    errors = [observation.error_mw for observation in observations]
    total_actual = sum(observation.actual_mw for observation in observations)
    absolute_error = sum(abs(error) for error in errors)
    matched_count = len(observations)
    expected_count = len(expected)

    metrics = AccuracyMetrics(
        mae_mw=(absolute_error / matched_count) if matched_count else None,
        rmse_mw=(sqrt(sum(error**2 for error in errors) / matched_count))
        if matched_count
        else None,
        mbe_mw=(sum(errors) / matched_count) if matched_count else None,
        wape_percent=(absolute_error / total_actual * 100)
        if matched_count and total_actual != 0
        else None,
        coverage_percent=(matched_count / expected_count * 100) if expected_count else None,
        expected_intervals=expected_count,
        matched_intervals=matched_count,
        missing_forecast_intervals=len(expected - set(forecast_by_delivery)),
        missing_actual_intervals=len(expected - set(actual_by_delivery)),
    )
    return AccuracyAnalysis(metrics=metrics, observations=observations)


def _index_by_delivery(
    observations: Iterable[SelectedForecast] | Iterable[HourlyActualObservation],
    source_name: str,
) -> dict[datetime, SelectedForecast | HourlyActualObservation]:
    indexed: dict[datetime, SelectedForecast | HourlyActualObservation] = {}
    for observation in observations:
        if observation.delivery_time in indexed:
            raise ValueError(f"duplicate {source_name} delivery interval")
        indexed[observation.delivery_time] = observation
    return indexed
