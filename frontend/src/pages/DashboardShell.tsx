import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  Building2,
  CalendarClock,
  Landmark,
  LineChart,
  RefreshCw,
  Wallet,
} from "lucide-react";

import { fetchHealth, fetchReadiness } from "../api/client";

const MODULES = [
  {
    name: "Banking Actors & Accounts",
    description: "Manage banks, brokers, neobanks, and multi-currency checking/brokerage accounts.",
    icon: Landmark,
    phase: "Phase 1",
  },
  {
    name: "Cashflow & Recurring Rules",
    description:
      "Track ordinary income/expenses, one-offs, 13th/14th salaries, bonuses, and automated schedules.",
    icon: CalendarClock,
    phase: "Phase 1",
  },
  {
    name: "Portfolio, Bonds & PAC",
    description:
      "Ledger-based tracking for stocks, ETFs, bonds (coupons & YTM), and recurring PAC plans.",
    icon: Wallet,
    phase: "Phase 2",
  },
  {
    name: "Live Market Data & Analytics",
    description:
      "Free-tier market data adapters, Redis caching, SSE price streaming, and net worth history.",
    icon: LineChart,
    phase: "Phase 3",
  },
] as const;

export function DashboardShell() {
  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    retry: false,
  });

  const readinessQuery = useQuery({
    queryKey: ["readiness"],
    queryFn: fetchReadiness,
    retry: false,
  });

  const refreshAll = () => {
    void healthQuery.refetch();
    void readinessQuery.refetch();
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-900/70 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/30">
              <Building2 className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-lg font-semibold tracking-tight">Finance4Dummies</h1>
              <p className="text-xs text-slate-400">
                Personal Finance, Banking Actors &amp; Portfolio Workspace
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={refreshAll}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm font-medium text-slate-200 transition hover:bg-slate-700"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh Status
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-8 px-6 py-10">
        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <Activity className="h-5 w-5 text-emerald-400" />
              <div>
                <h2 className="text-base font-semibold">System Foundation Status</h2>
                <p className="text-sm text-slate-400">
                  Phase 0 environment connectivity between React, FastAPI, PostgreSQL/TimescaleDB,
                  and Redis.
                </p>
              </div>
            </div>

            <div className="flex flex-wrap gap-3 text-xs font-medium">
              <StatusBadge
                label="API"
                state={
                  healthQuery.isLoading
                    ? "loading"
                    : healthQuery.isSuccess
                      ? "ok"
                      : "error"
                }
              />
              <StatusBadge
                label="PostgreSQL"
                state={
                  readinessQuery.isLoading
                    ? "loading"
                    : readinessQuery.data?.dependencies.database === "ok"
                      ? "ok"
                      : "error"
                }
              />
              <StatusBadge
                label="Redis"
                state={
                  readinessQuery.isLoading
                    ? "loading"
                    : readinessQuery.data?.dependencies.redis === "ok"
                      ? "ok"
                      : "error"
                }
              />
            </div>
          </div>
        </section>

        <section>
          <h2 className="mb-4 text-sm font-semibold tracking-wider text-slate-400 uppercase">
            Planned Domain Modules
          </h2>
          <div className="grid gap-4 md:grid-cols-2">
            {MODULES.map((mod) => {
              const Icon = mod.icon;
              return (
                <article
                  key={mod.name}
                  className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5 transition hover:border-slate-700"
                >
                  <div className="mb-3 flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <Icon className="h-5 w-5 text-emerald-400" />
                      <h3 className="font-medium text-slate-100">{mod.name}</h3>
                    </div>
                    <span className="rounded-full bg-slate-800 px-2.5 py-0.5 text-xs font-medium text-slate-300">
                      {mod.phase}
                    </span>
                  </div>
                  <p className="text-sm leading-relaxed text-slate-400">{mod.description}</p>
                </article>
              );
            })}
          </div>
        </section>
      </main>
    </div>
  );
}

function StatusBadge({ label, state }: { label: string; state: "loading" | "ok" | "error" }) {
  const styles =
    state === "ok"
      ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
      : state === "loading"
        ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
        : "border-rose-500/30 bg-rose-500/10 text-rose-300";

  const statusText = state === "ok" ? "Online" : state === "loading" ? "Checking" : "Offline";

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 ${styles}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {label}: {statusText}
    </span>
  );
}
