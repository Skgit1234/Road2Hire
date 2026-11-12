import assert from "node:assert/strict";
import test from "node:test";
import { getCareerReadiness } from "../lib/api-client.ts";

const completed = {
  score: 75,
  formula: "Use the most recent saved skill-gap match_score.",
  analysis_id: 12,
  target_role: "Fullstack Developer",
  matched_skills: ["JavaScript", "React", "Java"],
  required_skills: ["JavaScript", "React", "Java", "SQL"],
  missing_skills: ["SQL"],
  created_at: "2026-10-19T23:16:17.148417+05:30",
};

test("career-readiness request uses GET and bearer auth without adding query parameters", async () => {
  let request;
  const result = await getCareerReadiness("readiness-token", async (url, options) => {
    request = { url: new URL(url), options };
    return Response.json(completed);
  });

  assert.equal(request.url.pathname, "/career-readiness");
  assert.equal(request.url.search, "");
  assert.equal(request.options.method, "GET");
  assert.equal(request.options.headers.Authorization, "Bearer readiness-token");
  assert.deepEqual(result, completed);
});

test("career-readiness request requires authentication before fetching", async () => {
  await assert.rejects(getCareerReadiness("  ", async () => {
    throw new Error("fetch must not be called");
  }), /Sign in/);
});

test("career-readiness parses the backend no-analysis response distinctly", async () => {
  const result = await getCareerReadiness("token", async () => Response.json({
    score: null,
    formula: "Use the most recent saved skill-gap match_score.",
    analysis_id: null,
    target_role: null,
    message: "Run a skill-gap analysis to calculate a readiness score.",
  }));
  assert.equal(result.score, null);
  assert.equal(result.analysis_id, null);
  assert.match(result.message, /Run a skill-gap analysis/);
});

test("career-readiness surfaces API and network errors and rejects malformed results", async () => {
  await assert.rejects(getCareerReadiness("token", async () => Response.json(
    { detail: "Not authenticated" }, { status: 401 },
  )), (error) => {
    assert.equal(error.status, 401);
    assert.equal(error.message, "Not authenticated");
    return true;
  });
  await assert.rejects(getCareerReadiness("token", async () => { throw new Error("offline"); }), /Could not connect to the Road2Hire API/);
  await assert.rejects(getCareerReadiness("token", async () => Response.json({ ...completed, score: 101 })), /invalid career-readiness response/);
  await assert.rejects(getCareerReadiness("token", async () => Response.json({ ...completed, matched_skills: "Java" })), /invalid career-readiness response/);
});
