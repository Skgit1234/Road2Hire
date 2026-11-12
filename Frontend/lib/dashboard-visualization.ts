import type { KnowledgeGraphResponse, PipelineLearningRoadmapResponse, SkillPriorityResponse } from "./pipeline-types.ts";

export type ChartCount = { label: string; count: number };
export type LearningProgressPoint = { label: string; status: string; progress: number };

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function mapSkillCoverageChart(graph: KnowledgeGraphResponse | null): ChartCount[] {
  if (!graph) return [];
  const targetsByType = new Map<string, Set<string>>();
  for (const relationship of graph.relationships) {
    if (!record(relationship) || typeof relationship.type !== "string" || typeof relationship.target !== "string") continue;
    if (relationship.type !== "matches_skill" && relationship.type !== "partially_matches_skill") continue;
    const targetIds = targetsByType.get(relationship.type) ?? new Set<string>();
    targetIds.add(relationship.target);
    targetsByType.set(relationship.type, targetIds);
  }
  const missingIds = new Set<string>();
  for (const node of graph.nodes) {
    if (record(node) && node.gap_status === "missing" && typeof node.id === "string") missingIds.add(node.id);
  }
  const values = [
    { label: "Matched skills", count: targetsByType.get("matches_skill")?.size ?? 0 },
    { label: "Partially matched", count: targetsByType.get("partially_matches_skill")?.size ?? 0 },
    { label: "Missing skills", count: missingIds.size },
  ];
  return values.some((item) => item.count > 0) ? values : [];
}

export function mapPriorityChart(priorities: SkillPriorityResponse | null): ChartCount[] {
  if (!priorities) return [];
  const counts = new Map<string, number>();
  for (const item of priorities.items) {
    const priority = item.priority;
    if (typeof priority !== "string" || !priority.trim()) continue;
    const label = priority.trim();
    counts.set(label, (counts.get(label) ?? 0) + 1);
  }
  return [...counts.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([label, count]) => ({ label, count }));
}

export function mapLearningProgressChart(roadmap: PipelineLearningRoadmapResponse | null): LearningProgressPoint[] {
  if (!roadmap) return [];
  return roadmap.phases.flatMap((phase) => phase.items.map((item) => ({
    label: item.skill_name,
    status: item.status.replaceAll("_", " "),
    progress: item.progress,
  })));
}
