import assert from "node:assert/strict";
import test from "node:test";
import { analyzeSkillGap } from "../lib/pipeline-api.ts";

const validResponse = {
  pipeline_run_id: 12,
  status: "completed",
  matching_basis: "semantic",
  warnings: [],
  target_occupation: null,
  skill_gap: null,
  learning_roadmap: null,
  knowledge_graph: null,
  error: null,
};

test("skill-gap analysis requires authentication before fetching", async () => {
  let fetchCalled = false;
  await assert.rejects(
    analyzeSkillGap(" ", { resume_id: 7, auto_select_top_occupation: true }, async () => {
      fetchCalled = true;
      return Response.json(validResponse);
    }),
    /sign in/i,
  );
  assert.equal(fetchCalled, false);
});

test("skill-gap analysis surfaces backend HTTP errors", async () => {
  await assert.rejects(
    analyzeSkillGap("test-token", { resume_id: 7, auto_select_top_occupation: true }, async () =>
      Response.json({ detail: "Resume not found" }, { status: 404 })),
    (error) => error.status === 404 && error.message === "Resume not found",
  );
});

test("skill-gap analysis reports network failures safely", async () => {
  await assert.rejects(
    analyzeSkillGap("test-token", { resume_id: 7, auto_select_top_occupation: true }, async () => {
      throw new Error("offline");
    }),
    /Could not connect to the Road2Hire API/,
  );
});

test("skill-gap analysis rejects malformed backend responses", async () => {
  await assert.rejects(
    analyzeSkillGap("test-token", { resume_id: 7, auto_select_top_occupation: true }, async () =>
      Response.json({ ...validResponse, matching_basis: 42 })),
    /invalid skill-gap analysis response/i,
  );
});
