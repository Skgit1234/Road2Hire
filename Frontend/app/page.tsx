"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/auth/AuthProvider";
import { getDashboard, getRecentActivity, type ActivityItem, type DashboardResponse } from "@/lib/api-client";
import { getPipelineCareerReadiness, getPipelineKnowledgeGraph, getPipelineLearningRoadmap, getSkillPriorities } from "@/lib/pipeline-api";
import type { CareerReadinessPredictionResponse, KnowledgeGraphResponse, PipelineLearningRoadmapResponse, SkillPriorityResponse } from "@/lib/pipeline-types";
import { mapLearningProgressChart, mapPriorityChart, mapSkillCoverageChart } from "@/lib/dashboard-visualization";

type DashboardData = {
  userId: number;
  summary: DashboardResponse;
  activity: ActivityItem[];
  readiness: CareerReadinessPredictionResponse | null;
  knowledgeGraph: KnowledgeGraphResponse | null;
  roadmap: PipelineLearningRoadmapResponse | null;
  priorities: SkillPriorityResponse | null;
  panelErrors: string[];
};

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <section className={`rounded-[18px] border border-slate-200 bg-white p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_6px_18px_rgba(15,23,42,0.04)] ${className}`}>{children}</section>;
}

function Empty({ children }: { children: React.ReactNode }) {
  return <p className="rounded-xl border border-dashed border-slate-300 px-3 py-5 text-center text-sm text-slate-500">{children}</p>;
}

function CountChart({ title, values, emptyMessage, showPercent = false }: { title: string; values: { label: string; count: number }[]; emptyMessage: string; showPercent?: boolean }) {
  const max = Math.max(0, ...values.map((item) => item.count));
  const total = values.reduce((sum, item) => sum + item.count, 0);
  const palette = ["bg-indigo-500", "bg-cyan-500", "bg-violet-500", "bg-orange-500", "bg-rose-500", "bg-teal-500"];
  const coverageTones: Record<string, string> = { "Matched skills": "bg-emerald-500", "Partially matched": "bg-amber-500", "Missing skills": "bg-rose-500" };
  return <Card className="p-5"><div className="mb-5 flex items-start justify-between gap-3"><div><h2 className="text-lg font-semibold text-slate-900">{title}</h2><p className="mt-1 text-xs text-slate-500">{showPercent && total > 0 ? `${total} skills in latest analysis` : "Saved roadmap priority distribution"}</p></div><span aria-hidden="true" className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-50 text-lg text-indigo-600">{showPercent ? "◉" : "▥"}</span></div>{values.length ? <figure aria-label={title} className="space-y-4">{values.map((item, index) => {
    const percent = total ? Math.round((item.count / total) * 100) : 0;
    const width = showPercent ? percent : max ? (item.count / max) * 100 : 0;
    const tone = showPercent ? coverageTones[item.label] ?? palette[index % palette.length] : palette[index % palette.length];
    return <div key={item.label}><div className="mb-1.5 flex items-center justify-between gap-3 text-sm"><span className="flex min-w-0 items-center gap-2 text-slate-700"><span className={`h-2.5 w-2.5 shrink-0 rounded-full ${tone}`} aria-hidden="true" /><span className="truncate">{item.label}</span></span><span className="shrink-0 font-semibold tabular-nums text-slate-900">{item.count}{showPercent ? ` · ${percent}%` : ""}</span></div><div className="h-3 overflow-hidden rounded-full bg-slate-100" role="img" aria-label={`${item.label}: ${item.count}${showPercent ? `, ${percent}%` : ""}`}><div className={`h-full rounded-full transition-[width] duration-500 ${tone}`} style={{ width: `${width}%` }} /></div></div>;
  })}</figure> : <Empty>{emptyMessage}</Empty>}</Card>;
}

