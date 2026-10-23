from datetime import datetime, timezone

from app.services.normalization import (
    ActualObservation,
    aggregate_actuals_to_hourly,
    normalize_actuals,
    normalize_forecasts,
)


def test_normalize_forecasts_converts_timestamps_to_utc_and_preserves_revisions():
    result = normalize_forecasts(
        [
            {
                "startTime": "2026-01-01T01:00:00+01:00",
                "publishTime": "2025-12-31T23:00:00Z",
                "generation": "12000",
            },
            {
                "startTime": "2026-01-01T00:00:00Z",
                "publishTime": "2025-12-31T23:30:00Z",
                "generation": 12100,
            },
        ]
    )

    assert len(result.records) == 2
    assert result.records[0].delivery_time == datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert result.records[0].generation_mw == 12000.0
    assert result.records[1].publish_time > result.records[0].publish_time


def test_normalize_forecasts_removes_only_exact_duplicates():
    raw_record = {
        "startTime": "2026-01-01T00:00:00Z",
        "publishTime": "2025-12-31T12:00:00Z",
        "generation": 100,
    }
    revised_record = {**raw_record, "generation": 110}

    result = normalize_forecasts([raw_record, raw_record, revised_record])

    assert [record.generation_mw for record in result.records] == [100.0, 110.0]
    assert result.duplicate_records_removed == 1
    assert result.issues == []


def test_normalize_records_reports_malformed_and_missing_values():
    result = normalize_forecasts(
        [
            {"startTime": "2026-01-01T00:00:00", "publishTime": "2025-12-31T12:00:00Z", "generation": 1},
            {"startTime": "2026-01-01T00:00:00Z", "publishTime": "bad", "generation": 1},
            {"startTime": "2026-01-01T00:00:00Z", "publishTime": "2025-12-31T12:00:00Z", "generation": None},
        ]
    )

    assert result.records == []
    assert result.duplicate_records_removed == 0
    assert len(result.issues) == 3
    assert "timezone" in result.issues[0].reason
    assert "valid ISO" in result.issues[1].reason
    assert "finite number" in result.issues[2].reason


def test_normalize_actuals_requires_wind_and_removes_exact_duplicates():
    wind = {"fuelType": "WIND", "startTime": "2026-01-01T00:00:00Z", "generation": 100}
    result = normalize_actuals([wind, wind, {**wind, "fuelType": "CCGT"}])

    assert len(result.records) == 1
    assert result.duplicate_records_removed == 1
    assert result.issues[0].reason == "fuelType must be WIND"


def test_aggregate_actuals_to_hourly_averages_complete_half_hour_pairs():
    actuals = [
        ActualObservation(datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc), 100.0),
        ActualObservation(datetime(2026, 1, 1, 0, 30, tzinfo=timezone.utc), 140.0),
    ]

    result = aggregate_actuals_to_hourly(actuals)

    assert len(result.records) == 1
    assert result.records[0].delivery_time == datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert result.records[0].generation_mw == 120.0
    assert result.incomplete_hours == []


def test_aggregate_actuals_to_hourly_withholds_missing_half_hour():
    hour = datetime(2026, 1, 1, tzinfo=timezone.utc)
    result = aggregate_actuals_to_hourly([ActualObservation(hour, 100.0)])

    assert result.records == []
    assert result.incomplete_hours == [hour]


def test_aggregate_actuals_to_hourly_withholds_conflicting_duplicate_interval():
    hour = datetime(2026, 1, 1, tzinfo=timezone.utc)
    result = aggregate_actuals_to_hourly(
        [
            ActualObservation(hour, 100.0),
            ActualObservation(hour, 101.0),
            ActualObservation(hour.replace(minute=30), 120.0),
        ]
    )

    assert result.records == []
    assert result.incomplete_hours == [hour]
