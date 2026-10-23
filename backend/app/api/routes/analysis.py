from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.schemas import (
    AccuracyMetrics,
    AnalysisResponse,
    DataQualityResponse,
    MatchedIntervalResponse,
)
from app.services.analysis_service import AnalysisService
from app.services.elexon_client import ElexonClientError

router = APIRouter(tags=["Analysis"])
_analysis_service = AnalysisService()


def get_analysis_service() -> AnalysisService:
    return _analysis_service


@router.get("/analysis", response_model=AnalysisResponse)
async def get_analysis(
    start_date: date = Query(default=date(2026, 1, 1)),
    end_date: date = Query(default=date(2026, 1, 31)),
    cutoff: Literal["24h", "12h", "6h", "latest"] = "24h",
    service: AnalysisService = Depends(get_analysis_service),
) -> AnalysisResponse:
    """Return January 2026 wind forecast accuracy and chart-ready matches."""
    try:
        payload = await service.analyze(start_date, end_date, cutoff)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ElexonClientError as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve Elexon wind generation data. Please retry shortly.",
        ) from exc

    return AnalysisResponse(
        period_start=payload.period_start,
        period_end_exclusive=payload.period_end_exclusive,
        cutoff=payload.cutoff,
        metrics=AccuracyMetrics.model_validate(
            payload.analysis.metrics, from_attributes=True
        ),
        observations=[
            MatchedIntervalResponse.model_validate(observation, from_attributes=True)
            for observation in payload.analysis.observations
        ],
        data_quality=DataQualityResponse.model_validate(
            payload.data_quality, from_attributes=True
        ),
    )
