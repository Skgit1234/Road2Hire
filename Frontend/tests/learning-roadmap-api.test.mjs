import assert from "node:assert/strict";
import test from "node:test";
import {
  getPipelineLearningRoadmap,
  updatePipelineTaskProgress,
} from "../lib/pipeline-api.ts";

const item = {
  logical_item_key: "1:Java",
  roadmap_phase_number: 1,
  roadmap_phase_name: "Foundations",
  skill_name: "Java",
  skill_uri: null,
  priority: "essential",
  roadmap_item_data: { skill_name: "Java" },
  current_status: null,
  importance_rationale: null,
  learning_outcome: "Build Java fundamentals",
  suggested_activities: ["Complete a practice module"],
  practical_project: null,
  estimated_duration_weeks: "4",
  prerequisites: [],
  completion_criteria: "Complete the exercises",
  resource_categories: [],
  status: "in_progress",
  progress: 40,
  task_id: 23,
  updated_at: "2026-10-19T12:00:00Z",
};

const roadmap = {
  pipeline_run_id: 19,
  target_occupation_title: "Backend Developer",
  target_occupation_uri: null,
  total_roadmap_skills: 1,
  total_estimated_weeks: "4",
  phases: [{
    phase_number: 1,
    phase_name: "Foundations",
    description: "Build core skills",
    estimated_weeks: "4",
    items: [item],
  }],
  disclaimers: [],
};

const updatedTask = {
  id: 23,
  pipeline_run_id: 19,
  logical_item_key: item.logical_item_key,
  roadmap_phase_number: 1,
  roadmap_phase_name: "Foundations",
  skill_name: "Java",
  skill_uri: null,
  priority: "essential",
  status: "in_progress",
  progress: 55,
  roadmap_item_data: item.roadmap_item_data,
  updated_at: "2026-10-20T12:00:00Z",
};

test("roadmap GET validates the current pipeline response and bearer auth", async () => {
  let request;
  const result = await getPipelineLearningRoadmap("roadmap-token", undefined, async (url, options) => {
    request = { url: new URL(url), options };
    return Response.json(roadmap);
  });

  assert.equal(request.url.pathname, "/learning-roadmap");
  assert.equal(request.options.method, "GET");
  assert.equal(request.options.headers.Authorization, "Bearer roadmap-token");
  assert.deepEqual(result, roadmap);
});

test("roadmap can be requested by run ID and requires authentication", async () => {
  let requestedUrl;
  await getPipelineLearningRoadmap("roadmap-token", 19, async (url) => {
    requestedUrl = new URL(url);
    return Response.json(roadmap);
  });
  assert.equal(requestedUrl.pathname, "/learning-roadmap/runs/19");
  await assert.rejects(getPipelineLearningRoadmap(" ", undefined, async () => {
    throw new Error("fetch must not be called");
  }), /sign in/i);
});

test("task progress PATCH uses the current pipeline task response contract", async () => {
  let request;
  const result = await updatePipelineTaskProgress("task-token", 23, { status: "in_progress", progress: 55 }, async (url, options) => {
    request = { url: new URL(url), options };
    return Response.json(updatedTask);
  });

  assert.equal(request.url.pathname, "/tasks/23");
  assert.equal(request.options.method, "PATCH");
  assert.equal(request.options.headers.Authorization, "Bearer task-token");
  assert.equal(request.options.headers["Content-Type"], "application/json");
  assert.deepEqual(JSON.parse(request.options.body), { status: "in_progress", progress: 55 });
  assert.deepEqual(result, updatedTask);
});

test("task progress accepts all valid status and progress combinations", async () => {
  const validCombinations = [
    { status: "not_started", progress: 0 },
    { status: "in_progress", progress: 1 },
    { status: "in_progress", progress: 99 },
    { status: "completed", progress: 100 },
  ];

  for (const update of validCombinations) {
    let sentBody;
    await updatePipelineTaskProgress("token", 23, update, async (_url, options) => {
      sentBody = JSON.parse(options.body);
      return Response.json({ ...updatedTask, ...update });
    });
    assert.deepEqual(sentBody, update);
  }
});

test("task progress rejects invalid input and reports API, network, and shape errors", async () => {
  const unexpectedFetch = async () => { throw new Error("fetch must not be called"); };
  await assert.rejects(updatePipelineTaskProgress(" ", 23, { status: "in_progress", progress: 40 }, unexpectedFetch), /sign in/i);
  await assert.rejects(updatePipelineTaskProgress("token", 0, { status: "in_progress", progress: 40 }, unexpectedFetch), /valid task ID/i);
  await assert.rejects(updatePipelineTaskProgress("token", 23, { status: "in_progress", progress: 101 }, unexpectedFetch), /integer from 0 to 100/i);
  await assert.rejects(updatePipelineTaskProgress("token", 23, { status: "done", progress: 20 }, unexpectedFetch), /invalid learning task status/i);
  await assert.rejects(updatePipelineTaskProgress("token", 23, { progress: 40 }, unexpectedFetch), /Provide both a task status and progress/i);
  for (const update of [
    { status: "completed", progress: 99 },
    { status: "not_started", progress: 1 },
    { status: "in_progress", progress: 0 },
    { status: "in_progress", progress: 100 },
  ]) {
    await assert.rejects(
      updatePipelineTaskProgress("token", 23, update, unexpectedFetch),
      /Task status and progress are inconsistent/,
    );
  }
  await assert.rejects(updatePipelineTaskProgress("token", 23, { status: "in_progress", progress: 40 }, async () => Response.json(
    { detail: "Task not found" }, { status: 404 },
  )), (error) => error.status === 404 && error.message === "Task not found");
  await assert.rejects(updatePipelineTaskProgress("token", 23, { status: "in_progress", progress: 40 }, async () => { throw new Error("offline"); }), /Could not connect to the Road2Hire API/);
  await assert.rejects(updatePipelineTaskProgress("token", 23, { status: "in_progress", progress: 40 }, async () => Response.json({ id: 23 })), /invalid updated learning task response/i);
});
