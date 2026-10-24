
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertCircle,
  ArrowDownRight,
  ArrowUpRight,
  CheckCircle2,
  Clock3,
  Database,
  Download,
  Gauge,
  RefreshCw,
  ShieldCheck,
  Wind,
} from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  cutoffs,
  exportAnalysisUrl,
  fetchAnalysis,
  type AnalysisFilters,
  type Cutoff,
} from "../api/analysis";

const labels: Record<Cutoff, string> = {
  "24h": "24 hours before delivery",
  "12h": "12 hours before delivery",
  "6h": "6 hours before delivery",
  latest: "Latest before delivery",
};

const numberFormat = new Intl.NumberFormat("en-GB", {
  maximumFractionDigits: 1,
});

const wholeNumberFormat = new Intl.NumberFormat("en-GB", {
  maximumFractionDigits: 0,
});

function formatMw(value: number | null | undefined) {
  return value == null ? "—" : `${wholeNumberFormat.format(value)} MW`;
}

function formatPercent(value: number | null | undefined) {
  return value == null ? "—" : `${numberFormat.format(value)}%`;
}

function formatTime(value: string, includeDate = true) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return "Invalid date";

  return new Intl.DateTimeFormat("en-GB", {
    ...(includeDate ? { day: "2-digit", month: "short" } : {}),
    year: includeDate ? "numeric" : undefined,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
  }).format(date);
}

function MetricCard({
  label,
  value,
  description,
  icon: Icon,
  accent = "blue",
}: {
  label: string;
  value: string;
  description: string;
  icon: typeof Activity;
  accent?: "blue" | "teal" | "violet" | "amber";
}) {
  const accents = {
    blue: "bg-blue-50 text-blue-700 ring-blue-100",
    teal: "bg-teal-50 text-teal-700 ring-teal-100",
    violet: "bg-violet-50 text-violet-700 ring-violet-100",
    amber: "bg-amber-50 text-amber-700 ring-amber-100",
  };

  return (
    <article className="group rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm transition duration-200 hover:-translate-y-0.5 hover:shadow-md">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-slate-500">{label}</p>
        <span className={`rounded-xl p-2 ring-1 ${accents[accent]}`}>
          <Icon size={17} />
        </span>
      </div>
      <p className="mt-5 text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">
        {value}
      </p>
      <p className="mt-2 text-xs leading-5 text-slate-500">{description}</p>
    </article>
  );
}

function SectionHeading({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description?: string;
}) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-teal-700">
        {eyebrow}
      </p>
      <h2 className="mt-1.5 text-lg font-semibold tracking-tight text-slate-950">
        {title}
      </h2>
      {description && (
        <p className="mt-1.5 text-sm leading-6 text-slate-500">
          {description}
        </p>
      )}
    </div>
  );
}

