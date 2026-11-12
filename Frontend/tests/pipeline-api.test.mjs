import test from "node:test";
import assert from "node:assert/strict";

import {
  analyzeSkillGap,
  getPipelineSkillGapHistory,
  getPipelineCareerReadiness,
  updatePipelineTaskProgress,
  getPipelineLearningRoadmap,
} from "../lib/pipeline-api.ts";

test("analyzeSkillGap sends authenticated analysis request", async () => {
  let capturedUrl;
  let capturedInit;

  const mockFetch = async (url, init) => {
    capturedUrl = url;
    capturedInit = init;

    return Response.json({
      pipeline_run_id: 12,
      status: "completed",
      matching_basis: "semantic",
      warnings: [],
      target_occupation: null,
      skill_gap: null,
      learning_roadmap: null,
      knowledge_graph: null,
      error: null,
    });
  };

  const result = await analyzeSkillGap(
    "test-access-token",
    { resume_id: 5, auto_select_top_occupation: true },
    mockFetch,
  );

  assert.equal(result.pipeline_run_id, 12);
  assert.equal(capturedUrl.endsWith("/skill-gaps/analyze"), true);
  assert.equal(capturedInit.method, "POST");
  assert.equal(
    capturedInit.headers.Authorization,
    "Bearer test-access-token",
  );

  assert.deepEqual(JSON.parse(capturedInit.body), {
    resume_id: 5,
    auto_select_top_occupation: true,
  });
});

test("analyzeSkillGap rejects a missing occupation selection", async () => {
  let fetchCalled = false;

  const mockFetch = async () => {
    fetchCalled = true;
    return Response.json({});
  };

  await assert.rejects(
    analyzeSkillGap(
      "test-access-token",
      { resume_id: 5 },
      mockFetch,
    ),
    /target occupation|automatic occupation selection/i,
  );

  assert.equal(fetchCalled, false);
});

test("analyzeSkillGap rejects an invalid resume ID", async () => {
  await assert.rejects(
    analyzeSkillGap(
      "test-access-token",
      { resume_id: 0, auto_select_top_occupation: true },
      async () => Response.json({}),
    ),
    /valid resume/i,
  );
});

test("getPipelineSkillGapHistory sends pagination and bearer token", async () => {
  let capturedUrl;
  let capturedInit;

  const mockFetch = async (url, init) => {
    capturedUrl = url;
    capturedInit = init;

    return Response.json({
      items: [],
      total: 0,
      limit: 10,
      offset: 20,
    });
  };

  const result = await getPipelineSkillGapHistory(
    "test-access-token",
    10,
    20,
    mockFetch,
  );

  assert.deepEqual(result.items, []);
  assert.equal(capturedUrl.includes("/skill-gaps/history?"), true);
  assert.equal(capturedUrl.includes("limit=10"), true);
  assert.equal(capturedUrl.includes("offset=20"), true);
  assert.equal(
    capturedInit.headers.Authorization,
    "Bearer test-access-token",
  );
});

test("getPipelineSkillGapHistory rejects invalid pagination", async () => {
  await assert.rejects(
    getPipelineSkillGapHistory(
      "test-access-token",
      0,
      0,
      async () => Response.json({}),
    ),
    /history limit/i,
  );
});

test("analyzeSkillGap rejects unsupported pipeline statuses", async () => {
  await assert.rejects(
    analyzeSkillGap(
      "test-access-token",
      { resume_id: 5, auto_select_top_occupation: true },
      async () => Response.json({
        pipeline_run_id: 12,
        status: "queued",
        matching_basis: "semantic",
        warnings: [],
        target_occupation: null,
        skill_gap: null,
        learning_roadmap: null,
        knowledge_graph: null,
        error: null,
      }),
    ),
    /invalid skill-gap analysis response/i,
  );
});

test("career readiness accepts decimal probabilities and integer class counts", async () => {
  const result = await getPipelineCareerReadiness(
    "test-access-token",
    undefined,
    async () => Response.json({
      pipeline_run_id: 12,
      resume_id: 5,
      completed_at: "2026-11-10T10:00:00",
      predicted_class: "developing",
      class_probabilities: {
        developing: 0.82,
        ready: 0.18,
      },
      model_version: "v1",
      model_type: "classifier",
      is_experimental: false,
      is_ood: false,
      ood_warnings: [],
      pipeline_warnings: [],
      training_sample_count: 120,
      training_class_distribution: {
        developing: 80,
        ready: 40,
      },
      feature_values: {
        skill_coverage: 0.75,
      },
      feature_diagnostics: {},
      limitations: [],
    }),
  );

  assert.equal(result.class_probabilities.developing, 0.82);
  assert.equal(result.training_class_distribution.developing, 80);
});

