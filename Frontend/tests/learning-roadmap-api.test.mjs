import assert from "node:assert/strict";
import test from "node:test";
import { getLearningRoadmap, prepareLearningRoadmap, updateTaskProgress } from "../lib/api-client.ts";

const resource = {
  resource_id: "LR-4",
  skill_name: "Java",
  category: "Programming",
  provider: "Example Provider",
  course_title: "Java course",
  difficulty: "Beginner",
  duration_hours: "4",
  certificate: null,
  course_url: "https://example.test/java",
};

const roadmap = {
  analysis_id: 19,
  target_role: "Backend Developer",
  resource_availability: "available",
  tasks: [
    { id: 23, skill_name: "Java", status: "in_progress", progress: 40, resources: [resource] },
    { id: 24, skill_name: "SQL", status: "not_started", progress: 0, resources: [] },
    { id: 25, skill_name: "Docker", status: "completed", progress: 100, resources: [] },
  ],
};

test("roadmap GET sends bearer authorization and parses numeric task IDs and exact statuses", async () => {
  let request;
  const result = await getLearningRoadmap("roadmap-token", async (url, options) => {
    request = { url: new URL(url), options };
    return Response.json(roadmap);
  });
  assert.equal(request.url.pathname, "/learning-roadmap");
  assert.equal(request.url.search, "");
  assert.equal(request.options.method, "GET");
  assert.equal(request.options.headers.Authorization, "Bearer roadmap-token");
  assert.deepEqual(result.tasks.map(({ id, status }) => [id, status]), [
    [23, "in_progress"], [24, "not_started"], [25, "completed"],
  ]);
  assert.deepEqual(result.tasks[0].resources, [resource]);
});

test("roadmap prepare POST sends bearer authorization and parses the response", async () => {
  let request;
  const result = await prepareLearningRoadmap("prepare-token", async (url, options) => {
    request = { url: new URL(url), options };
    return Response.json(roadmap);
  });
  assert.equal(request.url.pathname, "/learning-roadmap/prepare");
  assert.equal(request.options.method, "POST");
  assert.equal(request.options.headers.Authorization, "Bearer prepare-token");
  assert.equal(request.options.body, undefined);
  assert.deepEqual(result.tasks.map(({ id }) => id), [23, 24, 25]);
});

test("roadmap prepare requires authentication", async () => {
  await assert.rejects(prepareLearningRoadmap(" ", async () => {
    throw new Error("fetch must not be called");
  }), /Sign in/);
});

test("roadmap represents the backend response when no skill-gap analysis exists", async () => {
  const response = {
    analysis_id: null,
    target_role: null,
    tasks: [],
    resource_availability: "awaiting_skill_gap_analysis",
  };
  assert.deepEqual(await getLearningRoadmap("token", async () => Response.json(response)), response);
});

test("roadmap requires authentication and rejects malformed task statuses and identifiers", async () => {
  const unexpectedFetch = async () => { throw new Error("fetch must not be called"); };
  await assert.rejects(getLearningRoadmap(" ", unexpectedFetch), /Sign in/);
  await assert.rejects(getLearningRoadmap("token", async () => Response.json({
    ...roadmap,
    tasks: [{ ...roadmap.tasks[0], id: "23" }],
  })), /invalid learning-roadmap response/);
  await assert.rejects(getLearningRoadmap("token", async () => Response.json({
    ...roadmap,
    tasks: [{ ...roadmap.tasks[0], status: "In progress" }],
  })), /invalid learning-roadmap response/);
});

test("task progress PATCH sends numeric task ID, bearer token, and JSON progress", async () => {
  let request;
  const response = { id: 23, skill_gap_id: 19, skill_name: "Java", status: "in_progress", progress: 40, updated_at: "2026-10-19T12:00:00Z" };
  const result = await updateTaskProgress(23, { progress: 40 }, "task-token", async (url, options) => {
    request = { url: new URL(url), options };
    return Response.json(response);
  });
  assert.equal(request.url.pathname, "/tasks/23");
  assert.equal(request.options.method, "PATCH");
  assert.equal(request.options.headers.Authorization, "Bearer task-token");
  assert.equal(request.options.headers["Content-Type"], "application/json");
  assert.deepEqual(JSON.parse(request.options.body), { progress: 40 });
  assert.deepEqual(result, response);
});

test("task progress PATCH validates inputs and surfaces API, network, and schema failures", async () => {
  const unexpectedFetch = async () => { throw new Error("fetch must not be called"); };
  await assert.rejects(updateTaskProgress(23, { progress: 40 }, " ", unexpectedFetch), /Sign in/);
  await assert.rejects(updateTaskProgress(0, { progress: 40 }, "token", unexpectedFetch), /valid roadmap task/);
  await assert.rejects(updateTaskProgress(23, {}, "token", unexpectedFetch), /status or progress/);
  await assert.rejects(updateTaskProgress(23, { progress: 101 }, "token", unexpectedFetch), /whole number from 0 to 100/);
  await assert.rejects(updateTaskProgress(23, { status: "completed", progress: 40 }, "token", unexpectedFetch), /inconsistent/);
  await assert.rejects(updateTaskProgress(23, { progress: 40 }, "token", async () => Response.json(
    { detail: "Task not found" }, { status: 404 },
  )), (error) => {
    assert.equal(error.status, 404);
    assert.equal(error.message, "Task not found");
    return true;
  });
  await assert.rejects(updateTaskProgress(23, { progress: 40 }, "token", async () => { throw new Error("offline"); }), /Could not connect to the Road2Hire API/);
  await assert.rejects(updateTaskProgress(23, { progress: 40 }, "token", async () => Response.json({ id: 23 })), /invalid task-progress response/);
});
