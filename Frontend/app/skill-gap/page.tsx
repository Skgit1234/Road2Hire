"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { useAuth } from "@/components/auth/AuthProvider";
import { listResumes, type ResumeRecord } from "@/lib/api-client";
import {
  analyzeSkillGap,
  getPipelineKnowledgeGraph,
  getSkillPriorities,
} from "@/lib/pipeline-api";
import type {
  KnowledgeGraphResponse,
  PipelineSkillGapData,
  SkillGapAnalysisResponse,
  SkillPriorityResponse,
} from "@/lib/pipeline-types";

type SkillRecord = Record<string, unknown>;
type PanelState = "idle" | "loading" | "ready" | "error";

function recordArray(value: unknown, key: string): SkillRecord[] {
  if (typeof value !== "object" || value === null) return [];
  const items = (value as Record<string, unknown>)[key];
  return Array.isArray(items)
    ? items.filter((item): item is SkillRecord => typeof item === "object" && item !== null && !Array.isArray(item))
    : [];
}

function skillName(item: SkillRecord): string {
  return [item.candidate_skill, item.target_skill, item.occupation_skill, item.skill_label, item.skill_name]
    .find((value): value is string => typeof value === "string" && value.trim().length > 0) ?? "Skill name unavailable";
}

function asScore(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 1 ? value : null;
}

function percent(value: unknown): string {
  const score = asScore(value);
  return score === null ? "Unavailable" : `${Math.round(score * 100)}%`;
}

function CoverageCard({ title, value, tone }: { title: string; value: unknown; tone: string }) {
  const score = asScore(value);
  const barColor = tone === "text-emerald-700" ? "#047857" : tone === "text-amber-700" ? "#b45309" : "#4338ca";
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
      <h3 className="text-sm font-medium text-slate-500">{title}</h3>
      <p className={`mt-2 text-3xl font-bold tabular-nums ${tone}`}>{percent(value)}</p>
      {score !== null ? (
        <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100" role="img" aria-label={`${title}: ${Math.round(score * 100)} percent`}>
          <div className="h-full rounded-full" style={{ width: `${score * 100}%`, backgroundColor: barColor }} />
        </div>
      ) : <p className="mt-3 text-xs text-slate-400">No score was returned for this analysis.</p>}
    </article>
  );
}