test("career readiness rejects fractional training class counts", async () => {
  await assert.rejects(
    getPipelineCareerReadiness(
      "test-access-token",
      undefined,
      async () => Response.json({
        pipeline_run_id: 12,
        resume_id: 5,
        completed_at: null,
        predicted_class: "developing",
        class_probabilities: { developing: 0.82 },
        model_version: null,
        model_type: null,
        is_experimental: false,
        is_ood: false,
        ood_warnings: [],
        pipeline_warnings: [],
        training_sample_count: 120,
        training_class_distribution: { developing: 80.5 },
        feature_values: {},
        feature_diagnostics: {},
        limitations: [],
      }),
    ),
    /invalid career-readiness response/i,
  );
});

test("task progress update sends PATCH payload and validates the response", async () => {
  let capturedUrl;
  let capturedInit;

  const mockFetch = async (url, init) => {
    capturedUrl = url;
    capturedInit = init;

    return Response.json({
      id: 7,
      pipeline_run_id: 12,
      logical_item_key: "phase:1:skill:javascript",
      roadmap_phase_number: 1,
      roadmap_phase_name: "Foundations",
      skill_name: "JavaScript",
      skill_uri: null,
      priority: "high",
      status: "in_progress",
      progress: 45,
      roadmap_item_data: {},
      updated_at: "2026-11-10T10:00:00",
    });
  };

  const result = await updatePipelineTaskProgress(
    "test-access-token",
    7,
    { status: "in_progress", progress: 45 },
    mockFetch,
  );

  assert.equal(result.id, 7);
  assert.equal(capturedUrl.endsWith("/tasks/7"), true);
  assert.equal(capturedInit.method, "PATCH");
  assert.equal(
    capturedInit.headers.Authorization,
    "Bearer test-access-token",
  );
  assert.deepEqual(JSON.parse(capturedInit.body), {
    status: "in_progress",
    progress: 45,
  });
});

test("task progress update rejects malformed task responses", async () => {
  await assert.rejects(
    updatePipelineTaskProgress(
      "test-access-token",
      7,
      { status: "in_progress", progress: 45 },
      async () => Response.json({
        id: 7,
        pipeline_run_id: 12,
        logical_item_key: "phase:1:skill:javascript",
        roadmap_phase_number: 1,
        roadmap_phase_name: null,
        skill_name: "JavaScript",
        skill_uri: null,
        priority: null,
        status: "queued",
        progress: 45,
        roadmap_item_data: {},
        updated_at: "2026-11-10T10:00:00",
      }),
    ),
    /invalid updated learning task response/i,
  );
});

test("career readiness rejects fractional training sample counts", async () => {
  await assert.rejects(
    getPipelineCareerReadiness(
      "test-access-token",
      undefined,
      async () => Response.json({
        pipeline_run_id: 12,
        resume_id: 5,
        completed_at: null,
        predicted_class: "developing",
        class_probabilities: { developing: 0.82 },
        model_version: null,
        model_type: null,
        is_experimental: false,
        is_ood: false,
        ood_warnings: [],
        pipeline_warnings: [],
        training_sample_count: 120.5,
        training_class_distribution: { developing: 80 },
        feature_values: {},
        feature_diagnostics: {},
        limitations: [],
      }),
    ),
    /invalid career-readiness response/i,
  );
});

test("learning roadmap accepts integer and null skill counts", async () => {
  const validRoadmap = {
    pipeline_run_id: 12,
    target_occupation_title: "Software Developer",
    target_occupation_uri: null,
    total_roadmap_skills: 8,
    total_estimated_weeks: "12 weeks",
    phases: [],
    disclaimers: [],
  };

  const integerResult = await getPipelineLearningRoadmap(
    "test-access-token",
    undefined,
    async () => Response.json(validRoadmap),
  );

  assert.equal(integerResult.total_roadmap_skills, 8);

  const nullResult = await getPipelineLearningRoadmap(
    "test-access-token",
    undefined,
    async () => Response.json({
      ...validRoadmap,
      total_roadmap_skills: null,
    }),
  );

  assert.equal(nullResult.total_roadmap_skills, null);
});

test("learning roadmap rejects fractional skill counts", async () => {
  await assert.rejects(
    getPipelineLearningRoadmap(
      "test-access-token",
      undefined,
      async () => Response.json({
        pipeline_run_id: 12,
        target_occupation_title: "Software Developer",
        target_occupation_uri: null,
        total_roadmap_skills: 8.5,
        total_estimated_weeks: "12 weeks",
        phases: [],
        disclaimers: [],
      }),
    ),
    /invalid learning roadmap response/i,
  );
});
