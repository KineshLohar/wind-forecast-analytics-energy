"""Transform raw Elexon records into validated internal observations."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import isfinite
from typing import Any


@dataclass(frozen=True)
class ForecastObservation:
    """A single published hourly forecast, retaining its publication vintage."""

    delivery_time: datetime
    publish_time: datetime
    generation_mw: float


@dataclass(frozen=True)
class ActualObservation:
    """A single half-hourly actual generation observation."""

    delivery_time: datetime
    generation_mw: float


@dataclass(frozen=True)
class HourlyActualObservation:
    """Mean MW across the two complete half-hour settlement intervals in an hour."""

    delivery_time: datetime
    generation_mw: float


@dataclass(frozen=True)
class NormalizationIssue:
    record_index: int
    reason: str


@dataclass
class NormalizationResult:
    records: list[ForecastObservation] | list[ActualObservation]
    issues: list[NormalizationIssue]
    duplicate_records_removed: int


@dataclass
class HourlyActualAggregationResult:
    records: list[HourlyActualObservation]
    incomplete_hours: list[datetime]


class _InvalidRecord(ValueError):
    pass


def normalize_forecasts(raw_records: Iterable[Mapping[str, Any]]) -> NormalizationResult:
    """Validate WINDFOR records and retain every distinct forecast revision."""
    records: list[ForecastObservation] = []
    issues: list[NormalizationIssue] = []
    seen: set[tuple[datetime, datetime, float]] = set()
    duplicates_removed = 0

    for index, raw_record in enumerate(raw_records):
        try:
            record = _as_mapping(raw_record)
            observation = ForecastObservation(
                delivery_time=_parse_timestamp(record.get("startTime"), "startTime"),
                publish_time=_parse_timestamp(record.get("publishTime"), "publishTime"),
                generation_mw=_parse_generation(record.get("generation")),
            )
        except _InvalidRecord as exc:
            issues.append(NormalizationIssue(index, str(exc)))
            continue

        identity = (
            observation.delivery_time,
            observation.publish_time,
            observation.generation_mw,
        )
        if identity in seen:
            duplicates_removed += 1
            continue
        seen.add(identity)
        records.append(observation)

    return NormalizationResult(records, issues, duplicates_removed)


def normalize_actuals(raw_records: Iterable[Mapping[str, Any]]) -> NormalizationResult:
    """Validate FUELHH WIND records and remove only exact duplicate observations."""
    records: list[ActualObservation] = []
    issues: list[NormalizationIssue] = []
    seen: set[tuple[datetime, float]] = set()
    duplicates_removed = 0

    for index, raw_record in enumerate(raw_records):
        try:
            record = _as_mapping(raw_record)
            fuel_type = record.get("fuelType")
            if fuel_type != "WIND":
                raise _InvalidRecord("fuelType must be WIND")
            observation = ActualObservation(
                delivery_time=_parse_timestamp(record.get("startTime"), "startTime"),
                generation_mw=_parse_generation(record.get("generation")),
            )
        except _InvalidRecord as exc:
            issues.append(NormalizationIssue(index, str(exc)))
            continue

        identity = (observation.delivery_time, observation.generation_mw)
        if identity in seen:
            duplicates_removed += 1
            continue
        seen.add(identity)
        records.append(observation)

    return NormalizationResult(records, issues, duplicates_removed)


def aggregate_actuals_to_hourly(
    actuals: Iterable[ActualObservation],
) -> HourlyActualAggregationResult:
    """Convert complete half-hourly actuals to hourly mean MW observations.

    WINDFOR publishes values on the hour, while FUELHH records 30-minute MW
    observations. An hourly actual is therefore the arithmetic mean of the
    observations at ``HH:00`` and ``HH:30``. We do not duplicate forecasts to
    manufacture additional matches, and incomplete or conflicting hours are
    withheld from later accuracy calculations.
    """
    buckets: dict[datetime, dict[datetime, list[ActualObservation]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for actual in actuals:
        timestamp = actual.delivery_time
        if timestamp.minute not in (0, 30) or timestamp.second or timestamp.microsecond:
            hour = timestamp.replace(minute=0, second=0, microsecond=0)
            buckets[hour][timestamp].append(actual)
            continue
        hour = timestamp.replace(minute=0, second=0, microsecond=0)
        buckets[hour][timestamp].append(actual)

    hourly_records: list[HourlyActualObservation] = []
    incomplete_hours: list[datetime] = []
    for hour in sorted(buckets):
        expected_times = (hour, hour + timedelta(minutes=30))
        values = buckets[hour]
        if (
            set(values) != set(expected_times)
            or any(len(values[expected_time]) != 1 for expected_time in expected_times)
        ):
            incomplete_hours.append(hour)
            continue

        hourly_records.append(
            HourlyActualObservation(
                delivery_time=hour,
                generation_mw=(
                    values[expected_times[0]][0].generation_mw
                    + values[expected_times[1]][0].generation_mw
                )
                / 2,
            )
        )

    return HourlyActualAggregationResult(hourly_records, incomplete_hours)


def _as_mapping(raw_record: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(raw_record, Mapping):
        raise _InvalidRecord("record must be an object")
    return raw_record


def _parse_timestamp(value: Any, field_name: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise _InvalidRecord(f"{field_name} must be a non-empty ISO 8601 timestamp")

    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise _InvalidRecord(f"{field_name} is not a valid ISO 8601 timestamp") from exc

    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise _InvalidRecord(f"{field_name} must include a timezone")
    return timestamp.astimezone(timezone.utc)


def _parse_generation(value: Any) -> float:
    if isinstance(value, bool) or value is None:
        raise _InvalidRecord("generation must be a finite number")
    try:
        generation = float(value)
    except (TypeError, ValueError) as exc:
        raise _InvalidRecord("generation must be a finite number") from exc
    if not isfinite(generation):
        raise _InvalidRecord("generation must be a finite number")
    return generation
