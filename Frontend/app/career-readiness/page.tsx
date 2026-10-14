
"use client";

import Link from "next/link";
import { useCandidateProfile } from "@/components/profile/CandidateProfileProvider";

const categoryPresentation = {
  "On track": {
    tone: "bg-emerald-500",
    badge: "border-emerald-200 bg-emerald-50 text-emerald-700",
  },
  "Build next": {
    tone: "bg-indigo-600",
    badge: "border-indigo-200 bg-indigo-50 text-indigo-700",
  },
  Priority: {
    tone: "bg-amber-500",
    badge: "border-amber-200 bg-amber-50 text-amber-700",
  },
} as const;

const strengths = [
  "Consistent technical foundation",
  "Resume communicates relevant experience",
  "Clear direction toward a target role",
];

const priorities = [
  {
    title: "Practice interview scenarios",
    detail: "Complete one technical mock interview and review where your explanations can be clearer.",
    time: "45 min",
  },
  {
    title: "Strengthen a portfolio project",
    detail: "Add a concise case study with the problem, your decisions, and the measurable outcome.",
    time: "This week",
  },
  {
    title: "Rehearse project stories",
    detail: "Prepare two short examples that show collaboration, ownership, and impact.",
    time: "20 min",
  },
];

const nextSteps = [
  { title: "Review your skill profile", status: "Completed", style: "bg-emerald-50 text-emerald-700" },
  { title: "Update resume with project outcomes", status: "In progress", style: "bg-indigo-50 text-indigo-700" },
  { title: "Schedule a mock interview", status: "Recommended", style: "bg-slate-100 text-slate-600" },
];

function ProgressBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div
      className="h-2.5 overflow-hidden rounded-full bg-slate-100"
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={value}
      aria-valuetext={`${value} out of 100`}
    >
      <div className={`h-full rounded-full ${color}`} style={{ width: `${value}%` }} />
    </div>
  );
}

