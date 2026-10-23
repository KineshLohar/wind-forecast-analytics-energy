import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertCircle, Download, Wind } from "lucide-react";
import {
  Line,
  LineChart,
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
  "24h": "24h before delivery",
  "12h": "12h before delivery",
  "6h": "6h before delivery",
  latest: "Latest before delivery",
};
const mw = (value: number | null) =>
  value === null ? "—" : `${Math.round(value).toLocaleString("en-GB")} MW`;
const time = (value: string) =>
  new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
  }).format(new Date(value));

function Card({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border bg-white p-5">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
    </div>
  );
}

export default function LiveDashboard() {
  const [startDate, setStartDate] = useState("2026-01-01");
  const [endDate, setEndDate] = useState("2026-01-31");
  const [cutoff, setCutoff] = useState<Cutoff>("24h");
  const filters: AnalysisFilters = { startDate, endDate, cutoff };
  const query = useQuery({
    queryKey: ["analysis", filters],
    queryFn: () => fetchAnalysis(filters),
    staleTime: 300000,
  });
  const data = query.data;
  const chart =
    data?.observations.map((row) => ({
      time: row.delivery_time,
      Forecast: row.forecast_mw,
      Actual: row.actual_mw,
    })) ?? [];
  return (
    <main className="min-h-screen bg-slate-50 p-5 text-slate-900">
      <header className="mx-auto flex max-w-7xl items-center gap-3 py-4">
        <div className="rounded-xl bg-slate-900 p-2 text-white">
          <Wind />
        </div>
        <div>
          <h1 className="font-semibold">Wind Forecast Analytics</h1>
          <p className="text-xs text-slate-500">
            UK electricity generation · January 2026
          </p>
        </div>
      </header>
      <div className="mx-auto max-w-7xl">
        <section className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="text-2xl font-semibold">
              Wind generation performance
            </h2>
            <p className="text-sm text-slate-500">
              Forecast accuracy at a procurement cutoff.
            </p>
          </div>
          <div className="flex gap-2">
            <input
              className="rounded border p-2"
              type="date"
              min="2026-01-01"
              max="2026-01-31"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
            <input
              className="rounded border p-2"
              type="date"
              min="2026-01-01"
              max="2026-01-31"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
            <select
              className="rounded border p-2"
              value={cutoff}
              onChange={(e) => setCutoff(e.target.value as Cutoff)}
            >
              {cutoffs.map((item) => (
                <option key={item} value={item}>{labels[item]}</option>
              ))}
            </select>
          </div>
        </section>
        {cutoff === "latest" && (
          <p className="mt-4 rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            <b>Benchmark mode:</b> latest forecasts were unavailable to a
            day-ahead buyer.
          </p>
        )}
        {query.isPending && (
          <p className="mt-6 rounded bg-white p-8 text-center">
            Loading Elexon analysis…
          </p>
        )}
        {query.isError && (
          <p className="mt-6 flex gap-2 rounded bg-rose-50 p-4 text-rose-900">
            <AlertCircle />
            {query.error.message}
          </p>
        )}
        {data && (
          <>
            <section className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <Card label="MAE" value={mw(data.metrics.mae_mw)} />
              <Card label="RMSE" value={mw(data.metrics.rmse_mw)} />
              <Card label="Bias" value={mw(data.metrics.mbe_mw)} />
              <Card
                label="Coverage"
                value={`${data.metrics.coverage_percent?.toFixed(1) ?? "—"}%`}
              />
            </section>
            <section className="mt-5 rounded-xl border bg-white p-5">
              <div className="flex justify-between">
                <h3 className="font-semibold">Forecast versus actual</h3>
                <p className="mt-1 text-sm text-slate-500">
                  Scenario: <strong>{labels[cutoff]}</strong>. Each forecast is the newest publication available by this cutoff.
                </p>
                <a
                  className="flex items-center gap-2 rounded bg-slate-900 px-3 py-2 text-sm text-white"
                  href={exportAnalysisUrl(filters)}
                >
                  <Download size={15} />
                  CSV
                </a>
              </div>
              <div className="mt-5 h-80">
                <ResponsiveContainer>
                  <LineChart data={chart}>
                    <XAxis
                      dataKey="time"
                      tickFormatter={time}
                      minTickGap={80}
                    />
                    <YAxis />
                    <Tooltip labelFormatter={(label) => time(String(label))} />
                    <Line dataKey="Forecast" stroke="#2563eb" dot={false} />
                    <Line dataKey="Actual" stroke="#0f766e" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </section>
            <section className="mt-5 max-h-[500px] overflow-auto rounded-xl border bg-white">
              <table className="min-w-full text-sm">
                <thead className="sticky top-0 bg-slate-50">
                  <tr>
                    <th className="p-3 text-left">Delivery</th>
                    <th className="p-3 text-left">Forecast</th>
                    <th className="p-3 text-right">Forecast published</th>
                    <th className="p-3 text-right">Actual</th>
                    <th className="p-3 text-right">Error</th>
                  </tr>
                </thead>
                <tbody>
                  {data.observations.map((row) => (
                    <tr className="border-t" key={row.delivery_time}>
                      <td className="p-3">{time(row.delivery_time)}</td>
                      <td className="p-3">{time(row.forecast_publish_time)}</td>
                      <td className="p-3 text-right">{mw(row.forecast_mw)}</td>
                      <td className="p-3 text-right">{mw(row.actual_mw)}</td>
                      <td className="p-3 text-right">{mw(row.error_mw)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          </>
        )}
      </div>
    </main>
  );
}
