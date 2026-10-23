from datetime import datetime, timedelta, timezone

import pytest

from app.services.analytics import calculate_accuracy, select_forecast_vintages
from app.services.normalization import ForecastObservation, HourlyActualObservation


def at(hour: int) -> datetime:
    return datetime(2026, 1, 2, hour, tzinfo=timezone.utc)


def test_selects_newest_forecast_available_at_day_ahead_cutoff():
    forecasts = [
        ForecastObservation(at(18), at(18) - timedelta(hours=30), 18000),
        ForecastObservation(at(18), at(18) - timedelta(hours=25), 18100),
        ForecastObservation(at(18), at(18) - timedelta(hours=23), 18200),
        ForecastObservation(at(18), at(18) - timedelta(hours=6), 18300),
    ]

    selected = select_forecast_vintages(forecasts, timedelta(hours=24))

    assert len(selected) == 1
    assert selected[0].generation_mw == 18100
    assert selected[0].publish_time == at(18) - timedelta(hours=25)


def test_latest_before_delivery_uses_latest_non_future_revision():
    forecasts = [
        ForecastObservation(at(10), at(10) - timedelta(hours=3), 100),
        ForecastObservation(at(10), at(10) - timedelta(minutes=1), 110),
        ForecastObservation(at(10), at(10) + timedelta(minutes=1), 120),
    ]

    selected = select_forecast_vintages(forecasts, None)

    assert [forecast.generation_mw for forecast in selected] == [110]


def test_rejects_negative_cutoff_lead_time():
    with pytest.raises(ValueError, match="zero or positive"):
        select_forecast_vintages([], timedelta(hours=-1))


def test_calculates_all_error_metrics_for_known_values():
    forecasts = [
        _selected_forecast(0, 110),
        _selected_forecast(1, 180),
    ]
    actuals = [
        HourlyActualObservation(at(0), 100),
        HourlyActualObservation(at(1), 200),
    ]

    analysis = calculate_accuracy(forecasts, actuals)

    assert analysis.metrics.mae_mw == 15
    assert analysis.metrics.rmse_mw == pytest.approx(250**0.5)
    assert analysis.metrics.mbe_mw == -5
    assert analysis.metrics.wape_percent == 10
    assert analysis.metrics.coverage_percent == 100
    assert analysis.metrics.expected_intervals == 2
    assert analysis.metrics.matched_intervals == 2
    assert [observation.error_mw for observation in analysis.observations] == [10, -20]


def test_reports_missing_intervals_and_coverage_without_zero_filling():
    forecasts = [_selected_forecast(0, 110), _selected_forecast(1, 120)]
    actuals = [
        HourlyActualObservation(at(0), 100),
        HourlyActualObservation(at(2), 130),
    ]

    analysis = calculate_accuracy(forecasts, actuals, [at(0), at(1), at(2)])

    assert analysis.metrics.matched_intervals == 1
    assert analysis.metrics.missing_forecast_intervals == 1
    assert analysis.metrics.missing_actual_intervals == 1
    assert analysis.metrics.coverage_percent == pytest.approx(100 / 3)
    assert analysis.metrics.mae_mw == 10


def test_empty_data_and_zero_actual_total_have_no_undefined_metrics():
    empty = calculate_accuracy([], [])
    zero_actual = calculate_accuracy(
        [_selected_forecast(0, 5)],
        [HourlyActualObservation(at(0), 0)],
    )

    assert empty.metrics.mae_mw is None
    assert empty.metrics.coverage_percent is None
    assert zero_actual.metrics.wape_percent is None
    assert zero_actual.metrics.mae_mw == 5


def test_rejects_duplicate_delivery_observations():
    with pytest.raises(ValueError, match="duplicate forecast"):
        calculate_accuracy(
            [_selected_forecast(0, 1), _selected_forecast(0, 2)],
            [HourlyActualObservation(at(0), 1)],
        )


def _selected_forecast(hour: int, generation_mw: float):
    delivery_time = at(hour)
    selected = select_forecast_vintages(
        [ForecastObservation(delivery_time, delivery_time - timedelta(hours=24), generation_mw)],
        timedelta(hours=24),
    )
    return selected[0]