export default function CareerReadinessPage() {
  const { profile } = useCandidateProfile();
  const categories = profile.readiness.categories;
  const overallScore = profile.readiness.overall;

  return (
    <div className="min-h-screen bg-background px-4 pb-8 pt-16 sm:px-6 md:py-8 lg:px-8">
      <div className="mx-auto max-w-[1440px]">
        <header className="mb-6 flex flex-col gap-4 border-b border-slate-200 pb-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="mb-1 text-sm font-semibold text-primary">Career Assessment</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-900">Career readiness</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
              See how prepared you are for your next role and choose a practical focus for what comes next.
            </p>
          </div>
          <span className="inline-flex w-fit items-center gap-2 rounded-full border border-indigo-100 bg-white px-3 py-1.5 text-xs font-medium text-slate-500">
            <span className="h-2 w-2 rounded-full bg-indigo-500" />
            Sample assessment
          </span>
        </header>

        <section className="mb-6 grid gap-5 lg:grid-cols-[minmax(0,1.2fr)_minmax(280px,0.8fr)]" aria-labelledby="overall-score-heading">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_6px_18px_rgba(15,23,42,0.04)] sm:p-7">
            <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <p className="text-sm font-medium text-slate-500">Overall readiness score</p>
                <h2 id="overall-score-heading" className="mt-2 flex items-baseline gap-1 text-5xl font-bold tracking-tight text-slate-900">
                  {overallScore}<span className="text-2xl font-semibold text-slate-400">/100</span>
                </h2>
                <p className="mt-3 max-w-xl text-sm leading-6 text-slate-500">
                  You have a solid base. Interview practice and a stronger project story are the most useful next steps.
                </p>
              </div>
              <div className="w-full shrink-0 sm:max-w-[280px]">
                <div className="mb-2 flex items-center justify-between gap-3 text-xs font-medium text-slate-500">
                  <span>Current readiness</span><span className="tabular-nums">{overallScore}%</span>
                </div>
                <ProgressBar label="Overall career readiness" value={overallScore} color="bg-primary" />
                <div className="mt-2 flex justify-between text-[11px] text-slate-400"><span>Getting started</span><span>Job ready</span></div>
              </div>
            </div>
          </div>

          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_6px_18px_rgba(15,23,42,0.04)] sm:p-6" aria-labelledby="strengths-heading">
            <div className="flex items-center justify-between gap-3">
              <h2 id="strengths-heading" className="text-base font-semibold text-slate-900">Current strengths</h2>
              <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">3 areas</span>
            </div>
            <ul className="mt-4 space-y-3">
              {strengths.map((strength) => (
                <li key={strength} className="flex items-start gap-3 text-sm leading-5 text-slate-600">
                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-[11px] font-bold text-emerald-700" aria-hidden="true">✓</span>
                  {strength}
                </li>
              ))}
            </ul>
          </section>
        </section>

        <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1.5fr)_minmax(300px,0.85fr)]">
          <section className="min-w-0 rounded-2xl border border-slate-200 bg-white p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_6px_18px_rgba(15,23,42,0.04)] sm:p-6" aria-labelledby="breakdown-heading">
            <div className="mb-5">
              <h2 id="breakdown-heading" className="text-lg font-semibold text-slate-900">Readiness breakdown</h2>
              <p className="mt-1 text-sm text-slate-500">Sample scores for five areas that shape role readiness.</p>
            </div>
            <div className="space-y-3">
              {categories.length === 0 ? (
                <p className="rounded-xl border border-dashed border-slate-300 px-4 py-8 text-center text-sm text-slate-500">
                  No readiness categories are available in this sample profile yet.
                </p>
              ) : categories.map((category) => (
                <article key={category.name} className="rounded-xl border border-slate-200 p-4 sm:p-5">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0">
                      <h3 className="font-semibold text-slate-900">{category.name}</h3>
                      <p className="mt-1 text-xs leading-5 text-slate-500">{category.note}</p>
                    </div>
                    <div className="flex items-center gap-2 sm:shrink-0">
                      <span className="text-lg font-bold tabular-nums text-slate-900" aria-label={`${category.score} out of 100`}>{category.score}<span className="text-sm font-medium text-slate-400">/100</span></span>
                      <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${categoryPresentation[category.status].badge}`}>{category.status}</span>
                    </div>
                  </div>
                  <div className="mt-4 flex items-center gap-3">
                    <div className="min-w-0 flex-1">
                      <ProgressBar label={`${category.name} readiness`} value={category.score} color={categoryPresentation[category.status].tone} />
                    </div>
                    <span className="w-8 text-right text-xs tabular-nums text-slate-500">{category.score}%</span>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <aside className="space-y-5">
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_6px_18px_rgba(15,23,42,0.04)] sm:p-6" aria-labelledby="priorities-heading">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.12em] text-amber-700">Focus next</p>
                  <h2 id="priorities-heading" className="mt-1 text-lg font-semibold text-slate-900">Improvement priorities</h2>
                </div>
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-amber-50 text-amber-700" aria-hidden="true">!</span>
              </div>
              <ol className="mt-5 space-y-5">
                {priorities.map((priority, index) => (
                  <li key={priority.title} className="flex gap-3">
                    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-xs font-bold text-slate-600">0{index + 1}</span>
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                        <h3 className="text-sm font-semibold text-slate-800">{priority.title}</h3>
                        <span className="text-[11px] text-slate-400">{priority.time}</span>
                      </div>
                      <p className="mt-1 text-xs leading-5 text-slate-500">{priority.detail}</p>
                    </div>
                  </li>
                ))}
              </ol>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_6px_18px_rgba(15,23,42,0.04)] sm:p-6" aria-labelledby="steps-heading">
              <h2 id="steps-heading" className="text-base font-semibold text-slate-900">Your next steps</h2>
              <ul className="mt-4 space-y-3">
                {nextSteps.map((step) => (
                  <li key={step.title} className="flex flex-col gap-2 border-b border-slate-100 pb-3 last:border-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between">
                    <span className="text-sm font-medium text-slate-700">{step.title}</span>
                    <span className={`w-fit rounded-full px-2.5 py-1 text-[11px] font-semibold ${step.style}`}>{step.status}</span>
                  </li>
                ))}
              </ul>
              <Link href="/learning-roadmap" className="mt-5 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-primary px-4 py-3 text-sm font-semibold text-white transition hover:bg-primary-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300 focus-visible:ring-offset-2">
                View learning roadmap <span aria-hidden="true">→</span>
              </Link>
            </section>

            <p className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-xs leading-5 text-slate-500">
              Illustrative sample data only. These readiness scores and recommendations are not based on a live resume or assessment.
            </p>
          </aside>
        </div>
      </div>
    </div>
  );
}