function LearningProgressChart({ items }: { items: { label: string; status: string; progress: number }[] }) {
  return <div className="mt-4 border-t border-slate-100 pt-4"><div className="mb-3 flex flex-wrap items-center justify-between gap-2"><h3 className="text-sm font-semibold text-slate-800">Learning progress</h3><div className="flex gap-3 text-[11px] text-slate-500"><span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-indigo-500" />In progress</span><span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-emerald-500" />Completed</span></div></div>{items.length ? <ul className="space-y-4" aria-label="Learning progress chart">{items.slice(0, 6).map((item, index) => {
    const tone = item.status === "completed" ? "bg-emerald-500" : item.status === "in progress" ? "bg-indigo-500" : "bg-slate-400";
    return <li key={`${item.label}-${index}`}><div className="mb-1.5 flex items-center justify-between gap-2 text-xs"><span className="truncate font-medium text-slate-700">{item.label}</span><span className="shrink-0 capitalize text-slate-500">{item.status} · {item.progress}%</span></div><div className="h-3 overflow-hidden rounded-full bg-slate-100" role="img" aria-label={`${item.label}: ${item.progress}% complete, ${item.status}`}><div className={`h-full rounded-full transition-[width] duration-500 ${tone}`} style={{ width: `${item.progress}%` }} /></div></li>;
  })}</ul> : <Empty>No saved learning task progress is available.</Empty>}</div>;
}

function eventLabel(item: ActivityItem) {
  if (item.type === "resume_uploaded") return `Resume uploaded: ${item.resume_name}`;
  if (item.type === "skill_gap_analyzed") return `Skill gap analyzed${item.target_role ? ` for ${item.target_role}` : ""}${item.match_score === null ? " (match score unavailable)" : ` (${item.match_score}% match)`}`;
  return `Learning progress updated: ${item.skill_name} (${item.progress}%)`;
}

