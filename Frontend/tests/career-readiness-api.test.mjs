import assert from "node:assert/strict";
import test from "node:test";
import { getPipelineCareerReadiness } from "../lib/pipeline-api.ts";

const completed = {
  pipeline_run_id: 12,
  resume_id: 7,
  completed_at: "2026-10-19T23:16:17.148417+05:30",
  predicted_class: "Developing",
  class_probabilities: { Developing: 0.75, "Job Ready": 0.2, "Not Ready": 0.05 },
  model_version: "0.1.0-exploratory",
  model_type: "LogisticRegression",
  is_experimental: true,
  is_ood: false,
  ood_warnings: [],
  pipeline_warnings: [],
  training_sample_count: 71,
  training_class_distribution: { Developing: 52, "Job Ready": 16, "Not Ready": 3 },
  feature_values: { skills_count: 5 },
  feature_diagnostics: {},
  limitations: ["Experimental model"],
};

test("career readiness uses the backend prediction contract and bearer auth", async () => {
  let request;
  const result = await getPipelineCareerReadiness("readiness-token", undefined, async (url, options) => {
    request = { url: new URL(url), options };
    return Response.json(completed);
  });

  assert.equal(request.url.pathname, "/career-readiness");
  assert.equal(request.url.search, "");
  assert.equal(request.options.method, "GET");
  assert.equal(request.options.headers.Authorization, "Bearer readiness-token");
  assert.deepEqual(result, completed);
});

test("career readiness accepts a selected run and requires authentication", async () => {
  let requestedUrl;
  const result = await getPipelineCareerReadiness("readiness-token", 12, async (url) => {
    requestedUrl = new URL(url);
    return Response.json(completed);
  });
  assert.equal(requestedUrl.pathname, "/career-readiness/runs/12");
  assert.equal(result.pipeline_run_id, 12);

  await assert.rejects(getPipelineCareerReadiness(" ", undefined, async () => {
    throw new Error("fetch must not be called");
  }), /sign in/i);
});

test("career readiness surfaces backend and network errors and rejects malformed output", async () => {
  await assert.rejects(getPipelineCareerReadiness("token", undefined, async () => Response.json(
    { detail: "No completed pipeline run is available" }, { status: 404 },
  )), (error) => error.status === 404 && error.message === "No completed pipeline run is available");
  await assert.rejects(getPipelineCareerReadiness("token", undefined, async () => { throw new Error("offline"); }), /Could not connect to the Road2Hire API/);
  await assert.rejects(getPipelineCareerReadiness("token", undefined, async () => Response.json({ ...completed, class_probabilities: [] })), /invalid career-readiness response/i);
});
