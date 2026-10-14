
"use client";

import Link from "next/link";
import { useCandidateProfile } from "@/components/profile/CandidateProfileProvider";
import { getRoadmapPhases } from "@/components/profile/candidate-profile-state";
import { type RoadmapStatus } from "../data/sample-data";

const statusStyle: Record<RoadmapStatus, string> = {
  Completed: "border-emerald-200 bg-emerald-50 text-emerald-700",
  "In progress": "border-indigo-200 bg-indigo-50 text-indigo-700",
  Upcoming: "border-slate-200 bg-slate-100 text-slate-600",
};

export default function LearningRoadmapPage() {
  const { profile, completeRoadmapItem } = useCandidateProfile();
  const roadmapPhases = getRoadmapPhases(profile.roadmap);
  const items = roadmapPhases.flatMap((phase) => phase.items);
  const totalItems = items.length;
  const completedItems = items.filter((item) => item.status === "Completed").length;
  const overallProgress = totalItems === 0
    ? 0
    : Math.round(items.reduce((total, item) => total + item.progress, 0) / totalItems);

  return (
    <div className="min-h-screen bg-background px-4 pb-8 pt-16 sm:px-6 md:py-8 lg:px-8">
      <div className="mx-auto max-w-[1280px]">
        <header className="mb-6 flex flex-col gap-4 border-b border-slate-200 pb-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="mb-1 text-sm font-semibold text-primary">Personalized learning</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-900">Learning roadmap</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
              A practical sequence of skills and projects to help you move toward your target role.
            </p>
          </div>
          <span className="inline-flex w-fit items-center gap-2 rounded-full border border-indigo-100 bg-white px-3 py-1.5 text-xs font-medium text-slate-500">
            <span className="h-2 w-2 rounded-full bg-indigo-500" />
            Sample roadmap
          </span>
        </header>

        <section className="mb-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_6px_18px_rgba(15,23,42,0.04)] sm:p-6" aria-labelledby="roadmap-progress-heading">
          <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium text-slate-500">Overall learning progress</p>
              <h2 id="roadmap-progress-heading" className="mt-1 text-4xl font-bold tracking-tight text-slate-900">{overallProgress}<span className="text-2xl text-slate-400">%</span></h2>
              <p className="mt-2 text-sm text-slate-500">{completedItems} of {totalItems} learning items completed</p>
            </div>
            <div className="w-full sm:max-w-md">
              <div className="mb-2 flex justify-between text-xs font-medium text-slate-500"><span>Roadmap progress</span><span>{overallProgress}%</span></div>
              <div className="h-3 overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-label="Overall roadmap progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={overallProgress} aria-valuetext={`${overallProgress}% complete`}>
                <div className="h-full rounded-full bg-primary transition-[width]" style={{ width: `${overallProgress}%` }} />
              </div>
            </div>
          </div>
        </section>

        <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1.55fr)_minmax(280px,0.8fr)]">
          <section className="min-w-0" aria-labelledby="learning-path-heading">
            <div className="mb-4">
              <h2 id="learning-path-heading" className="text-lg font-semibold text-slate-900">Your learning path</h2>
              <p className="mt-1 text-sm text-slate-500">Four phases, from foundations to interview preparation.</p>
            </div>

            <div className="space-y-4">
              {roadmapPhases.length === 0 ? (
                <p className="rounded-xl border border-dashed border-slate-300 bg-white px-4 py-8 text-center text-sm text-slate-500">
                  No roadmap phases are available in this sample profile yet.
                </p>
              ) : roadmapPhases.map((phase) => {
                const phaseItems = phase.items.map((original) => items.find((item) => item.title === original.title) ?? original);
                const phaseComplete = phaseItems.every((item) => item.status === "Completed");
                const phaseActive = phaseItems.some((item) => item.status === "In progress");
                return (
                  <section key={phase.phase} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_6px_18px_rgba(15,23,42,0.04)] sm:p-5" aria-labelledby={`phase-${phase.phase}`}>
                    <div className="flex flex-wrap items-center gap-3 border-b border-slate-100 pb-4">
                      <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-xs font-bold ${phaseComplete ? "bg-emerald-100 text-emerald-700" : phaseActive ? "bg-indigo-100 text-indigo-700" : "bg-slate-100 text-slate-500"}`}>{phase.phase}</span>
                      <div className="min-w-0 flex-1">
                        <h3 id={`phase-${phase.phase}`} className="font-semibold text-slate-900">{phase.name}</h3>
                        <p className="mt-0.5 text-xs text-slate-500">{phase.timeframe}</p>
                      </div>
                      <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${statusStyle[phaseComplete ? "Completed" : phaseActive ? "In progress" : "Upcoming"]}`}>
                        {phaseComplete ? "Completed" : phaseActive ? "In progress" : "Upcoming"}
                      </span>
                    </div>

                    <ol className="divide-y divide-slate-100">
                      {phaseItems.map((item, index) => (
                        <li key={item.title} className="flex min-w-0 flex-col gap-3 py-4 last:pb-1 sm:flex-row sm:items-start">
                          <span className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold ${item.status === "Completed" ? "bg-emerald-100 text-emerald-700" : item.status === "In progress" ? "bg-indigo-100 text-indigo-700" : "bg-slate-100 text-slate-500"}`} aria-hidden="true">
                            {item.status === "Completed" ? "✓" : `${index + 1}`}
                          </span>
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                              <div className="min-w-0">
                                <h4 className="break-words text-sm font-semibold text-slate-800">{item.title}</h4>
                                <p className="mt-1 text-xs text-slate-500">Skill: {item.skill}<span className="mx-2 text-slate-300">·</span>{item.duration}</p>
                              </div>
                              <span className={`w-fit shrink-0 rounded-full border px-2.5 py-1 text-[11px] font-semibold ${statusStyle[item.status]}`}>{item.status}</span>
                            </div>
                            <div className="mt-3 flex items-center gap-3">
                              <div className="min-w-0 flex-1">
                                <div className="h-1.5 overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-label={`${item.title} progress`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={item.progress} aria-valuetext={`${item.progress}% complete`}>
                                  <div className={`h-full rounded-full ${item.status === "Completed" ? "bg-emerald-500" : "bg-indigo-600"}`} style={{ width: `${item.progress}%` }} />
                                </div>
                              </div>
                              <span className="w-9 text-right text-[11px] tabular-nums text-slate-500">{item.progress}%</span>
                              {item.status !== "Completed" && (
                                <button type="button" onClick={() => completeRoadmapItem(item.title)} className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-600 transition hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300" aria-label={`Mark ${item.title} complete`}>
                                  Mark done
                                </button>
                              )}
                            </div>
                          </div>
                        </li>
                      ))}
                    </ol>
                  </section>
                );
              })}
            </div>
          </section>

          <aside className="space-y-5">
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_6px_18px_rgba(15,23,42,0.04)] sm:p-6" aria-labelledby="focus-heading">
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-indigo-700">Suggested focus</p>
              <h2 id="focus-heading" className="mt-1 text-lg font-semibold text-slate-900">Keep the sequence practical</h2>
              <p className="mt-2 text-sm leading-6 text-slate-500">Finish your TypeScript and Next.js work, then apply it in a deployed project before moving into backend topics.</p>
              <div className="mt-5 rounded-xl bg-indigo-50 p-4">
                <p className="text-xs font-semibold text-indigo-800">Next suggested item</p>
                <p className="mt-1 text-sm font-semibold text-slate-900">Type-safe application features</p>
                <p className="mt-1 text-xs text-slate-500">TypeScript · about 5 hours</p>
              </div>
              <Link href="/career-assistant" className="mt-4 inline-flex min-h-10 w-full items-center justify-center rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300">
                Discuss your learning plan
              </Link>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_6px_18px_rgba(15,23,42,0.04)] sm:p-6" aria-labelledby="status-key-heading">
              <h2 id="status-key-heading" className="text-base font-semibold text-slate-900">Status guide</h2>
              <ul className="mt-4 space-y-3 text-sm">
                {(["Completed", "In progress", "Upcoming"] as RoadmapStatus[]).map((status) => (
                  <li key={status} className="flex items-center justify-between gap-3">
                    <span className="text-slate-600">{status}</span>
                    <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${statusStyle[status]}`}>{status}</span>
                  </li>
                ))}
              </ul>
            </section>

            <p className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-xs leading-5 text-slate-500">
              Illustrative sample roadmap. Progress and recommended learning items are mock data and are not connected to a live profile.
            </p>
          </aside>
        </div>
      </div>
    </div>
  );
}

const roadmap = [
  {
    step: "01",
    title: "Master React.js",
    description:
      "Strengthen your React fundamentals, hooks, state management, and component architecture.",
    duration: "2 weeks",
    progress: 65,
    status: "In Progress",
  },
  {
    step: "02",
    title: "Learn Next.js",
    description:
      "Build modern applications using routing, server components, API integration, and deployment.",
    duration: "2 weeks",
    progress: 30,
    status: "In Progress",
  },
  {
    step: "03",
    title: "Backend Development",
    description:
      "Learn REST APIs, authentication, databases, and backend application development.",
    duration: "3 weeks",
    progress: 0,
    status: "Upcoming",
  },
  {
    step: "04",
    title: "Interview Preparation",
    description:
      "Practice DSA, technical interviews, behavioral questions, and real-world problem solving.",
    duration: "2 weeks",
    progress: 0,
    status: "Upcoming",
  },
];
