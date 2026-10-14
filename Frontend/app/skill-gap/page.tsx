"use client";

import Link from "next/link";
import { useState } from "react";
import { type SkillPriority } from "../data/sample-data";
import { useCandidateProfile } from "@/components/profile/CandidateProfileProvider";

type PriorityFilter = "All" | SkillPriority;

const recommendations = [
  {
    skill: "Cloud Fundamentals",
    action: "Deploy a small app and document the hosting, storage, and access setup.",
    duration: "2 weeks",
  },
  {
    skill: "TypeScript",
    action: "Convert one React feature to strict TypeScript and add typed API models.",
    duration: "3 sessions",
  },
  {
    skill: "System Design",
    action: "Sketch the data flow and trade-offs for a service you already know.",
    duration: "2 practice rounds",
  },
];

const priorityStyles: Record<SkillPriority, string> = {
  High: "border-rose-200 bg-rose-50 text-rose-700",
  Medium: "border-amber-200 bg-amber-50 text-amber-700",
  Low: "border-emerald-200 bg-emerald-50 text-emerald-700",
};

function SkillComparison({
  current,
  target,
  name,
}: {
  current: number;
  target: number;
  name: string;
}) {
  return (
    <div
      className="relative mt-3 h-3 rounded-full bg-slate-100"
      role="img"
      aria-label={`${name}: current ${current} out of 100, target ${target} out of 100`}
    >
      <div
        className="absolute inset-y-0 left-0 rounded-full bg-indigo-600"
        style={{ width: `${current}%` }}
      />
      <div
        className="absolute -top-1 -bottom-1 z-10 w-0.5 -translate-x-1/2 border-l-2 border-dashed border-slate-700"
        style={{ left: `${target}%` }}
      />
    </div>
  );
}

