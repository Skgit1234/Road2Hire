"use client";

import { useState } from "react";
import { checkBackendHealth } from "@/lib/health-check";

type CheckState =
  | { status: "idle" | "loading" }
  | { status: "success" }
  | { status: "failure"; message: string };

export default function ApiStatusPage() {
  const [check, setCheck] = useState<CheckState>({ status: "idle" });

  async function runHealthCheck() {
    setCheck({ status: "loading" });
    try {
      await checkBackendHealth();
      setCheck({ status: "success" });
    } catch (error) {
      setCheck({
        status: "failure",
        message: error instanceof Error ? error.message : "The health check failed.",
      });
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6 lg:px-8">
      <header className="mb-6">
        <p className="text-sm font-semibold uppercase tracking-wide text-indigo-600">
          Development diagnostic
        </p>
        <h1 className="mt-2 text-3xl font-bold text-slate-900">Backend connectivity</h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Check whether this browser can reach the Road2Hire backend health endpoint.
          A successful check confirms this endpoint responds; it does not verify other
          API routes or database persistence.
        </p>
      </header>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <button
          type="button"
          onClick={runHealthCheck}
          disabled={check.status === "loading"}
          className="min-h-11 rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-white hover:bg-primary-dark disabled:cursor-wait disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 focus-visible:ring-offset-2"
        >
          {check.status === "loading" ? "Checking…" : "Check backend health"}
        </button>

        <div className="mt-4 min-h-6" aria-live="polite" aria-atomic="true">
          {check.status === "loading" && (
            <p role="status" className="text-sm text-slate-600">
              Checking the Road2Hire backend…
            </p>
          )}
          {check.status === "success" && (
            <p className="text-sm font-medium text-emerald-700">
              Backend health check succeeded.
            </p>
          )}
          {check.status === "failure" && (
            <p role="alert" className="text-sm font-medium text-rose-700">
              {check.message}
            </p>
          )}
        </div>
      </section>
    </div>
  );
}
