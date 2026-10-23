
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    environment: str


class ErrorResponse(BaseModel):
    detail: str


class ForecastRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    publish_time: datetime
    start_time: datetime
    generation_mw: float


class AccuracyMetrics(BaseModel):
    mae_mw: float | None
    rmse_mw: float | None
    mbe_mw: float | None
    wape_percent: float | None
    coverage_percent: float | None
    expected_intervals: int
    matched_intervals: int
    missing_forecast_intervals: int
    missing_actual_intervals: int

class MatchedIntervalResponse(BaseModel):
    delivery_time: datetime
    forecast_publish_time: datetime
    forecast_mw: float
    actual_mw: float
    error_mw: float


class DataQualityResponse(BaseModel):
    normalized_forecasts: int
    normalized_actuals: int
    rejected_forecasts: int
    rejected_actuals: int
    duplicate_forecasts_removed: int
    duplicate_actuals_removed: int
    incomplete_actual_hours: int


class AnalysisResponse(BaseModel):
    period_start: datetime
    period_end_exclusive: datetime
    cutoff: str
    metrics: AccuracyMetrics
    observations: list[MatchedIntervalResponse]
    data_quality: DataQualityResponse
