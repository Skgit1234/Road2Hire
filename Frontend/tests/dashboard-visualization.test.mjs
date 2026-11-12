import assert from "node:assert/strict";
import test from "node:test";
import { mapLearningProgressChart, mapPriorityChart, mapSkillCoverageChart } from "../lib/dashboard-visualization.ts";

test("skill coverage chart counts distinct matched, partial, and missing graph skills", () => {
  const result = mapSkillCoverageChart({
    pipeline_run_id: 12,
    summary: {},
    nodes: [
      { id: "missing:sql", label: "SQL", gap_status: "missing" },
      { id: "missing:cloud", label: "Cloud", gap_status: "missing" },
    ],
    relationships: [
      { source: "candidate:java", target: "occupation:java", type: "matches_skill" },
      { source: "candidate:java-runtime", target: "occupation:java", type: "matches_skill" },
      { source: "candidate:postgres", target: "occupation:database", type: "partially_matches_skill" },
      { source: "candidate:other", target: "occupation:other", type: "unrelated" },
    ],
    scope: "Persisted skill graph",
  });

  assert.deepEqual(result, [
    { label: "Matched skills", count: 1 },
    { label: "Partially matched", count: 1 },
    { label: "Missing skills", count: 2 },
  ]);
});

test("skill priority chart aggregates actual saved priority labels", () => {
  assert.deepEqual(mapPriorityChart({
    pipeline_run_id: 12,
    target_occupation: null,
    items: [
      { skill_name: "Java", priority: "High" },
      { skill_name: "SQL", priority: "High" },
      { skill_name: "Cloud", priority: "Medium" },
      { skill_name: "Optional", priority: null },
    ],
  }), [
    { label: "High", count: 2 },
    { label: "Medium", count: 1 },
  ]);
});

test("learning progress chart maps task status and saved progress percentages", () => {
  const result = mapLearningProgressChart({
    pipeline_run_id: 12,
    target_occupation_title: "Developer",
    target_occupation_uri: null,
    total_roadmap_skills: 2,
    total_estimated_weeks: "4",
    phases: [{
      phase_number: 1,
      phase_name: "Core",
      description: "Core skills",
      estimated_weeks: "2",
      items: [
        { logical_item_key: "java", roadmap_phase_number: 1, roadmap_phase_name: "Core", skill_name: "Java", skill_uri: null, priority: "High", roadmap_item_data: {}, current_status: null, importance_rationale: null, learning_outcome: null, suggested_activities: [], practical_project: null, estimated_duration_weeks: null, prerequisites: [], completion_criteria: null, resource_categories: [], status: "in_progress", progress: 35, task_id: 4, updated_at: "2026-10-20T10:00:00Z" },
        { logical_item_key: "sql", roadmap_phase_number: 1, roadmap_phase_name: "Core", skill_name: "SQL", skill_uri: null, priority: "Medium", roadmap_item_data: {}, current_status: null, importance_rationale: null, learning_outcome: null, suggested_activities: [], practical_project: null, estimated_duration_weeks: null, prerequisites: [], completion_criteria: null, resource_categories: [], status: "completed", progress: 100, task_id: 5, updated_at: "2026-10-20T11:00:00Z" },
      ],
    }],
    disclaimers: [],
  });

  assert.deepEqual(result, [
    { label: "Java", status: "in progress", progress: 35 },
    { label: "SQL", status: "completed", progress: 100 },
  ]);
});

test("visualization mappings return empty data when backend data is absent", () => {
  assert.deepEqual(mapSkillCoverageChart(null), []);
  assert.deepEqual(mapSkillCoverageChart({ pipeline_run_id: 12, summary: {}, nodes: [], relationships: [], scope: "" }), []);
  assert.deepEqual(mapPriorityChart(null), []);
  assert.deepEqual(mapPriorityChart({ pipeline_run_id: 12, target_occupation: null, items: [] }), []);
  assert.deepEqual(mapLearningProgressChart(null), []);
  assert.deepEqual(mapLearningProgressChart({ pipeline_run_id: 12, target_occupation_title: null, target_occupation_uri: null, total_roadmap_skills: 0, total_estimated_weeks: null, phases: [], disclaimers: [] }), []);
});