function SkillList({ title, items, tone }: { title: string; items: SkillRecord[]; tone: string }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-semibold text-slate-900">{title}</h3>
        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${tone}`}>{items.length}</span>
      </div>
      {items.length ? (
        <ul className="mt-3 space-y-2">
          {items.map((item, index) => {
            const candidate = typeof item.candidate_skill === "string" ? item.candidate_skill : null;
            const target = typeof item.target_skill === "string" ? item.target_skill : typeof item.occupation_skill === "string" ? item.occupation_skill : null;
            const label = candidate && target && candidate !== target ? `${candidate} → ${target}` : skillName(item);
            const detail = typeof item.explanation === "string" ? item.explanation : typeof item.graph_relationship === "string" ? item.graph_relationship.replaceAll("_", " ") : null;
            return <li key={`${label}-${index}`} className="rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-800">
              <span>{label}</span>{detail && <span className="mt-1 block text-xs text-slate-500">{detail}</span>}
            </li>;
          })}
        </ul>
      ) : <p className="mt-3 text-sm text-slate-500">No {title.toLowerCase()} were returned.</p>}
    </section>
  );
}

type GraphNode = Record<string, unknown> & { id: string; label: string; kind: string };
type GraphEdge = Record<string, unknown> & { source: string; target: string; type: string };

function SkillGraph({ graph }: { graph: KnowledgeGraphResponse }) {
  const nodes = graph.nodes.filter((item): item is GraphNode =>
    typeof item.id === "string" && typeof item.label === "string" && typeof item.kind === "string");
  const nodeIds = new Set(nodes.map((node) => node.id));
  const edges = graph.relationships.filter((item): item is GraphEdge =>
    typeof item.source === "string" && typeof item.target === "string" && typeof item.type === "string" && nodeIds.has(item.source) && nodeIds.has(item.target));
  const positions = new Map<string, { x: number; y: number }>();
  const columns = Math.max(1, Math.min(4, Math.ceil(Math.sqrt(nodes.length || 1))));
  const cellWidth = 220;
  const cellHeight = 108;
  const width = Math.max(300, columns * cellWidth + 40);
  const rows = Math.ceil(nodes.length / columns);
  const height = Math.max(160, rows * cellHeight + 30);
  nodes.forEach((node, index) => positions.set(node.id, {
    x: 110 + (index % columns) * cellWidth,
    y: 52 + Math.floor(index / columns) * cellHeight,
  }));
  const statusByNode = new Map<string, "matched" | "partial" | "missing" | "neutral">();
  nodes.forEach((node) => statusByNode.set(node.id, node.gap_status === "missing" ? "missing" : "neutral"));
  edges.forEach((edge) => {
    const status = edge.type === "matches_skill" ? "matched" : "partial";
    if (nodeIds.has(edge.source)) statusByNode.set(edge.source, status);
    if (nodeIds.has(edge.target) && statusByNode.get(edge.target) !== "matched") statusByNode.set(edge.target, status);
  });
  const selectedDefault = nodes.find((node) => statusByNode.get(node.id) === "missing") ?? nodes[0] ?? null;
  const [selected, setSelected] = useState<GraphNode | null>(selectedDefault);
  const nodeColors = {
    matched: "#dcfce7",
    partial: "#fef3c7",
    missing: "#ffe4e6",
    neutral: "#e2e8f0",
  };
  const edgeColors = { matches_skill: "#059669", partially_matches_skill: "#d97706" };

  if (nodes.length === 0) return <p className="mt-4 rounded-xl border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500">No graph nodes were returned for this analysis.</p>;

  return <div className="mt-4">
    <div className="mb-3 flex flex-wrap gap-x-4 gap-y-2 text-xs text-slate-600" aria-label="Graph legend">
      {([["#059669", "Matched relationship"], ["#d97706", "Partial relationship"], ["#be123c", "Missing skill"], ["#64748b", "Other node"]] as const).map(([color, label]) => <span key={label} className="inline-flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: color }} />{label}</span>)}
    </div>
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500" role="region" aria-label="Interactive skill relationship graph" tabIndex={0}>
      <div className="relative" role="group" aria-label={`Skill graph with ${nodes.length} nodes and ${edges.length} relationships`} style={{ width, height }}>
      <svg viewBox={`0 0 ${width} ${height}`} className="pointer-events-none absolute inset-0" style={{ width, height }} aria-hidden="true" focusable="false">
        <defs><marker id="skill-graph-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#64748b" /></marker></defs>
        {edges.map((edge, index) => {
          const source = positions.get(edge.source); const target = positions.get(edge.target);
          if (!source || !target) return null;
          const color = edgeColors[edge.type as keyof typeof edgeColors] ?? "#64748b";
          return <g key={`${edge.source}-${edge.target}-${index}`}>
            <line x1={source.x} y1={source.y + 25} x2={target.x} y2={target.y - 25} stroke={color} strokeWidth="2.5" markerEnd="url(#skill-graph-arrow)" />
            <text x={(source.x + target.x) / 2} y={(source.y + target.y) / 2} textAnchor="middle" className="fill-slate-600" fontSize="10">{edge.type.replaceAll("_", " ")}</text>
          </g>;
        })}
      </svg>
      <ul className="sr-only" aria-label="Skill graph relationships">{edges.map((edge, index) => <li key={`${edge.source}-${edge.target}-${index}`}>{nodes.find((node) => node.id === edge.source)?.label} {edge.type.replaceAll("_", " ")} {nodes.find((node) => node.id === edge.target)?.label}{typeof edge.explanation === "string" ? `: ${edge.explanation}` : ""}</li>)}</ul>
      {nodes.map((node) => {
        const point = positions.get(node.id)!;
        const status = statusByNode.get(node.id) ?? "neutral";
        return <button key={node.id} type="button" aria-label={`${node.label}, ${status} ${node.kind.replaceAll("_", " ")}`} aria-pressed={selected?.id === node.id} onClick={() => setSelected(node)} className="absolute flex h-[52px] w-[176px] -translate-x-1/2 -translate-y-1/2 flex-col items-center justify-center rounded-xl border px-2 text-center text-xs font-semibold text-slate-900 shadow-sm focus-visible:z-10 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-indigo-500 focus-visible:ring-offset-2" style={{ left: point.x, top: point.y, backgroundColor: nodeColors[status], borderColor: selected?.id === node.id ? "#4f46e5" : "#cbd5e1" }}>
          <span className="max-w-full truncate">{node.label}</span>
          <span className="text-[10px] font-normal text-slate-600">{status} · {node.kind.replaceAll("_", " ")}</span>
        </button>;
      })}
      </div>
    </div>
    {selected && <p className="mt-3 rounded-lg bg-indigo-50 px-3 py-2 text-sm text-indigo-950" aria-live="polite"><strong>{selected.label}</strong> · {statusByNode.get(selected.id)} · {selected.kind.replaceAll("_", " ")}</p>}
    <p className="mt-3 text-xs leading-5 text-slate-500">{graph.scope}</p>
  </div>;
}

function Priorities({ state, data, error, onRetry }: { state: PanelState; data: SkillPriorityResponse | null; error: string; onRetry: () => void }) {
  const [priorityFilter, setPriorityFilter] = useState("All");
  const [categoryFilter, setCategoryFilter] = useState("All");
  const priorities = [...new Set((data?.items ?? []).flatMap((item) => typeof item.priority === "string" && item.priority.trim() ? [item.priority.trim()] : []))];
  const categories = [...new Set((data?.items ?? []).flatMap((item) => typeof item.phase_name === "string" && item.phase_name.trim() ? [item.phase_name.trim()] : []))];
  const filteredItems = (data?.items ?? []).filter((item) =>
    (priorityFilter === "All" || item.priority === priorityFilter) &&
    (categoryFilter === "All" || item.phase_name === categoryFilter));
  return <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5" aria-labelledby="priority-heading">
    <h2 id="priority-heading" className="font-semibold text-slate-900">Skill priorities</h2>
    {state === "loading" && <p className="mt-3 text-sm text-slate-500" role="status">Loading skill priorities…</p>}
    {state === "error" && <div className="mt-3 text-sm text-rose-800" role="alert"><p>{error}</p><button onClick={onRetry} className="mt-2 rounded-lg border border-rose-300 px-3 py-1.5 font-semibold">Retry priorities</button></div>}
    {state === "ready" && data && (data.items.length ? <>
      <div className="mt-3 space-y-3">
        {priorities.length > 0 && <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by priority">
          <button type="button" aria-pressed={priorityFilter === "All"} onClick={() => setPriorityFilter("All")} className="rounded-full border border-slate-200 px-3 py-1.5 text-xs font-semibold capitalize text-slate-700 aria-pressed:border-indigo-300 aria-pressed:bg-indigo-50 aria-pressed:text-indigo-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400">All priorities</button>
          {priorities.map((priority) => <button key={priority} type="button" aria-pressed={priorityFilter === priority} onClick={() => setPriorityFilter(priority)} className="rounded-full border border-slate-200 px-3 py-1.5 text-xs font-semibold capitalize text-slate-700 aria-pressed:border-indigo-300 aria-pressed:bg-indigo-50 aria-pressed:text-indigo-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400">{priority} priority</button>)}
        </div>}
        {categories.length > 0 && <label className="block text-xs font-medium text-slate-600">Filter by category<select aria-label="Filter by category" value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)} className="mt-1 min-h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm"><option value="All">All categories</option>{categories.map((category) => <option key={category} value={category}>{category}</option>)}</select></label>}
      </div>
      <p className="mt-3 text-xs text-slate-500">{filteredItems.length} {filteredItems.length === 1 ? "skill" : "skills"}</p>
      {filteredItems.length ? <ol className="mt-3 space-y-3">{filteredItems.map((item, index) => {
      const name = typeof item.skill_name === "string" ? item.skill_name : typeof item.skill_label === "string" ? item.skill_label : "Skill name unavailable";
      const priority = typeof item.priority === "string" ? item.priority : "Priority unavailable";
      const reason = typeof item.importance_rationale === "string" ? item.importance_rationale : typeof item.learning_outcome === "string" ? item.learning_outcome : null;
      const phase = typeof item.phase_name === "string" ? item.phase_name : typeof item.phase_number === "number" ? `Phase ${item.phase_number}` : null;
      return <li key={`${name}-${index}`} className="rounded-xl border border-slate-100 p-3">
        <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="text-sm font-semibold text-slate-800">{name}</h3><span className="rounded-full bg-indigo-50 px-2 py-1 text-xs font-semibold capitalize text-indigo-700">{priority}</span></div>
        {(phase || reason) && <p className="mt-1 text-xs leading-5 text-slate-500">{[phase, reason].filter(Boolean).join(" · ")}</p>}
      </li>;
      })}</ol> : <p className="mt-3 text-sm text-slate-500">No skills match both filters.</p>}
    </> : <p className="mt-3 text-sm text-slate-500">No priority items were returned for this analysis.</p>)}
  </section>;
}

function AnalysisResults({ result, prioritiesState, priorities, prioritiesError, retryPriorities, graphState, graph, graphError, retryGraph }: {
  result: SkillGapAnalysisResponse;
  prioritiesState: PanelState;
  priorities: SkillPriorityResponse | null;
  prioritiesError: string;
  retryPriorities: () => void;
  graphState: PanelState;
  graph: KnowledgeGraphResponse | null;
  graphError: string;
  retryGraph: () => void;
}) {
  const gap = result.skill_gap as PipelineSkillGapData | null;
  const occupation = result.target_occupation?.occupation_label;
  const title = typeof occupation === "string" ? occupation : "Skill-gap analysis";
  const matched = recordArray(gap, "matched_skills");
  const partial = recordArray(gap, "partially_matched_skills");
  const missingEssential = recordArray(gap, "missing_essential_skills");
  const missingOptional = recordArray(gap, "missing_optional_skills");

  return <div className="mt-6 space-y-6" aria-live="polite">
    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 pb-4">
      <div><h2 className="text-xl font-bold text-slate-900">{title}</h2><p className="mt-1 text-xs text-slate-500">Pipeline run #{result.pipeline_run_id}</p></div>
      <span className="rounded-full bg-slate-100 px-3 py-1 text-sm font-semibold capitalize text-slate-700">{result.status}</span>
    </div>
    <p className="text-sm leading-6 text-slate-600">{result.matching_basis}</p>
    {result.warnings.length > 0 && <div className="rounded-xl border border-amber-200 bg-amber-50 p-4"><h3 className="font-semibold text-amber-900">Analysis warnings</h3><ul className="mt-2 list-inside list-disc text-sm text-amber-900">{result.warnings.map((warning, index) => <li key={`${index}-${warning}`}>{warning}</li>)}</ul></div>}
    {result.error && <p className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900" role="alert">{typeof result.error.message === "string" ? result.error.message : "The pipeline returned an analysis error."}</p>}
    {result.status === "completed" && gap ? <>
      <section aria-label="Skill coverage scores" className="grid gap-3 sm:grid-cols-3">
        <CoverageCard title="Overall skill coverage" value={gap.overall_skill_coverage_score} tone="text-indigo-700" />
        <CoverageCard title="Essential skill coverage" value={gap.essential_skill_coverage_score} tone="text-emerald-700" />
        <CoverageCard title="Optional skill coverage" value={gap.optional_skill_coverage_score} tone="text-amber-700" />
      </section>
      <section aria-label="Skill match breakdown" className="grid gap-3 sm:grid-cols-2">
        <SkillList title="Matched skills" items={matched} tone="bg-emerald-100 text-emerald-800" />
        <SkillList title="Partially matched skills" items={partial} tone="bg-amber-100 text-amber-800" />
        <SkillList title="Missing essential skills" items={missingEssential} tone="bg-rose-100 text-rose-800" />
        <SkillList title="Missing optional skills" items={missingOptional} tone="bg-slate-100 text-slate-700" />
      </section>
      <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,1.5fr)_minmax(280px,0.8fr)]">
        <section className="min-w-0 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5" aria-labelledby="graph-heading">
          <h2 id="graph-heading" className="font-semibold text-slate-900">Knowledge graph</h2>
          {graphState === "loading" && <p className="mt-4 text-sm text-slate-500" role="status">Loading knowledge graph…</p>}
          {graphState === "error" && <div className="mt-4 text-sm text-rose-800" role="alert"><p>{graphError}</p><button onClick={retryGraph} className="mt-2 rounded-lg border border-rose-300 px-3 py-1.5 font-semibold">Retry graph</button></div>}
          {graphState === "ready" && graph && <SkillGraph key={graph.pipeline_run_id} graph={graph} />}
        </section>
        <Priorities key={priorities?.pipeline_run_id ?? result.pipeline_run_id} state={prioritiesState} data={priorities} error={prioritiesError} onRetry={retryPriorities} />
      </div>
    </> : result.status === "completed" ? <p className="rounded-xl border border-dashed border-slate-300 p-6 text-sm text-slate-500">This analysis completed without skill-gap details.</p> : <p className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">The pipeline has not returned a completed analysis yet.</p>}
  </div>;
}

export default function SkillGapPage() {
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
  const [prioritiesState, setPrioritiesState] = useState<PanelState>("idle");
  const [priorities, setPriorities] = useState<SkillPriorityResponse | null>(null);
  const [prioritiesError, setPrioritiesError] = useState("");
  const [graphState, setGraphState] = useState<PanelState>("idle");
  const [graph, setGraph] = useState<KnowledgeGraphResponse | null>(null);
  const [graphError, setGraphError] = useState("");
  const activeRunIdRef = useRef<number | null>(null);
  const analysisRequestRef = useRef(0);
  const prioritiesRequestRef = useRef(0);
  const graphRequestRef = useRef(0);

  useEffect(() => {
    let active = true;
    void Promise.resolve().then(() => {
      if (!active) return undefined;
      setResumes([]);
      setResumeState("loading");
      setResumeError("");
      setSelectedResumeId("");
      activeRunIdRef.current = null;
      analysisRequestRef.current += 1;
      prioritiesRequestRef.current += 1;
      graphRequestRef.current += 1;
      setResult(null);
      setRequestError("");
      setRequestState("idle");
      setPriorities(null);
      setPrioritiesError("");
      setPrioritiesState("idle");
      setGraph(null);
      setGraphError("");
      setGraphState("idle");
      if (!session) return undefined;
      return listResumes(session.accessToken);
    }).then((items) => {
      if (active && items) { setResumes(items); setResumeState("ready"); setResumeError(""); }
    }).catch((error: unknown) => {
      if (active) { setResumeState("error"); setResumeError(error instanceof Error ? error.message : "Could not load saved resumes."); }
    });
    return () => { active = false; };
  }, [session]);

  function clearResult() {
    activeRunIdRef.current = null;
    analysisRequestRef.current += 1;
    prioritiesRequestRef.current += 1;
    graphRequestRef.current += 1;
    setResult(null); setRequestError(""); setValidationError(""); setRequestState("idle");
    setPriorities(null); setPrioritiesState("idle"); setPrioritiesError("");
    setGraph(null); setGraphState("idle"); setGraphError("");
  }

  const loadPriorities = useMemo(() => async (runId: number, token: string) => {
    const requestId = ++prioritiesRequestRef.current;
    setPrioritiesState("loading"); setPrioritiesError("");
    try {
      const response = await getSkillPriorities(token, runId);
      if (activeRunIdRef.current !== runId || prioritiesRequestRef.current !== requestId) return;
      if (response.pipeline_run_id !== runId) throw new Error("The API returned priorities for a different analysis.");
      setPriorities(response);
      setPrioritiesState("ready");
    } catch (error) {
      if (activeRunIdRef.current !== runId || prioritiesRequestRef.current !== requestId) return;
      setPrioritiesError(error instanceof Error ? error.message : "Could not load skill priorities.");
      setPrioritiesState("error");
    }
  }, []);
  const loadGraph = useMemo(() => async (runId: number, token: string) => {
    const requestId = ++graphRequestRef.current;
    setGraphState("loading"); setGraphError("");
    try {
      const response = await getPipelineKnowledgeGraph(token, runId);
      if (activeRunIdRef.current !== runId || graphRequestRef.current !== requestId) return;
      if (response.pipeline_run_id !== runId) throw new Error("The API returned a graph for a different analysis.");
      setGraph(response);
      setGraphState("ready");
    } catch (error) {
      if (activeRunIdRef.current !== runId || graphRequestRef.current !== requestId) return;
      setGraphError(error instanceof Error ? error.message : "Could not load the knowledge graph.");
      setGraphState("error");
    }
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setValidationError(""); setRequestError(""); clearResult();
    if (!selectedResumeId) { setValidationError("Choose one of your saved resumes."); return; }
    if (!autoSelectOccupation && !targetRole.trim()) { setValidationError("Enter a target occupation or enable automatic occupation selection."); return; }
    if (!session) return;
    const requestId = ++analysisRequestRef.current;
    setRequestState("loading");
    try {
      const details = autoSelectOccupation
        ? { resume_id: Number(selectedResumeId), auto_select_top_occupation: true }
        : { resume_id: Number(selectedResumeId), target_occupation: targetRole.trim() };
      const response = await analyzeSkillGap(session.accessToken, details);
      if (analysisRequestRef.current !== requestId) return;
      activeRunIdRef.current = response.status === "completed" ? response.pipeline_run_id : null;
      setResult(response); setRequestState("success");
      if (response.status === "completed") {
        void loadPriorities(response.pipeline_run_id, session.accessToken);
        void loadGraph(response.pipeline_run_id, session.accessToken);
      }
    } catch (error) {
      if (analysisRequestRef.current !== requestId) return;
      setRequestError(error instanceof Error ? error.message : "Could not run skill-gap analysis."); setRequestState("error");
    }
  }

  return <div className="min-h-screen bg-background px-4 pb-10 pt-16 sm:px-6 md:py-8 lg:px-8">
    <div className="mx-auto max-w-[1440px]">
      <header className="mb-6 border-b border-slate-200 pb-6">
        <p className="mb-1 text-sm font-semibold text-primary">Skill Analysis</p>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">Skill gap dashboard</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">Analyze a saved resume against a target occupation to explore skill coverage, priorities, and relationships.</p>
      </header>
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6" aria-labelledby="analysis-heading">
        <h2 id="analysis-heading" className="text-xl font-bold text-slate-900">Run a skill-gap analysis</h2>
        <p className="mt-1 text-sm leading-6 text-slate-500">Analysis results and visualizations use the selected backend pipeline run.</p>
        {isRestoring ? <p className="mt-4 text-sm text-slate-600" role="status">Restoring your session…</p>
          : !session ? <p className="mt-4 text-sm text-amber-800" role="status">Sign in to run analysis. <Link className="font-semibold underline" href="/login">Go to sign in</Link></p>
          : resumeState === "loading" ? <p className="mt-4 text-sm text-slate-600" role="status">Loading your saved resumes…</p>
          : resumeState === "error" ? <p className="mt-4 text-sm text-rose-800" role="alert">{resumeError}</p>
          : resumes.length === 0 ? <p className="mt-4 text-sm text-slate-600" role="status">Upload a resume before running skill-gap analysis.</p>
          : <form onSubmit={submit} className="mt-4 grid gap-4 md:grid-cols-2">
            <label className="text-sm font-medium text-slate-700">Saved resume<select required value={selectedResumeId} onChange={(event) => { setSelectedResumeId(event.target.value); clearResult(); }} className="mt-1 min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3"><option value="">Choose a resume</option>{resumes.map((resume) => <option key={resume.id} value={resume.id}>{resume.original_name}</option>)}</select></label>
            <label className="text-sm font-medium text-slate-700">Target occupation<input value={targetRole} onChange={(event) => { setTargetRole(event.target.value); clearResult(); }} disabled={autoSelectOccupation} maxLength={512} placeholder="e.g. Software Developer" className="mt-1 min-h-11 w-full rounded-lg border border-slate-300 px-3 disabled:bg-slate-100" /></label>
            <label className="flex items-start gap-2 text-sm text-slate-700 md:col-span-2"><input type="checkbox" checked={autoSelectOccupation} onChange={(event) => { setAutoSelectOccupation(event.target.checked); clearResult(); }} className="mt-1" /><span>Automatically select the top suggested occupation from my resume</span></label>
            {validationError && <p className="text-sm text-rose-800 md:col-span-2" role="alert">{validationError}</p>}
            <button type="submit" disabled={requestState === "loading"} className="min-h-11 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary-dark disabled:cursor-wait disabled:opacity-60 md:col-span-2">{requestState === "loading" ? "Analyzing…" : "Run AI analysis"}</button>
          </form>}
        {requestState === "loading" && <p className="mt-4 text-sm text-slate-600" role="status">Running the unified AI pipeline…</p>}
        {requestState === "error" && <div className="mt-4 text-sm text-rose-800" role="alert"><p>{requestError}</p><button onClick={() => { const form = document.querySelector<HTMLFormElement>("#analysis-heading + p + form"); form?.requestSubmit(); }} className="mt-2 rounded-lg border border-rose-300 px-3 py-1.5 font-semibold">Retry analysis</button></div>}
        {requestState === "success" && result && <AnalysisResults result={result} prioritiesState={prioritiesState} priorities={priorities} prioritiesError={prioritiesError} retryPriorities={() => session && void loadPriorities(result.pipeline_run_id, session.accessToken)} graphState={graphState} graph={graph} graphError={graphError} retryGraph={() => session && void loadGraph(result.pipeline_run_id, session.accessToken)} />}
      </section>
    </div>
  </div>;
}
