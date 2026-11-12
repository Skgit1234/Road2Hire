"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { type SkillPriority } from "../data/sample-data";
import { useCandidateProfile } from "@/components/profile/CandidateProfileProvider";
import { useAuth } from "@/components/auth/AuthProvider";
import { listResumes, type ResumeRecord } from "@/lib/api-client";
import { analyzeSkillGap } from "@/lib/pipeline-api";
import type { SkillGapAnalysisResponse } from "@/lib/pipeline-types";

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

function getRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function getStringField(value: unknown, key: string): string | null {
  const record = getRecord(value);
  return typeof record?.[key] === "string" ? record[key] as string : null;
}

function getRecordArray(value: unknown, key: string): Record<string, unknown>[] {
  const record = getRecord(value);
  const items = record?.[key];
  return Array.isArray(items)
    ? items.filter((item): item is Record<string, unknown> =>
        typeof item === "object" && item !== null && !Array.isArray(item))
    : [];
}

function getSkillLabel(item: Record<string, unknown>): string {
  const candidate = typeof item.candidate_skill === "string" ? item.candidate_skill : null;
  const target = typeof item.target_skill === "string" ? item.target_skill : null;
  const label = typeof item.skill_label === "string" ? item.skill_label : null;

  if (candidate && target && candidate !== target) return `${candidate} â†’ ${target}`;
  return candidate ?? target ?? label ?? "Skill detail unavailable";
}

