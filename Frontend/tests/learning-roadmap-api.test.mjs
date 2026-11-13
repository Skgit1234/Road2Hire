
import assert from "node:assert/strict";
import test from "node:test";

import {
  getPipelineLearningRoadmap,
  updatePipelineTaskProgress,
} from "../lib/pipeline-api.ts";

// -----------------------------------------------------------------------------
// Pipeline learning-roadmap API fixtures
// -----------------------------------------------------------------------------

const pipelineItem = {
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

const pipelineRoadmap = {
  pipeline_run_id: 19,
  target_occupation_title: "Backend Developer",
  target_occupation_uri: null,
  total_roadmap_skills: 1,
  total_estimated_weeks: "4",
  phases: [
    {
      phase_number: 1,
      phase_name: "Foundations",
      description: "Build core skills",
      estimated_weeks: "4",
      items: [pipelineItem],
    },
  ],
  disclaimers: [],
};

const updatedPipelineTask = {
  id: 23,
  pipeline_run_id: 19,
  logical_item_key: pipelineItem.logical_item_key,
  roadmap_phase_number: 1,
  roadmap_phase_name: "Foundations",
  skill_name: "Java",
  skill_uri: null,
  priority: "essential",
  status: "in_progress",
  progress: 55,
  roadmap_item_data: pipelineItem.roadmap_item_data,
  updated_at: "2026-10-20T12:00:00Z",
};

// -----------------------------------------------------------------------------
// Pipeline API tests: GET /learning-roadmap
// -----------------------------------------------------------------------------

test("pipeline roadmap GET validates the current response and bearer authorization", async () => {
  let request;

  const result = await getPipelineLearningRoadmap(
    "roadmap-token",
    undefined,
    async (url, options) => {
      request = { url: new URL(url), options };
      return Response.json(pipelineRoadmap);
    },
  );

  assert.equal(request.url.pathname, "/learning-roadmap");
  assert.equal(request.options.method, "GET");
  assert.equal(
    request.options.headers.Authorization,
    "Bearer roadmap-token",
  );
  assert.deepEqual(result, pipelineRoadmap);
});

test("pipeline roadmap can be requested by run ID and requires authentication", async () => {
  let requestedUrl;

  await getPipelineLearningRoadmap(
    "roadmap-token",
    19,
    async (url) => {
      requestedUrl = new URL(url);
      return Response.json(pipelineRoadmap);
    },
  );

  assert.equal(
    requestedUrl.pathname,
    "/learning-roadmap/runs/19",
  );

  await assert.rejects(
    getPipelineLearningRoadmap(
      " ",
      undefined,
      async () => {
        throw new Error("fetch must not be called");
      },
    ),
    /sign in/i,
  );
});

// -----------------------------------------------------------------------------
// Pipeline API tests: PATCH /tasks/{id}
// -----------------------------------------------------------------------------

test("pipeline task progress PATCH uses the current task response contract", async () => {
  let request;

  const result = await updatePipelineTaskProgress(
    "task-token",
    23,
    { status: "in_progress", progress: 55 },
    async (url, options) => {
      request = { url: new URL(url), options };
      return Response.json(updatedPipelineTask);
    },
  );

  assert.equal(request.url.pathname, "/tasks/23");
  assert.equal(request.options.method, "PATCH");
  assert.equal(
    request.options.headers.Authorization,
    "Bearer task-token",
  );
  assert.equal(
    request.options.headers["Content-Type"],
    "application/json",
  );
  assert.deepEqual(
    JSON.parse(request.options.body),
    { status: "in_progress", progress: 55 },
  );
  assert.deepEqual(result, updatedPipelineTask);
});

test("pipeline task progress accepts all valid status and progress combinations", async () => {
  const validCombinations = [
    { status: "not_started", progress: 0 },
    { status: "in_progress", progress: 1 },
    { status: "in_progress", progress: 99 },
    { status: "completed", progress: 100 },
  ];

  for (const update of validCombinations) {
    let sentBody;

    await updatePipelineTaskProgress(
      "token",
      23,
      update,
      async (_url, options) => {
        sentBody = JSON.parse(options.body);
        return Response.json({
          ...updatedPipelineTask,
          ...update,
        });
      },
    );

    assert.deepEqual(sentBody, update);
  }
});

test("pipeline task progress rejects invalid input and reports API, network, and response-shape errors", async () => {
  const unexpectedFetch = async () => {
    throw new Error("fetch must not be called");
  };

  await assert.rejects(
    updatePipelineTaskProgress(
      " ",
      23,
      { status: "in_progress", progress: 40 },
      unexpectedFetch,
    ),
    /sign in/i,
  );

  await assert.rejects(
    updatePipelineTaskProgress(
      "token",
      0,
      { status: "in_progress", progress: 40 },
      unexpectedFetch,
    ),
    /valid task ID/i,
  );

  await assert.rejects(
    updatePipelineTaskProgress(
      "token",
      23,
      { status: "in_progress", progress: 101 },
      unexpectedFetch,
    ),
    /integer from 0 to 100/i,
  );

  await assert.rejects(
    updatePipelineTaskProgress(
      "token",
      23,
      { status: "done", progress: 20 },
      unexpectedFetch,
    ),
    /invalid learning task status/i,
  );

  await assert.rejects(
    updatePipelineTaskProgress(
      "token",
      23,
      { progress: 40 },
      unexpectedFetch,
    ),
    /Provide both a task status and progress/i,
  );

  const inconsistentUpdates = [
    { status: "completed", progress: 99 },
    { status: "not_started", progress: 1 },
    { status: "in_progress", progress: 0 },
    { status: "in_progress", progress: 100 },
  ];

  for (const update of inconsistentUpdates) {
    await assert.rejects(
      updatePipelineTaskProgress(
        "token",
        23,
        update,
        unexpectedFetch,
      ),
      /Task status and progress are inconsistent/,
    );
  }

  await assert.rejects(
    updatePipelineTaskProgress(
      "token",
      23,
      { status: "in_progress", progress: 40 },
      async () =>
        Response.json(
          { detail: "Task not found" },
          { status: 404 },
        ),
    ),
    (error) =>
      error.status === 404 &&
      error.message === "Task not found",
  );

  await assert.rejects(
    updatePipelineTaskProgress(
      "token",
      23,
      { status: "in_progress", progress: 40 },
      async () => {
        throw new Error("offline");
      },
    ),
    /Could not connect to the Road2Hire API/,
  );

  await assert.rejects(
    updatePipelineTaskProgress(
      "token",
      23,
      { status: "in_progress", progress: 40 },
      async () => Response.json({ id: 23 }),
    ),
    /invalid updated learning task response/i,
  );
});
