// Live dashboard component.

import LiveDashboard from "./components/LiveDashboard";
import { Activity, BarChart3, CalendarDays, Wind } from "lucide-react";

const navigation = [
  { label: "Overview", icon: BarChart3, active: true },
  { label: "Forecast analysis", icon: Wind, active: false },
  { label: "Interval data", icon: CalendarDays, active: false },
];

function App() {
  return <LiveDashboard />;
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center gap-3 px-5 py-4 sm:px-8">
          <div className="flex size-10 items-center justify-center rounded-xl bg-slate-900 text-white">
            <Wind size={21} />
          </div>

          <div>
            <h1 className="font-semibold tracking-tight">
              Wind Forecast Analytics
            </h1>
            <p className="text-xs text-slate-500">
              UK electricity generation · Historical analysis
            </p>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-8 px-5 py-8 sm:px-8 lg:grid-cols-[220px_minmax(0,1fr)]">
        <aside>
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
            Workspace
          </p>

          <nav aria-label="Main navigation" className="space-y-1">
            {navigation.map(({ label, icon: Icon, active }) => (
              <button
                key={label}
                type="button"
                disabled={!active}
                aria-current={active ? "page" : undefined}
                className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm ${
                  active
                    ? "bg-slate-900 font-medium text-white"
                    : "text-slate-500"
                }`}
              >
                <Icon size={17} />
                {label}
              </button>
            ))}
          </nav>

          <div className="mt-8 rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-sm font-medium">Analysis period</p>
            <p className="mt-1 text-sm text-slate-600">January 2026</p>
            <p className="mt-3 text-xs leading-5 text-slate-500">
              Historical delivery intervals. Forecast availability depends
              on the publication history provided by the source.
            </p>
          </div>
        </aside>

        <main className="min-w-0">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-sm text-slate-500">Overview</p>
              <h2 className="mt-1 text-2xl font-semibold tracking-tight">
                Wind generation performance
              </h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
                Compare published wind generation forecasts with actual
                generation and evaluate forecast accuracy at a historical
                decision cutoff.
              </p>
            </div>

            <div className="flex items-center gap-2 self-start rounded-full border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-800 sm:self-auto">
              <Activity size={14} />
              Data integration pending
            </div>
          </div>

          <section className="mt-7 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {[
              "Forecast generation",
              "Actual generation",
              "Mean absolute error",
              "Data coverage",
            ].map((label) => (
              <article
                key={label}
                className="rounded-xl border border-slate-200 bg-white p-5"
              >
                <p className="text-sm text-slate-500">{label}</p>
                <p className="mt-4 text-2xl font-semibold text-slate-300">
                  —
                </p>
                <p className="mt-2 text-xs text-slate-400">
                  Awaiting validated data
                </p>
              </article>
            ))}
          </section>

          <section className="mt-5 rounded-xl border border-slate-200 bg-white p-6">
            <h3 className="font-semibold">Forecast versus actual generation</h3>
            <p className="mt-2 text-sm leading-6 text-slate-500">
              The time-series chart will appear here once the source data,
              publication timestamps and matching logic have been validated.
            </p>

            <div className="mt-6 flex min-h-48 items-center justify-center rounded-lg border border-dashed border-slate-200 bg-slate-50 px-5 text-center">
              <div>
                <BarChart3 className="mx-auto text-slate-400" size={30} />
                <p className="mt-3 text-sm font-medium text-slate-600">
                  No data loaded
                </p>
                <p className="mt-1 text-xs text-slate-400">
                  We will not display fabricated metrics or sample values as
                  real results.
                </p>
              </div>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}

export default App;