function LiveSkillGapAnalysis() {
  const { session, isRestoring } = useAuth();
  const [resumes, setResumes] = useState<ResumeRecord[]>([]);
  const [resumeState, setResumeState] = useState<"loading" | "ready" | "error">("loading");
  const [resumeError, setResumeError] = useState("");
  const [selectedResumeId, setSelectedResumeId] = useState("");
  const [targetRole, setTargetRole] = useState("");
  const [autoSelectOccupation, setAutoSelectOccupation] = useState(false);
  const [requestState, setRequestState] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [result, setResult] = useState<SkillGapAnalysisResponse | null>(null);
  const [requestError, setRequestError] = useState("");
  const [validationError, setValidationError] = useState("");

  useEffect(() => {
    if (!session) return;
    let active = true;

    void Promise.resolve()
      .then(() => {
        if (!active) return undefined;
        setResumeState("loading");
        return listResumes(session.accessToken);
      })
      .then((items) => {
        if (active && items) {
          setResumes(items);
          setResumeState("ready");
          setResumeError("");
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setResumeState("error");
          setResumeError(error instanceof Error ? error.message : "Could not load saved resumes.");
        }
      });

    return () => { active = false; };
  }, [session]);

  function clearResult() {
    setResult(null);
    setRequestError("");
    setValidationError("");
    setRequestState("idle");
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setValidationError("");
    setRequestError("");
    setResult(null);

    if (!selectedResumeId) {
      setValidationError("Choose one of your saved resumes.");
      return;
    }

    if (!autoSelectOccupation && !targetRole.trim()) {
      setValidationError("Enter a target occupation or enable automatic occupation selection.");
      return;
    }

    if (!session) return;

    setRequestState("loading");

    try {
      const details = autoSelectOccupation
        ? { resume_id: Number(selectedResumeId), auto_select_top_occupation: true }
        : { resume_id: Number(selectedResumeId), target_occupation: targetRole.trim() };

      const response = await analyzeSkillGap(session.accessToken, details);
      setResult(response);
      setRequestState("success");
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "Could not run skill-gap analysis.");
      setRequestState("error");
    }
  }

  const gap = result?.skill_gap;
  const matchedSkills = getRecordArray(gap, "matched_skills");
  const partialSkills = getRecordArray(gap, "partially_matched_skills");
  const missingEssential = getRecordArray(gap, "missing_essential_skills");
  const missingOptional = getRecordArray(gap, "missing_optional_skills");
  const occupationLabel = getStringField(result?.target_occupation, "occupation_label");

  return (
    <section className="mb-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6" aria-labelledby="live-skill-gap-heading">
      <div className="mb-4">
        <p className="text-sm font-semibold text-primary">Backend analysis</p>
        <h2 id="live-skill-gap-heading" className="mt-1 text-xl font-bold text-slate-900">Run a live skill-gap analysis</h2>
        <p className="mt-1 text-sm leading-6 text-slate-500">
          Select a saved resume and a target occupation. The unified AI pipeline compares your skills against ESCO occupation requirements.
        </p>
      </div>

      {isRestoring ? (
        <p className="text-sm text-slate-600" role="status">Restoring your session…</p>
      ) : !session ? (
        <p className="text-sm text-amber-800" role="status">
          Sign in to run analysis. <Link className="font-semibold underline" href="/login">Go to sign in</Link>
        </p>
      ) : resumeState === "loading" ? (
        <p className="text-sm text-slate-600" role="status">Loading your saved resumesâ€¦</p>
      ) : resumeState === "error" ? (
        <p className="text-sm text-rose-800" role="alert">{resumeError}</p>
      ) : resumes.length === 0 ? (
        <p className="text-sm text-slate-600" role="status">Upload a resume before running skill-gap analysis.</p>
      ) : (
        <form onSubmit={submit} className="grid gap-4 md:grid-cols-2">
          <label className="text-sm font-medium text-slate-700">
            Saved resume
            <select
              required
              value={selectedResumeId}
              onChange={(event) => { setSelectedResumeId(event.target.value); clearResult(); }}
              className="mt-1 min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3"
            >
              <option value="">Choose a resume</option>
              {resumes.map((resume) => (
                <option key={resume.id} value={resume.id}>{resume.original_name}</option>
              ))}
            </select>
          </label>

          <label className="text-sm font-medium text-slate-700">
            Target occupation
            <input
              value={targetRole}
              onChange={(event) => { setTargetRole(event.target.value); clearResult(); }}
              disabled={autoSelectOccupation}
              maxLength={512}
              placeholder="e.g. Software Developer"
              className="mt-1 min-h-11 w-full rounded-lg border border-slate-300 px-3 disabled:bg-slate-100"
            />
          </label>

          <label className="flex items-start gap-2 text-sm text-slate-700 md:col-span-2">
            <input
              type="checkbox"
              checked={autoSelectOccupation}
              onChange={(event) => { setAutoSelectOccupation(event.target.checked); clearResult(); }}
              className="mt-1"
            />
            <span>
              Automatically select the top suggested occupation from my resume
              <span className="mt-1 block text-xs text-slate-500">
                When enabled, the target occupation field is ignored.
              </span>
            </span>
          </label>

          {validationError && (
            <p className="text-sm text-rose-800 md:col-span-2" role="alert">{validationError}</p>
          )}

          <button
            type="submit"
            disabled={requestState === "loading"}
            className="min-h-11 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary-dark disabled:cursor-wait disabled:opacity-60 md:col-span-2"
          >
            {requestState === "loading" ? "Analyzingâ€¦" : "Run AI analysis"}
          </button>
        </form>
      )}

      {requestState === "loading" && (
        <p className="mt-4 text-sm text-slate-600" role="status">Running the unified AI pipelineâ€¦</p>
      )}

      {requestState === "error" && (
        <p className="mt-4 text-sm text-rose-800" role="alert">{requestError}</p>
      )}

      {requestState === "success" && result && (
        <div className="mt-5 border-t border-slate-100 pt-5" aria-live="polite">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="font-semibold text-slate-900">
                {occupationLabel ?? "Skill-gap analysis result"}
              </h3>
              <p className="mt-1 text-xs text-slate-500">
                Resume #{selectedResumeId} Â· Pipeline run #{result.pipeline_run_id}
              </p>
            </div>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-sm font-semibold capitalize text-slate-700">
              {result.status}
            </span>
          </div>

          <p className="mt-3 text-sm leading-6 text-slate-600">{result.matching_basis}</p>

          {result.warnings.length > 0 && (
            <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4">
              <h4 className="font-semibold text-amber-900">Pipeline warnings</h4>
              <ul className="mt-2 list-inside list-disc text-sm text-amber-900">
                {result.warnings.map((warning, index) => <li key={`${index}-${warning}`}>{warning}</li>)}
              </ul>
            </div>
          )}

          {result.error && (
            <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-4">
              <h4 className="font-semibold text-rose-900">Analysis error</h4>
              <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-xs text-rose-900">
                {JSON.stringify(result.error, null, 2)}
              </pre>
            </div>
          )}

          {result.status === "completed" && gap && (
            <>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
                  <h4 className="font-semibold text-emerald-900">Matched skills ({matchedSkills.length})</h4>
                  {matchedSkills.length > 0 ? (
                    <ul className="mt-2 list-inside list-disc text-sm text-emerald-900">
                      {matchedSkills.map((item, index) => <li key={`${index}-${getSkillLabel(item)}`}>{getSkillLabel(item)}</li>)}
                    </ul>
                  ) : <p className="mt-2 text-sm text-emerald-800">No matched skills were returned.</p>}
                </div>

                <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
                  <h4 className="font-semibold text-blue-900">Partially matched ({partialSkills.length})</h4>
                  {partialSkills.length > 0 ? (
                    <ul className="mt-2 list-inside list-disc text-sm text-blue-900">
                      {partialSkills.map((item, index) => <li key={`${index}-${getSkillLabel(item)}`}>{getSkillLabel(item)}</li>)}
                    </ul>
                  ) : <p className="mt-2 text-sm text-blue-800">No partially matched skills were returned.</p>}
                </div>

                <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
                  <h4 className="font-semibold text-amber-900">Missing essential skills ({missingEssential.length})</h4>
                  {missingEssential.length > 0 ? (
                    <ul className="mt-2 list-inside list-disc text-sm text-amber-900">
                      {missingEssential.map((item, index) => <li key={`${index}-${getSkillLabel(item)}`}>{getSkillLabel(item)}</li>)}
                    </ul>
                  ) : <p className="mt-2 text-sm text-amber-800">No missing essential skills were returned.</p>}
                </div>

                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <h4 className="font-semibold text-slate-900">Missing optional skills ({missingOptional.length})</h4>
                  {missingOptional.length > 0 ? (
                    <ul className="mt-2 list-inside list-disc text-sm text-slate-700">
                      {missingOptional.map((item, index) => <li key={`${index}-${getSkillLabel(item)}`}>{getSkillLabel(item)}</li>)}
                    </ul>
                  ) : <p className="mt-2 text-sm text-slate-600">No missing optional skills were returned.</p>}
                </div>
              </div>

              <details className="mt-4 rounded-xl border border-slate-200 p-4">
                <summary className="cursor-pointer text-sm font-semibold text-slate-700">
                  View detailed skill-gap data
                </summary>
                <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap break-words text-xs text-slate-600">
                  {JSON.stringify(gap, null, 2)}
                </pre>
              </details>
            </>
          )}

          {result.status !== "completed" && !result.error && (
            <p className="mt-3 text-sm text-slate-600">
              The pipeline has not returned a completed analysis. You can inspect the run status above.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
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

      <LiveSkillGapAnalysis />

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
                <p className="mt-1 text-sm text-slate-500">Proficiency levels use a consistent 0Ã¢â‚¬â€œ100 scale.</p>
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
              <span className="ml-auto text-slate-400">0 = foundational Ã‚Â· 100 = advanced</span>
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
                          <span className="mx-2 text-slate-300">Ã‚Â·</span>
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
                Open learning roadmap <span aria-hidden="true">Ã¢â€ â€™</span>
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
