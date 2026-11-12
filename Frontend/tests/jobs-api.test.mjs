import test from "node:test";
import assert from "node:assert/strict";
import { createJob, listJobs, matchResumeToJob } from "../lib/api-client.ts";

const job = {
  id: 12,
  user_id: 7,
  title: "Software Developer",
  description: "Develop and maintain applications.",
  target_occupation: "Software Developer",
  required_skills: [
    { skill_name: "Python", importance: "essential", canonical_uri: null },
    { skill_name: "SQL", importance: "optional", canonical_uri: null },
  ],
  created_at: "2026-11-12T10:00:00Z",
  updated_at: "2026-11-12T10:00:00Z",
};

const matching = {
  job_id: 12,
  pipeline_run_id: 27,
  status: "completed",
  candidate_skill_source: "pipeline.skills.extracted_skills",
  candidate_skills_are_verified: false,
  matching_method: "semantic_skill_matcher",
  canonical_uri_matching: "not_used",
  thresholds_are_provisional: true,
  requirements: [
    {
      name: "Python",
      importance: "essential",
      canonical_uri: null,
      matched: true,
      candidate_skill: "Python",
      match_status: "confirmed_match",
      similarity_score: 1,
      evidence: "Canonical/exact equality",
      related_evidence: [],
    },
    {
      name: "SQL",
      importance: "optional",
      canonical_uri: null,
      matched: false,
      candidate_skill: "PostgreSQL",
      match_status: "related_skill",
      similarity_score: 0.71,
      evidence: "Database ecosystem",
      related_evidence: [{ candidate_skill: "PostgreSQL", similarity_score: 0.71, relation: "Database ecosystem", is_equivalent: false }],
    },
  ],
  scores: { essential: 1, optional: 0, overall: 0.75 },
};

const run = {
  id: 27,
  status: "completed",
  selection_mode: "explicit",
  target_occupation_uri: "https://example.test/occupation",
  target_occupation_title: "Software Developer",
  overall_skill_coverage_score: 0.5,
  essential_skill_coverage_score: 0.5,
  optional_skill_coverage_score: 0.5,
  readiness_class: "developing",
  is_ood: false,
  canonical_output: {},
  error_code: null,
  error_stage: null,
  error_message: null,
  created_at: "2026-11-12T10:00:00Z",
  completed_at: "2026-11-12T10:01:00Z",
};

const matchResponse = {
  job,
  run,
  matching_basis: "Occupation analysis and job-specific requirements are separate.",
  job_specific_required_skills_applied: true,
  job_specific_matching: matching,
};

test("job listing sends bearer authorization and validates saved jobs", async () => {
  let request;
  assert.deepEqual(await listJobs("jobs-token", async (url, options) => {
    request = { url, options };
    return Response.json([job]);
  }), [job]);
  assert.match(request.url, /\/jobs$/);
  assert.equal(request.options.method, "GET");
  assert.equal(request.options.headers.Authorization, "Bearer jobs-token");
});

test("job creation sends backend fields and validates the saved response", async () => {
  let request;
  const details = {
    title: job.title,
    description: job.description,
    target_occupation: job.target_occupation,
    required_skills: [
      { skill_name: "Python", importance: "essential" },
      { skill_name: "SQL", importance: "optional" },
    ],
  };
  assert.deepEqual(await createJob(details, "jobs-token", async (url, options) => {
    request = { url, options };
    return Response.json(job, { status: 201 });
  }), job);
  assert.match(request.url, /\/jobs$/);
  assert.equal(request.options.method, "POST");
  assert.equal(request.options.headers.Authorization, "Bearer jobs-token");
  assert.deepEqual(JSON.parse(request.options.body), details);
});

test("job matching sends the selected resume and validates nested result evidence", async () => {
  let request;
  const result = await matchResumeToJob(12, 31, "jobs-token", async (url, options) => {
    request = { url, options };
    return Response.json(matchResponse);
  });
  assert.match(request.url, /\/jobs\/12\/matches$/);
  assert.equal(request.options.method, "POST");
  assert.equal(request.options.headers.Authorization, "Bearer jobs-token");
  assert.deepEqual(JSON.parse(request.options.body), { resume_id: 31 });
  assert.deepEqual(result.job_specific_matching.requirements.map((item) => item.match_status), ["confirmed_match", "related_skill"]);
});

test("job APIs reject missing authentication and invalid IDs before fetching", async () => {
  const noFetch = async () => { throw new Error("fetch must not be called"); };
  await assert.rejects(listJobs(" ", noFetch), /Sign in to manage saved jobs/);
  await assert.rejects(createJob({ title: " ", description: "d", target_occupation: "r", required_skills: [] }, "token", noFetch), /title, description/);
  await assert.rejects(matchResumeToJob(0, 31, "token", noFetch), /valid saved job/);
  await assert.rejects(matchResumeToJob(12, -1, "token", noFetch), /valid saved resume/);
  await assert.rejects(matchResumeToJob(12, 31, " ", noFetch), /Sign in to match/);
});

test("job APIs preserve backend errors and safely report network failures", async () => {
  await assert.rejects(listJobs("token", async () => Response.json({ detail: "Not authenticated" }, { status: 401 })), (error) => {
    assert.equal(error.status, 401);
    assert.equal(error.message, "Not authenticated");
    return true;
  });
  await assert.rejects(createJob({ title: "Role", description: "Description", target_occupation: "Role", required_skills: [] }, "token", async () => { throw new Error("offline"); }), /Could not connect to the Road2Hire API/);
});

test("job and matching response validators reject malformed schema and evidence", async () => {
  await assert.rejects(listJobs("token", async () => Response.json([{ ...job, required_skills: [{ skill_name: "Python", importance: "critical" }] }])), /invalid job list/);
  await assert.rejects(createJob({ title: "Role", description: "Description", target_occupation: "Role", required_skills: [] }, "token", async () => Response.json({ ...job, updated_at: "bad-date" })), /invalid job response/);
  await assert.rejects(matchResumeToJob(12, 31, "token", async () => Response.json({ ...matchResponse, run: { ...run, status: "queued" } })), /invalid job matching response/);
  await assert.rejects(matchResumeToJob(12, 31, "token", async () => Response.json({ ...matchResponse, job_specific_matching: { ...matching, scores: { essential: 1.1, optional: 0, overall: 0.5 } } })), /invalid job matching response/);
  await assert.rejects(matchResumeToJob(12, 31, "token", async () => Response.json({ ...matchResponse, job_specific_matching: { ...matching, requirements: [{ ...matching.requirements[0], matched: true, match_status: "uncertain_match" }] } })), /invalid job matching response/);
  await assert.rejects(matchResumeToJob(12, 31, "token", async () => Response.json({ ...matchResponse, job_specific_matching: { ...matching, requirements: [{ ...matching.requirements[1], related_evidence: [{ candidate_skill: "PostgreSQL", similarity_score: 2, relation: "related", is_equivalent: false }] }] } })), /invalid job matching response/);
});
