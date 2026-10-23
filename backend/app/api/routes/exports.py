import csv
from datetime import date
from io import StringIO
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.api.routes.analysis import get_analysis_service
from app.services.analysis_service import AnalysisService
from app.services.elexon_client import ElexonClientError

router = APIRouter(tags=["Exports"])


@router.get("/exports/analysis.csv")
async def export_analysis_csv(
    start_date: date = Query(default=date(2026, 1, 1)),
    end_date: date = Query(default=date(2026, 1, 31)),
    cutoff: Literal["24h", "12h", "6h", "latest"] = "24h",
    service: AnalysisService = Depends(get_analysis_service),
) -> Response:
    """Export the selected analysis intervals as a CSV file."""
    try:
        payload = await service.analyze(start_date, end_date, cutoff)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ElexonClientError as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve Elexon wind generation data. Please retry shortly.",
        ) from exc

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["delivery_time_utc", "forecast_publish_time_utc", "forecast_mw", "actual_mw", "error_mw"])
    for observation in payload.analysis.observations:
        writer.writerow(
            [
                observation.delivery_time.isoformat().replace("+00:00", "Z"),
                observation.forecast_publish_time.isoformat().replace("+00:00", "Z"),
                observation.forecast_mw,
                observation.actual_mw,
                observation.error_mw,
            ]
        )

    filename = f"wind-analysis-{start_date.isoformat()}-to-{end_date.isoformat()}-{cutoff}.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