export default function LiveDashboard() {
  const [startDate, setStartDate] = useState("2026-01-01");
  const [endDate, setEndDate] = useState("2026-01-31");
  const [cutoff, setCutoff] = useState<Cutoff>("24h");

  const validRange = startDate <= endDate;

  const filters: AnalysisFilters = { startDate, endDate, cutoff };

  const query = useQuery({
    queryKey: ["analysis", startDate, endDate, cutoff],
    queryFn: () => fetchAnalysis(filters),
    enabled: validRange,
    staleTime: 300_000,
    retry: 1,
  });

  const data = query.data;

  const chart =
    data?.observations.map((row) => ({
      time: row.delivery_time,
      Forecast: row.forecast_mw,
      Actual: row.actual_mw,
    })) ?? [];

  const handleStartDateChange = (value: string) => {
    setStartDate(value);
    if (value > endDate) setEndDate(value);
  };

  const handleEndDateChange = (value: string) => {
    setEndDate(value);
    if (value < startDate) setStartDate(value);
  };

  const exportUrl = validRange ? exportAnalysisUrl(filters) : undefined;

  return (
    <div className="min-h-screen bg-[#f5f7fb] text-slate-900">
      <header className="relative isolate overflow-hidden bg-[#0b1425] text-white">
        <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top_right,rgba(20,184,166,0.22),transparent_48%),radial-gradient(ellipse_at_bottom_left,rgba(59,130,246,0.14),transparent_50%)]" />

        <div className="mx-auto max-w-[1440px] px-5 pb-8 pt-5 sm:px-8 lg:px-10">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-5">
            <div className="flex items-center gap-3">
              <div className="flex size-11 items-center justify-center rounded-2xl border border-teal-300/20 bg-teal-400/10 text-teal-300 shadow-inner shadow-teal-200/5">
                <Wind size={23} />
              </div>
              <div>
                <p className="font-semibold tracking-tight">
                  Wind<span className="text-teal-300">Lens</span>
                </p>
                <p className="mt-0.5 text-xs text-slate-400">
                  Generation forecast intelligence
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-300">
                <span className="size-1.5 rounded-full bg-teal-400" />
                Historical analysis
              </span>
              <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-300">
                <Database size={13} />
                Elexon BMRS
              </span>
            </div>
          </div>

          <div className="grid gap-7 pt-8 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
            <div>
              <p className="text-sm font-medium text-teal-300">
                Great Britain · January 2026
              </p>
              <h1 className="mt-3 max-w-3xl text-3xl font-semibold leading-tight tracking-tight sm:text-4xl lg:text-[42px]">
                How accurate were the wind generation forecasts?
              </h1>
              <p className="mt-4 max-w-2xl text-sm leading-6 text-slate-300 sm:text-base sm:leading-7">
                Compare published forecasts with realised generation at
                historical decision cutoffs. Every matched observation uses
                the latest forecast that was available at that point in time.
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/[0.06] p-4 backdrop-blur-sm sm:min-w-64">
              <div className="flex items-center gap-2 text-xs font-medium text-slate-300">
                <ShieldCheck size={15} className="text-teal-300" />
                Methodology
              </div>
              <p className="mt-2 text-sm font-medium text-white">
                No future forecast leakage
              </p>
              <p className="mt-1 text-xs leading-5 text-slate-400">
                Forecast publication time is checked against each selected
                cutoff before accuracy is calculated.
              </p>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1440px] space-y-7 px-5 py-7 sm:px-8 lg:px-10 lg:py-9">
        <section className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm sm:p-6">
          <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
            <div>
              <SectionHeading
                eyebrow="Analysis workspace"
                title="Configure your comparison"
                description="Choose the delivery dates and the forecast lead time to evaluate."
              />
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold text-slate-500">
                  From date
                </span>
                <input
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none transition focus:border-teal-500 focus:bg-white focus:ring-4 focus:ring-teal-500/10"
                  type="date"
                  min="2026-01-01"
                  max={endDate}
                  value={startDate}
                  onChange={(event) => handleStartDateChange(event.target.value)}
                />
              </label>

              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold text-slate-500">
                  To date
                </span>
                <input
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none transition focus:border-teal-500 focus:bg-white focus:ring-4 focus:ring-teal-500/10"
                  type="date"
                  min={startDate}
                  max="2026-01-31"
                  value={endDate}
                  onChange={(event) => handleEndDateChange(event.target.value)}
                />
              </label>

              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold text-slate-500">
                  Forecast cutoff
                </span>
                <select
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none transition focus:border-teal-500 focus:bg-white focus:ring-4 focus:ring-teal-500/10"
                  value={cutoff}
                  onChange={(event) => setCutoff(event.target.value as Cutoff)}
                >
                  {cutoffs.map((item) => (
                    <option key={item} value={item}>
                      {labels[item]}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </div>

          {cutoff === "latest" && (
            <div className="mt-5 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-amber-950">
              <Clock3 size={18} className="mt-0.5 shrink-0 text-amber-700" />
              <div>
                <p className="text-sm font-semibold">Near-delivery benchmark</p>
                <p className="mt-1 text-xs leading-5 text-amber-900/80">
                  This scenario uses the latest eligible forecast before
                  delivery. It is a hindsight comparison, not a day-ahead
                  forecast available to a buyer.
                </p>
              </div>
            </div>
          )}
        </section>

        {query.isFetching && (
          <div className="flex items-center gap-3 rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-900">
            <RefreshCw size={16} className="animate-spin" />
            <span>
              {data
                ? "Refreshing analysis from Elexon…"
                : "Loading and validating Elexon data…"}
            </span>
          </div>
        )}

        {query.isError && (
          <div
            role="alert"
            className="flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-5 text-rose-950"
          >
            <AlertCircle size={20} className="mt-0.5 shrink-0 text-rose-700" />
            <div className="min-w-0 flex-1">
              <p className="font-semibold">Unable to load the analysis</p>
              <p className="mt-1 break-words text-sm leading-6 text-rose-800">
                {query.error.message}
              </p>
              <button
                type="button"
                onClick={() => void query.refetch()}
                className="mt-3 inline-flex items-center gap-2 rounded-lg border border-rose-200 bg-white px-3 py-2 text-sm font-medium transition hover:bg-rose-100"
              >
                <RefreshCw size={14} />
                Try again
              </button>
            </div>
          </div>
        )}

        {!validRange && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
            The start date must be on or before the end date.
          </div>
        )}

        {!data && query.isPending && !query.isFetching && validRange && (
          <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center">
            <Activity className="mx-auto text-slate-300" size={30} />
            <p className="mt-3 font-medium text-slate-700">
              Preparing your analysis
            </p>
            <p className="mt-1 text-sm text-slate-500">
              No metrics are displayed until the API returns validated results.
            </p>
          </div>
        )}

        {data && (
          <>
            <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <MetricCard
                label="Mean absolute error"
                value={formatMw(data.metrics.mae_mw)}
                description="Average absolute forecast error. Lower is better."
                icon={Gauge}
                accent="blue"
              />
              <MetricCard
                label="Root mean square error"
                value={formatMw(data.metrics.rmse_mw)}
                description="Penalises larger forecast misses more heavily."
                icon={Activity}
                accent="violet"
              />
              <MetricCard
                label="Mean forecast bias"
                value={formatMw(data.metrics.mbe_mw)}
                description="Positive means overforecasting; negative means underforecasting."
                icon={
                  (data.metrics.mbe_mw ?? 0) >= 0
                    ? ArrowUpRight
                    : ArrowDownRight
                }
                accent="teal"
              />
              <MetricCard
                label="Data coverage"
                value={formatPercent(data.metrics.coverage_percent)}
                description={`${data.metrics.matched_intervals.toLocaleString("en-GB")} matched out of ${data.metrics.expected_intervals.toLocaleString("en-GB")} expected hourly intervals.`}
                icon={CheckCircle2}
                accent="amber"
              />
            </section>

            <section className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-sm">
              <div className="flex flex-col gap-4 border-b border-slate-100 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
                <SectionHeading
                  eyebrow="Generation profile"
                  title="Forecast vs actual"
                  description={`${data.observations.length.toLocaleString("en-GB")} matched hourly observations · Values in MW · Times in UTC`}
                />

                <div className="flex flex-wrap items-center gap-3">
                  <div className="flex items-center gap-3 text-xs font-medium text-slate-600">
                    <span className="flex items-center gap-1.5">
                      <span className="h-0.5 w-4 rounded bg-blue-600" />
                      Forecast
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="h-0.5 w-4 rounded bg-teal-600" />
                      Actual
                    </span>
                  </div>

                  {exportUrl && (
                    <a
                      href={exportUrl}
                      className="inline-flex items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-slate-800 focus:outline-none focus:ring-4 focus:ring-slate-400/30"
                    >
                      <Download size={15} />
                      Export CSV
                    </a>
                  )}
                </div>
              </div>

              <div className="p-4 sm:p-6">
                {data.observations.length === 0 ? (
                  <div className="flex min-h-64 flex-col items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50 px-5 text-center">
                    <Activity size={30} className="text-slate-300" />
                    <p className="mt-3 font-medium text-slate-700">
                      No matched observations
                    </p>
                    <p className="mt-1 max-w-md text-sm leading-6 text-slate-500">
                      There are no intervals with both an eligible forecast
                      and a complete actual value for this selection. Check
                      the coverage and data-quality details below.
                    </p>
                  </div>
                ) : (
                  <div className="h-[300px] w-full sm:h-[380px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart
                        data={chart}
                        margin={{ top: 8, right: 12, left: 0, bottom: 4 }}
                      >
                        <CartesianGrid
                          stroke="#e9eef5"
                          strokeDasharray="3 5"
                          vertical={false}
                        />
                        <XAxis
                          dataKey="time"
                          tickFormatter={(value) => formatTime(String(value), false)}
                          minTickGap={48}
                          tickLine={false}
                          axisLine={false}
                          tick={{ fill: "#64748b", fontSize: 11 }}
                          tickMargin={12}
                        />
                        <YAxis
                          width={68}
                          tickFormatter={(value) =>
                            wholeNumberFormat.format(Number(value))
                          }
                          tickLine={false}
                          axisLine={false}
                          tick={{ fill: "#64748b", fontSize: 11 }}
                          tickMargin={8}
                          domain={["auto", "auto"]}
                        />
                        <ReferenceLine y={0} stroke="#cbd5e1" />
                        <Tooltip
                          labelFormatter={(value) =>
                            `${formatTime(String(value))} UTC`
                          }
                          formatter={(value, name) => [
                            formatMw(Number(value)),
                            String(name),
                          ]}
                          contentStyle={{
                            border: "1px solid #e2e8f0",
                            borderRadius: 12,
                            boxShadow: "0 12px 32px rgba(15,23,42,0.10)",
                            fontSize: 12,
                          }}
                        />
                        <Line
                          type="monotone"
                          dataKey="Forecast"
                          stroke="#2563eb"
                          strokeWidth={2}
                          dot={false}
                          activeDot={{ r: 4, strokeWidth: 0 }}
                          connectNulls={false}
                        />
                        <Line
                          type="monotone"
                          dataKey="Actual"
                          stroke="#0d9488"
                          strokeWidth={2}
                          dot={false}
                          activeDot={{ r: 4, strokeWidth: 0 }}
                          connectNulls={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}

                <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-4 text-xs text-slate-500">
                  <span>
                    Forecast scenario:{" "}
                    <strong className="font-semibold text-slate-700">
                      {labels[cutoff]}
                    </strong>
                  </span>
                  <span>Source: Elexon BMRS</span>
                </div>
              </div>
            </section>

            <section className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-sm">
              <div className="flex flex-col gap-3 border-b border-slate-100 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
                <SectionHeading
                  eyebrow="Interval explorer"
                  title="Matched delivery intervals"
                  description="Inspect the selected forecast vintage and its realised error."
                />
                <span className="w-fit rounded-full bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-600">
                  {data.observations.length.toLocaleString("en-GB")} rows
                </span>
              </div>

              <div className="max-h-[520px] overflow-auto">
                <table className="min-w-[760px] w-full text-left text-sm">
                  <thead className="sticky top-0 z-10 bg-slate-50/95 text-xs uppercase tracking-wide text-slate-500 backdrop-blur">
                    <tr>
                      <th className="px-5 py-3.5 font-semibold">Delivery (UTC)</th>
                      <th className="px-5 py-3.5 text-right font-semibold">
                        Forecast (MW)
                      </th>
                      <th className="px-5 py-3.5 font-semibold">
                        Forecast published (UTC)
                      </th>
                      <th className="px-5 py-3.5 text-right font-semibold">
                        Actual (MW)
                      </th>
                      <th className="px-5 py-3.5 text-right font-semibold">
                        Error (MW)
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {data.observations.map((row) => (
                      <tr
                        key={row.delivery_time}
                        className="transition hover:bg-slate-50/80"
                      >
                        <td className="whitespace-nowrap px-5 py-3.5 font-medium text-slate-800">
                          {formatTime(row.delivery_time)}
                        </td>
                        <td className="whitespace-nowrap px-5 py-3.5 text-right tabular-nums text-slate-700">
                          {formatMw(row.forecast_mw)}
                        </td>
                        <td className="whitespace-nowrap px-5 py-3.5 text-slate-500">
                          {formatTime(row.forecast_publish_time)}
                        </td>
                        <td className="whitespace-nowrap px-5 py-3.5 text-right tabular-nums text-slate-700">
                          {formatMw(row.actual_mw)}
                        </td>
                        <td
                          className={`whitespace-nowrap px-5 py-3.5 text-right font-medium tabular-nums ${
                            row.error_mw > 0
                              ? "text-amber-700"
                              : row.error_mw < 0
                                ? "text-blue-700"
                                : "text-slate-600"
                          }`}
                        >
                          {row.error_mw > 0 ? "+" : ""}
                          {formatMw(row.error_mw)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm sm:p-6">
              <div className="flex items-center gap-2">
                <Database size={18} className="text-teal-700" />
                <h2 className="font-semibold text-slate-950">
                  Data quality and methodology
                </h2>
              </div>

              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
                Only WIND records from FUELHH are used as actuals. Half-hourly
                actuals are averaged into an hourly MW value only when both
                half-hour observations are available and valid. Forecasts are
                never duplicated to increase the sample count.
              </p>

              <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {[
                  ["Forecast records accepted", data.data_quality.normalized_forecasts],
                  ["Actual records accepted", data.data_quality.normalized_actuals],
                  ["Forecast records rejected", data.data_quality.rejected_forecasts],
                  ["Actual records rejected", data.data_quality.rejected_actuals],
                  ["Duplicate forecasts removed", data.data_quality.duplicate_forecasts_removed],
                  ["Duplicate actuals removed", data.data_quality.duplicate_actuals_removed],
                  ["Incomplete actual hours", data.data_quality.incomplete_actual_hours],
                  ["Missing forecast intervals", data.metrics.missing_forecast_intervals],
                  ["Missing actual intervals", data.metrics.missing_actual_intervals],
                ].map(([label, value]) => (
                  <div
                    key={String(label)}
                    className="flex items-center justify-between gap-3 rounded-xl bg-slate-50 px-4 py-3"
                  >
                    <span className="text-xs leading-5 text-slate-500">
                      {label}
                    </span>
                    <span className="shrink-0 text-sm font-semibold tabular-nums text-slate-800">
                      {Number(value).toLocaleString("en-GB")}
                    </span>
                  </div>
                ))}
              </div>

              <div className="mt-5 flex items-start gap-3 rounded-xl border border-blue-100 bg-blue-50/70 p-4">
                <ShieldCheck size={17} className="mt-0.5 shrink-0 text-blue-700" />
                <p className="text-xs leading-5 text-blue-950/80">
                  Error is calculated as forecast minus actual. Positive
                  values mean overforecasting; negative values mean
                  underforecasting. Coverage is matched intervals divided by
                  expected hourly intervals. Missing data is not treated as
                  zero.
                </p>
              </div>
            </section>
          </>
        )}

        <footer className="flex flex-col gap-2 border-t border-slate-200 py-5 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between">
          <span>WindLens · Historical wind generation forecast analysis</span>
          <span>Data source: Elexon BMRS · All displayed times are UTC</span>
        </footer>
      </main>
    </div>
  );
}