export default function Dashboard() {
  const { session, isRestoring } = useAuth();
  const [data, setData] = useState<DashboardData | null>(null);
  const [accountError, setAccountError] = useState<{ userId: number; message: string } | null>(null);
  const [retry, setRetry] = useState(0);

  const refresh = useCallback(() => {
    setData(null);
    setAccountError(null);
    setRetry((value) => value + 1);
  }, []);

  useEffect(() => {
    let active = true;
    if (!session) {
      return () => { active = false; };
    }
    const token = session.accessToken;
    const userId = session.profile.id;
    void Promise.allSettled([getDashboard(token), getRecentActivity(token)]).then(async ([summaryResult, activityResult]) => {
      if (!active) return;
      if (summaryResult.status === "rejected") {
        setAccountError({ userId, message: summaryResult.reason instanceof Error ? summaryResult.reason.message : "Could not load your account summary." });
        return;
      }
      const summary = summaryResult.value;
      const panelErrors: string[] = [];
      const activity = activityResult.status === "fulfilled" ? activityResult.value.items : [];
      if (activityResult.status === "rejected") panelErrors.push("Recent activity could not be loaded.");
      let readiness: CareerReadinessPredictionResponse | null = null;
      let knowledgeGraph: KnowledgeGraphResponse | null = null;
      let roadmap: PipelineLearningRoadmapResponse | null = null;
      let priorities: SkillPriorityResponse | null = null;
      const runId = summary.latest_skill_gap?.id;
      if (runId) {
        const [readinessResult, graphResult, roadmapResult, prioritiesResult] = await Promise.allSettled([
          getPipelineCareerReadiness(token, runId),
          getPipelineKnowledgeGraph(token, runId),
          getPipelineLearningRoadmap(token, runId),
          getSkillPriorities(token, runId),
        ]);
        if (!active) return;
        if (readinessResult.status === "fulfilled") readiness = readinessResult.value;
        else panelErrors.push("Career readiness is unavailable for this analysis.");
        if (graphResult.status === "fulfilled") knowledgeGraph = graphResult.value;
        else panelErrors.push("Skill coverage data is unavailable for this analysis.");
        if (roadmapResult.status === "fulfilled") roadmap = roadmapResult.value;
        else panelErrors.push("Learning recommendations are unavailable for this analysis.");
        if (prioritiesResult.status === "fulfilled") priorities = prioritiesResult.value;
        else panelErrors.push("Skill priorities are unavailable for this analysis.");
      }
      setData({ userId, summary, activity, readiness, knowledgeGraph, roadmap, priorities, panelErrors });
    }).catch((reason: unknown) => {
      if (!active) return;
      setAccountError({ userId, message: reason instanceof Error ? reason.message : "Could not load dashboard data." });
    });
    return () => { active = false; };
  }, [session, retry]);

  const owned = session && data?.userId === session.profile.id ? data : null;
  const error = session && accountError?.userId === session.profile.id ? accountError.message : "";
  const loading = Boolean(session && !owned && !error);
  const summary = owned?.summary;
  const roadmapItems = owned?.roadmap?.phases.flatMap((phase) => phase.items) ?? [];
  const skillCoverage = mapSkillCoverageChart(owned?.knowledgeGraph ?? null);
  const priorityCounts = mapPriorityChart(owned?.priorities ?? null);
  const learningProgress = mapLearningProgressChart(owned?.roadmap ?? null);
  const cards = summary ? [
    { title: "Saved resumes", value: String(summary.resume_count), note: "On your account" },
    { title: "Skill gap analyses", value: String(summary.skill_gap_count), note: "Saved pipeline runs" },
    { title: "Average skill match", value: summary.average_match_score === null ? "Unavailable" : `${summary.average_match_score}%`, note: "Across completed analyses" },
    { title: "Latest target role", value: summary.latest_skill_gap?.target_role ?? "No analysis yet", note: summary.latest_skill_gap ? (summary.latest_skill_gap.match_score === null ? "Match score unavailable" : `${summary.latest_skill_gap.match_score}% match`) : "Run a skill gap analysis to begin" },
  ] : [];

  return <div className="min-h-screen bg-background px-3 py-4 md:px-5 lg:px-6 xl:px-8">
    <div className="mx-auto max-w-[1520px]">
      <header className="mb-5 flex flex-col gap-3 pl-14 sm:flex-row sm:items-center sm:justify-between sm:pl-0">
        <div><h1 className="text-xl font-semibold text-slate-900">{session ? `Welcome, ${session.profile.name}` : "Welcome to Road2Hire"}</h1><p className="mt-1 text-sm text-slate-500">Your account data and saved career analysis</p></div>
        {session && <span className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-600 text-sm font-semibold text-white" role="img" aria-label={`Dashboard avatar: ${session.profile.name}`}>{session.profile.name.trim().split(/\s+/).map((part) => part[0]).slice(0, 2).join("").toUpperCase()}</span>}
      </header>

      {isRestoring && <p role="status" className="mb-4 rounded-xl border bg-white p-4 text-sm text-slate-600">Restoring your session…</p>}
      {!isRestoring && !session && <Card><p className="text-sm text-slate-700">Sign in to view your account dashboard.</p><Link href="/login" className="mt-2 inline-block font-semibold text-indigo-700 underline">Sign in</Link></Card>}
      {session && loading && <p role="status" className="mb-4 rounded-xl border bg-white p-4 text-sm text-slate-600">Loading your account dashboard…</p>}
      {session && error && <div role="alert" className="mb-4 rounded-xl border border-rose-200 bg-white p-4 text-sm text-rose-700"><p>{error}</p><button type="button" onClick={refresh} className="mt-3 rounded-lg border border-rose-300 px-3 py-2 font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-500">Retry dashboard</button></div>}

      {owned && <>
        <section className="mb-5 grid gap-4 sm:grid-cols-2 2xl:grid-cols-4" aria-label="Account summary">
          {cards.map((card, index) => <Card key={card.title} className="relative overflow-hidden p-5"><span className={`absolute inset-x-0 top-0 h-1 ${["bg-indigo-500", "bg-cyan-500", "bg-emerald-500", "bg-violet-500"][index]}`} aria-hidden="true" /><p className="text-sm font-medium text-slate-500">{card.title}</p><p className="mt-3 break-words text-3xl font-bold tracking-tight text-slate-900">{card.value}</p><p className="mt-1 text-sm text-slate-500">{card.note}</p></Card>)}
        </section>

        <section className="mb-5 grid gap-4 xl:grid-cols-3">
          <Card><h2 className="mb-3 text-lg font-semibold text-slate-900">Career readiness</h2>{owned.readiness ? <><p className="text-2xl font-bold capitalize text-indigo-700">{owned.readiness.predicted_class}</p><p className="mt-1 text-sm text-slate-500">Backend prediction for pipeline run #{owned.readiness.pipeline_run_id}</p>{owned.readiness.is_experimental && <p className="mt-2 text-xs text-amber-700">Experimental prediction</p>}</> : <Empty>{summary?.latest_skill_gap ? "Readiness prediction is not available for this analysis." : "Complete a skill gap analysis to see a readiness prediction."}</Empty>}</Card>
          <CountChart title="Skill coverage chart" values={skillCoverage} emptyMessage="Matched and missing skill data is not available for the latest analysis." showPercent />
          <Card><h2 className="mb-3 text-lg font-semibold text-slate-900">Career readiness trend</h2><Empty>Historical readiness data is not available yet.</Empty></Card>
        </section>

        <section className="mb-5 grid gap-4 xl:grid-cols-3">
          <Card><h2 className="mb-3 text-lg font-semibold text-slate-900">AI insights</h2><Empty>Account-specific AI insights are not available yet.</Empty><Link href="/career-assistant" className="mt-3 inline-block text-sm font-semibold text-indigo-700 underline">Open assistant</Link></Card>
          <Card><div className="mb-3 flex items-center justify-between gap-2"><h2 className="text-lg font-semibold text-slate-900">Recommended learning path</h2><Link href="/learning-roadmap" className="text-sm font-medium text-indigo-700 underline">Open roadmap</Link></div>{roadmapItems.length ? <p className="text-sm text-slate-500">Progress from saved learning tasks · run #{owned.roadmap?.pipeline_run_id}</p> : <Empty>{summary?.latest_skill_gap ? "No learning path items were returned for this analysis." : "A learning path is available after a completed skill gap analysis."}</Empty>}<LearningProgressChart items={learningProgress} /></Card>
          <CountChart title="Skill priority chart" values={priorityCounts} emptyMessage="No saved roadmap priority data is available for the latest analysis." />
        </section>

        <section className="mb-5 grid gap-4 xl:grid-cols-3">
          <Card><h2 className="mb-3 text-lg font-semibold text-slate-900">Resume score</h2><Empty>Resume scoring is not included in the current backend response.</Empty></Card>
          <Card><h2 className="mb-3 text-lg font-semibold text-slate-900">Interview readiness</h2><Empty>Interview readiness is not included in the current backend response.</Empty></Card>
          <Card><h2 className="mb-3 text-lg font-semibold text-slate-900">Learning streak</h2><Empty>Learning streak data is not available yet.</Empty></Card>
          <Card><h2 className="mb-3 text-lg font-semibold text-slate-900">Today&apos;s plan</h2><Empty>The backend provides saved roadmap tasks but no date-specific daily plan.</Empty></Card>
        </section>

        {owned.panelErrors.length > 0 && <div role="status" className="mb-4 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"><p>Some dashboard panels could not be loaded: {owned.panelErrors.join(" ")}</p><button type="button" onClick={refresh} className="mt-2 font-semibold underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-600">Retry unavailable panels</button></div>}
        <section className="grid gap-4 lg:grid-cols-2">
          <Card><h2 className="mb-3 text-lg font-semibold text-slate-900">Recent analysis</h2>{owned.summary.latest_skill_gap ? <div className="rounded-lg bg-slate-50 p-3"><p className="font-medium text-slate-800">{owned.summary.latest_skill_gap.target_role ?? "Target role unavailable"}</p><p className="mt-1 text-sm text-slate-500">{new Date(owned.summary.latest_skill_gap.created_at).toLocaleString()} · {owned.summary.latest_skill_gap.match_score === null ? "Match score unavailable" : `${owned.summary.latest_skill_gap.match_score}% match`}</p></div> : <Empty>No skill gap analysis has been saved.</Empty>}{owned.summary.latest_resume && <p className="mt-3 break-words text-sm text-slate-500">Latest resume: {owned.summary.latest_resume.original_name}</p>}</Card>
          <Card><h2 className="mb-3 text-lg font-semibold text-slate-900">Recent activity</h2>{owned.panelErrors.includes("Recent activity could not be loaded.") ? <Empty>Recent activity is unavailable. Use Retry unavailable panels above.</Empty> : owned.activity.length ? <ul className="space-y-2">{owned.activity.slice(0, 8).map((item) => <li key={`${item.type}-${item.id}`} className="flex flex-wrap justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2 text-sm"><span className="text-slate-700">{eventLabel(item)}</span><time className="text-xs text-slate-500" dateTime={item.timestamp}>{new Date(item.timestamp).toLocaleString()}</time></li>)}</ul> : <Empty>No account activity yet.</Empty>}</Card>
        </section>
      </>}
    </div>
  </div>;
}