export default function SkillGapPage() {
  const [priorityFilter, setPriorityFilter] = useState<PriorityFilter>("All");
  const [categoryFilter, setCategoryFilter] = useState("All categories");
  const { profile } = useCandidateProfile();
  const skills = profile.skills;
  const categories = Array.from(new Set(skills.map((skill) => skill.category)));
  const categoryCount = categories.length;
  const visibleSkills = skills.filter((skill) =>
    (priorityFilter === "All" || skill.priority === priorityFilter) &&
    (categoryFilter === "All categories" || skill.category === categoryFilter),
  );
  const summaryItems = [
    {
      label: "Skills assessed",
      value: skills.length,
      detail: `Across ${categoryCount} skill group${categoryCount === 1 ? "" : "s"}`,
      tone: "text-slate-900",
    },
    {
      label: "Meeting target",
      value: skills.filter((skill) => skill.current >= skill.target).length,
      detail: "At or above required level",
      tone: "text-emerald-700",
    },
    {
      label: "Needs improvement",
      value: skills.filter((skill) => skill.current < skill.target).length,
      detail: "Below the target level",
      tone: "text-indigo-700",
    },
    {
      label: "High-priority gaps",
      value: skills.filter((skill) => skill.current < skill.target && skill.priority === "High").length,
      detail: "Recommended focus areas",
      tone: "text-rose-700",
    },
  ];

  return (
    <div className="min-h-screen bg-background px-4 pb-8 pt-16 sm:px-6 md:py-8 lg:px-8">
      <div className="mx-auto max-w-[1440px]">
        <header className="mb-6 flex flex-col gap-4 border-b border-slate-200 pb-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="mb-1 text-sm font-semibold text-primary">Skill Analysis</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-900">Your skill gap</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
              Compare your current strengths with the levels your next career step calls for.
            </p>
          </div>
          <span className="inline-flex w-fit items-center gap-2 rounded-full border border-indigo-100 bg-white px-3 py-1.5 text-xs font-medium text-slate-500">
            <span className="h-2 w-2 rounded-full bg-indigo-500" />
            Sample profile data
          </span>
        </header>

        <section className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4" aria-label="Skill gap summary">
          {summaryItems.map((item) => (
            <div key={item.label} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_6px_18px_rgba(15,23,42,0.04)] sm:p-5">
              <p className="text-xs font-medium leading-5 text-slate-500 sm:text-sm">{item.label}</p>
              <p className={`mt-2 text-3xl font-bold tracking-tight ${item.tone}`}>{item.value}</p>
              <p className="mt-1 text-xs leading-5 text-slate-400">{item.detail}</p>
            </div>
          ))}
        </section>

        <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1.65fr)_minmax(300px,0.85fr)]">
          <section className="min-w-0 rounded-2xl border border-slate-200 bg-white p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_6px_18px_rgba(15,23,42,0.04)] sm:p-6">
            <div className="flex flex-col gap-4 border-b border-slate-100 pb-5 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">Skill comparisons</h2>
                <p className="mt-1 text-sm text-slate-500">Proficiency levels use a consistent 0–100 scale.</p>
              </div>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <label className="flex items-center gap-2 text-xs font-medium text-slate-500">
                  Category
                  <select
                    aria-label="Filter by category"
                    value={categoryFilter}
                    onChange={(event) => setCategoryFilter(event.target.value)}
                    className="max-w-[190px] rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
                  >
                    <option>All categories</option>
                    {categories.map((category) => <option key={category}>{category}</option>)}
                  </select>
                </label>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 py-4" aria-label="Filter by priority">
              {(["All", "High", "Medium", "Low"] as PriorityFilter[]).map((priority) => {
                const selected = priorityFilter === priority;
                return (
                  <button
                    key={priority}
                    type="button"
                    aria-pressed={selected}
                    onClick={() => setPriorityFilter(priority)}
                    className={`rounded-lg border px-3 py-1.5 text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300 ${selected ? "border-indigo-600 bg-indigo-600 text-white" : "border-slate-200 bg-white text-slate-600 hover:border-indigo-200 hover:bg-indigo-50"}`}
                  >
                    {priority === "All" ? "All priorities" : `${priority} priority`}
                  </button>
                );
              })}
              <span className="ml-auto text-xs text-slate-400" aria-live="polite">{visibleSkills.length} skills</span>
            </div>

            <div className="flex flex-wrap items-center gap-x-5 gap-y-2 py-4 text-xs text-slate-500" aria-label="Comparison legend">
              <span className="inline-flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-indigo-600" />Current</span>
              <span className="inline-flex items-center gap-2"><span className="h-3 w-0 border-l-2 border-dashed border-slate-700" />Required target</span>
              <span className="ml-auto text-slate-400">0 = foundational · 100 = advanced</span>
            </div>

            <div className="space-y-3">
              {visibleSkills.length > 0 ? visibleSkills.map((skill) => {
                const gap = Math.max(0, skill.target - skill.current);
                const meetsTarget = gap === 0;
                return (
                  <article key={skill.name} className="rounded-xl border border-slate-200 p-4 sm:p-5">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="font-semibold text-slate-900">{skill.name}</h3>
                          <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-500">{skill.category}</span>
                        </div>
                        <p className="mt-1 text-xs text-slate-500">
                          Current <span className="font-semibold text-slate-700">{skill.current}/100</span>
                          <span className="mx-2 text-slate-300">·</span>
                          Target <span className="font-semibold text-slate-700">{skill.target}/100</span>
                        </p>
                      </div>
                      <div className="flex flex-wrap items-center gap-2 sm:justify-end">
                        <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${meetsTarget ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-slate-200 bg-slate-50 text-slate-600"}`}>
                          {meetsTarget ? "Meets target" : `${gap} pt${gap === 1 ? "" : "s"} gap`}
                        </span>
                        <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${priorityStyles[skill.priority]}`}>
                          {skill.priority} priority
                        </span>
                      </div>
                    </div>

                    <SkillComparison current={skill.current} target={skill.target} name={skill.name} />
                    <div className="mt-2 flex justify-between text-[10px] tabular-nums text-slate-400" aria-hidden="true">
                      <span>0</span><span>25</span><span>50</span><span>75</span><span>100</span>
                    </div>
                  </article>
                );
              }) : (
                <p className="rounded-xl border border-dashed border-slate-300 px-4 py-8 text-center text-sm text-slate-500">
                  No skills match both filters. Choose another priority or category.
                </p>
              )}
            </div>
          </section>

          <aside className="space-y-5">
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_6px_18px_rgba(15,23,42,0.04)] sm:p-6">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.12em] text-rose-600">Start here</p>
                  <h2 className="mt-1 text-lg font-semibold text-slate-900">Recommended next steps</h2>
                </div>
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700" aria-hidden="true">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5"><path strokeLinecap="round" strokeLinejoin="round" d="M4 17.5 9 12l3.5 3.5L20 7.5M14.5 7.5H20V13" /></svg>
                </span>
              </div>
              <ol className="mt-5 space-y-5">
                {recommendations.map((item, index) => (
                  <li key={item.skill} className="flex gap-3">
                    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-xs font-bold text-slate-600">0{index + 1}</span>
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                        <h3 className="text-sm font-semibold text-slate-800">{item.skill}</h3>
                        <span className="text-[11px] text-slate-400">{item.duration}</span>
                      </div>
                      <p className="mt-1 text-xs leading-5 text-slate-500">{item.action}</p>
                    </div>
                  </li>
                ))}
              </ol>
              <Link href="/learning-roadmap" className="mt-6 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-primary px-4 py-3 text-sm font-semibold text-white transition hover:bg-primary-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300 focus-visible:ring-offset-2">
                Open learning roadmap <span aria-hidden="true">→</span>
              </Link>
              <Link href="/career-readiness" className="mt-3 inline-flex min-h-10 w-full items-center justify-center rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300">
                Review career readiness
              </Link>
            </section>

            <p className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-xs leading-5 text-slate-500">
              Sample data for demonstration only. Skill levels and targets are illustrative and are not based on a live resume analysis.
            </p>
          </aside>
        </div>
      </div>
    </div>
  );
}