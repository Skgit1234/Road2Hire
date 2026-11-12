import assert from "node:assert/strict";
import test from "node:test";
import { getDashboard, getRecentActivity } from "../lib/api-client.ts";

const dashboardResponse = {
  resume_count: 2,
  skill_gap_count: 1,
  average_match_score: 75,
  latest_resume: { id: 12, original_name: "resume.pdf", uploaded_at: "2026-10-20T10:00:00Z" },
  latest_skill_gap: { id: 4, resume_id: 12, target_role: "Fullstack Developer", match_score: 75, created_at: "2026-10-20T10:10:00Z" },
};

test("dashboard request uses bearer auth and validates backend aggregate fields", async () => {
  let request;
  const result = await getDashboard("test-token", async (url, options) => {
    request = { url, options };
    return Response.json(dashboardResponse);
  });

  assert.ok(request.url.endsWith("/dashboard"));
  assert.equal(request.options.method, "GET");
  assert.equal(request.options.headers.Authorization, "Bearer test-token");
  assert.deepEqual(result, dashboardResponse);
});

test("dashboard preserves empty aggregates without inventing scores", async () => {
  const result = await getDashboard("test-token", async () => Response.json({
    resume_count: 0,
    skill_gap_count: 0,
    average_match_score: null,
    latest_resume: null,
    latest_skill_gap: null,
  }));
  assert.equal(result.average_match_score, null);
  assert.equal(result.latest_resume, null);
  assert.equal(result.latest_skill_gap, null);
});

test("dashboard accepts a saved analysis whose coverage score is unavailable", async () => {
  const payload = {
    ...dashboardResponse,
    latest_skill_gap: { ...dashboardResponse.latest_skill_gap, match_score: null },
  };
  const result = await getDashboard("test-token", async () => Response.json(payload));
  assert.equal(result.latest_skill_gap.match_score, null);
});

test("dashboard rejects malformed responses and reports API failures", async () => {
  await assert.rejects(getDashboard("test-token", async () => Response.json({ ...dashboardResponse, resume_count: -1 })), /invalid dashboard response/i);
  await assert.rejects(getDashboard("test-token", async () => Response.json({ detail: "Unavailable" }, { status: 503 })), { status: 503 });
  await assert.rejects(getDashboard("", async () => Response.json(dashboardResponse)), /sign in/i);
});

test("recent activity requests the requested limit and parses supported event variants", async () => {
  let request;
  const events = [
    { type: "resume_uploaded", id: 12, timestamp: "2026-10-20T10:00:00Z", resume_name: "resume.pdf" },
    { type: "skill_gap_analyzed", id: 4, timestamp: "2026-10-20T10:10:00Z", resume_id: 12, target_role: "Fullstack Developer", match_score: 75 },
    { type: "skill_gap_analyzed", id: 5, timestamp: "2026-10-20T10:15:00Z", resume_id: 12, target_role: "Data Analyst", match_score: null },
    { type: "task_progress_updated", id: 8, timestamp: "2026-10-20T10:20:00Z", pipeline_run_id: 15, skill_name: "Python", status: "in_progress", progress: 50 },
  ];
  const result = await getRecentActivity("test-token", 10, async (url, options) => {
    request = { url, options };
    return Response.json({ items: events, limit: 10 });
  });

  assert.ok(request.url.endsWith("/activity?limit=10"));
  assert.equal(request.options.headers.Authorization, "Bearer test-token");
  assert.deepEqual(result.items, events);
});

test("recent activity rejects malformed events and invalid limits", async () => {
  await assert.rejects(getRecentActivity("test-token", 0), /limit must be/i);
  await assert.rejects(
    getRecentActivity("test-token", 20, async () => Response.json({
      items: [{
        type: "task_progress_updated",
        id: 8,
        timestamp: "2026-10-20T10:20:00Z",
        skill_gap_id: 4,
        skill_name: "Python",
        status: "in_progress",
        progress: 50,
      }],
      limit: 20,
    })),
    /invalid activity response/i,
  );
  await assert.rejects(getRecentActivity("test-token", 20, async () => Response.json({ items: [{ type: "unknown", id: 1, timestamp: "2026-10-20T00:00:00Z" }], limit: 20 })), /invalid activity response/i);
});
