export const cutoffs = ["24h", "12h", "6h", "latest"] as const;

export type Cutoff = (typeof cutoffs)[number];

export interface AnalysisFilters {
  startDate: string;
  endDate: string;
  cutoff: Cutoff;
}

export interface AccuracyMetrics {
  mae_mw: number | null;
  rmse_mw: number | null;
  mbe_mw: number | null;
  wape_percent: number | null;
  coverage_percent: number | null;
  expected_intervals: number;
  matched_intervals: number;
  missing_forecast_intervals: number;
  missing_actual_intervals: number;
}

export interface MatchedInterval {
  delivery_time: string;
  forecast_publish_time: string;
  forecast_mw: number;
  actual_mw: number;
  error_mw: number;
}

export interface DataQuality {
  normalized_forecasts: number;
  normalized_actuals: number;
  rejected_forecasts: number;
  rejected_actuals: number;
  duplicate_forecasts_removed: number;
  duplicate_actuals_removed: number;
  incomplete_actual_hours: number;
}

export interface AnalysisResponse {
  period_start: string;
  period_end_exclusive: string;
  cutoff: Cutoff;
  metrics: AccuracyMetrics;
  observations: MatchedInterval[];
  data_quality: DataQuality;
}

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

function queryString(filters: AnalysisFilters): string {
  return new URLSearchParams({
    start_date: filters.startDate,
    end_date: filters.endDate,
    cutoff: filters.cutoff,
  }).toString();
}

export function exportAnalysisUrl(filters: AnalysisFilters): string {
  return `${apiBaseUrl}/api/exports/analysis.csv?${queryString(filters)}`;
}

export async function fetchAnalysis(filters: AnalysisFilters): Promise<AnalysisResponse> {
  const response = await fetch(`${apiBaseUrl}/api/analysis?${queryString(filters)}`);
  if (!response.ok) {
    let detail = `The analysis request failed (${response.status}).`;
    try {
      const body: { detail?: string } = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // A non-JSON upstream error still gets a useful status message.
    }
    throw new Error(detail);
  }
  return response.json() as Promise<AnalysisResponse>;
}
