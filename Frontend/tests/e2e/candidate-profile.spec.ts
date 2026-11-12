import { expect, test, type Page, type Route } from "@playwright/test";

const routes = [
  ["/", "Welcome to Road2Hire"],
  ["/resume", "Resume and candidate profile"],
  ["/jobs", "Jobs"],
  ["/skill-gap", "Your skill gap"],
  ["/career-readiness", "Career readiness"],
  ["/learning-roadmap", "Learning roadmap"],
  ["/career-assistant", "Career assistant"],
] as const;

const resume = {
  id: 31,
  user_id: 7,
  original_name: "candidate-e2e.pdf",
  stored_name: "stored-candidate-e2e.pdf",
  uploaded_at: "2026-10-20T08:00:00Z",
};

const analysis = {
  resume_id: resume.id,
  original_name: resume.original_name,
  status: "completed",
  pipeline_version: "resume-pipeline-test",
  extraction_status: "success",
  page_count: 1,
  sections: { projects: "Built a small test application." },
  detected_section_names: ["projects"],
  extracted_skills: [],
  skill_count: 0,
  skill_extraction_method: "keyword_v1",
};

const readiness = {
  pipeline_run_id: 27,
  resume_id: 12,
  completed_at: "2026-10-20T08:00:00Z",
  predicted_class: "developing",
  class_probabilities: {
    developing: 0.75,
    ready: 0.25,
  },
  model_version: "3.0.0",
  model_type: "random_forest",
  is_experimental: true,
  is_ood: false,
  ood_warnings: [],
  pipeline_warnings: [],
  training_sample_count: 120,
  training_class_distribution: {
    developing: 70,
    ready: 50,
  },
  feature_values: {
    skill_coverage: 0.75,
  },
  feature_diagnostics: {},
  limitations: ["This prediction is experimental."],
};

function jsonResponse(route: Route, status: number, payload: unknown) {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(payload),
  });
}

function deferred() {
  let resolve!: () => void;
  const promise = new Promise<void>((done) => { resolve = done; });
  return { promise, resolve };
}

function minimalPdfFixture() {
  const stream = "BT /F1 12 Tf 72 720 Td (Road2Hire browser smoke resume) Tj ET\n";
  const objects = [
    "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
    "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
    "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>\nendobj\n",
    `4 0 obj\n<< /Length ${Buffer.byteLength(stream, "ascii")} >>\nstream\n${stream}endstream\nendobj\n`,
    "5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
  ];
  let pdf = "%PDF-1.4\n";
  const offsets = [0];
  for (const object of objects) {
    offsets.push(Buffer.byteLength(pdf, "ascii"));
    pdf += object;
  }
  const xrefOffset = Buffer.byteLength(pdf, "ascii");
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  for (const offset of offsets.slice(1)) pdf += `${String(offset).padStart(10, "0")} 00000 n \n`;
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF\n`;
  return Buffer.from(pdf, "ascii");
}

async function installAuthMocks(page: Page) {
  await page.route(/\/auth\/login\/?$/, (route) => jsonResponse(route, 200, {
    access_token: "e2e-access-token",
    token_type: "bearer",
  }));
  await page.route(/\/profile\/?$/, (route) => jsonResponse(route, 200, {
    id: 7,
    name: "Avery Candidate",
    email: "avery@example.test",
  }));
  await page.route(/\/dashboard\/?$/, (route) => jsonResponse(route, 200, {
    resume_count: 2,
    skill_gap_count: 1,
    average_match_score: 75,
    latest_resume: { id: 31, original_name: resume.original_name, uploaded_at: resume.uploaded_at },
    latest_skill_gap: { id: 18, resume_id: 31, target_role: "Software Developer", match_score: 75, created_at: readiness.completed_at },
  }));
  await page.route(/\/activity(?:\?.*)?$/, (route) => jsonResponse(route, 200, {
    items: [{ type: "resume_uploaded", id: 31, timestamp: resume.uploaded_at, resume_name: resume.original_name }],
    limit: 20,
  }));
}

async function signIn(page: Page) {
  await installAuthMocks(page);
  await page.goto("/login");
  await page.getByLabel("Email").fill("avery@example.test");
  await page.getByLabel("Password").fill("e2e-test-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.locator("main").getByRole("button", { name: "Sign out" })).toBeVisible();
  await expect(page.getByText("Avery Candidate", { exact: true })).toBeVisible();
}

async function navigateFromSidebar(page: Page, name: string) {
  await page.getByRole("link", { name, exact: true }).click();
}

async function expectNoHorizontalOverflow(page: Page) {
  const dimensions = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth);
}

test("all primary routes render at desktop and mobile widths without horizontal overflow", async ({ page }) => {
  for (const [path, heading] of routes) {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(path);
    await expect(page.locator("main h1").last()).toHaveText(heading);
    await expectNoHorizontalOverflow(page);

    await page.setViewportSize({ width: 390, height: 844 });
    await expectNoHorizontalOverflow(page);
  }
});

test("protected feature pages explain the signed-out state", async ({ page }) => {
  await page.goto("/career-readiness");
  await expect(page.getByText(/Sign in to view the career-readiness assessment/)).toBeVisible();
  await expect(page.getByRole("link", { name: "Go to sign in" })).toHaveAttribute("href", "/login");
  await expect(page.getByRole("progressbar", { name: "Career readiness score" })).toHaveCount(0);

  await page.goto("/learning-roadmap");
  await expect(page.getByText(/Sign in to view and update your learning roadmap/)).toBeVisible();

  await page.goto("/resume");
  await expect(page.getByText(/Sign in before uploading or viewing saved resumes/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Upload PDF" })).toBeDisabled();
});

test("authentication session is restored after a page reload", async ({ page }) => {
  await signIn(page);

  await expect.poll(() =>
    page.evaluate(() => window.sessionStorage.getItem("road2hire_access_token"))
  ).toBe("e2e-access-token");

  await page.reload();

  await expect(page.locator("main").getByRole("button", { name: "Sign out" })).toBeVisible();
  await expect(page.getByText("Avery Candidate", { exact: true })).toBeVisible();
});

test("login form stays hidden until session restoration finishes", async ({ page }) => {
  await signIn(page);

  const restorationStarted = deferred();
  const finishRestoration = deferred();
  await page.route("**/profile", async (route) => {
    restorationStarted.resolve();
    await finishRestoration.promise;
    await jsonResponse(route, 200, {
      id: 7,
      name: "Avery Candidate",
      email: "avery@example.test",
    });
  });

  await page.reload();
  await restorationStarted.promise;
  await expect(page.getByRole("status").filter({ hasText: "Restoring your session…" })).toBeVisible();
  await expect(page.getByLabel("Email")).toHaveCount(0);
  await expect(page.getByLabel("Password")).toHaveCount(0);

  finishRestoration.resolve();
  await expect(page.locator("main").getByRole("button", { name: "Sign out" })).toBeVisible();
  await expect(page.getByText("Avery Candidate", { exact: true })).toBeVisible();
});

test("dashboard loads authenticated summary and recent activity from mocked APIs", async ({ page }) => {
  await signIn(page);
  await navigateFromSidebar(page, "Dashboard");

  const summary = page.getByLabel("Backend dashboard summary");
  await expect(summary.getByText("Saved resumes")).toBeVisible();
  await expect(summary.getByText("2", { exact: true })).toBeVisible();
  await expect(summary.getByText("Average skill match")).toBeVisible();
  await expect(page.getByText(`Resume uploaded: ${resume.original_name}`)).toBeVisible();
});

test("resume flow validates PDFs, uploads through mocked API, refreshes the list, and displays analysis", async ({ page }) => {
  let savedResumes: typeof resume[] = [];
  let uploadRequest: { authorization?: string; contentType?: string; body?: string } = {};
  let resumeListRequests = 0;
  const uploadStarted = deferred();
  const releaseUpload = deferred();

  await page.route("**/resumes", async (route) => {
    if (route.request().method() !== "GET") return route.continue();
    resumeListRequests += 1;
    await jsonResponse(route, 200, savedResumes);
  });
  await page.route("**/resume/upload", async (route) => {
    uploadRequest = {
      authorization: route.request().headers().authorization,
      contentType: route.request().headers()["content-type"],
      body: route.request().postData() ?? "",
    };
    uploadStarted.resolve();
    await releaseUpload.promise;
    savedResumes = [resume];
    await jsonResponse(route, 200, { message: "Resume uploaded.", resume });
  });
  await page.route(`**/resume/${resume.id}/analysis`, (route) => jsonResponse(route, 200, analysis));

  await signIn(page);
  await navigateFromSidebar(page, "Resume");
  await expect(page.getByText("No resumes have been uploaded yet.")).toBeVisible();

  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles({
    name: resume.original_name,
    mimeType: "application/pdf",
    buffer: minimalPdfFixture(),
  });
  await expect(page.getByRole("region", { name: "Resume upload" }).getByRole("status").filter({ hasText: /PDF selected/ })).toBeVisible();
  await expect(page.getByRole("link", { name: "Open PDF preview" })).toBeVisible();

  await page.getByRole("button", { name: "Upload PDF" }).click();
  await uploadStarted.promise;
  await expect(page.getByRole("status").filter({ hasText: /Uploading resume/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Uploading/ })).toBeDisabled();
  releaseUpload.resolve();

  await expect(page.getByText("Resume uploaded.")).toBeVisible();
  await expect(page.getByRole("listitem").getByText(resume.original_name, { exact: true })).toBeVisible();
  expect(resumeListRequests).toBeGreaterThanOrEqual(2);
  expect(uploadRequest.authorization).toBe("Bearer e2e-access-token");
  expect(uploadRequest.contentType).toContain("multipart/form-data; boundary=");
  expect(uploadRequest.body).toContain('name="user_id"');
  expect(uploadRequest.body).toContain('name="file"');

  await page.getByRole("button", { name: "Analyze", exact: true }).click();
  await expect(page.getByText(`Analysis completed for ${resume.original_name}`)).toBeVisible();
  await expect(page.getByText("Built a small test application.")).toBeVisible();
});

test("resume analysis displays a mocked backend error without crashing the page", async ({ page }) => {
  await page.route("**/resumes", (route) => jsonResponse(route, 200, [resume]));
  await page.route(`**/resume/${resume.id}/analysis`, (route) => jsonResponse(route, 422, {
    detail: "This PDF contains no extractable text. OCR is required.",
  }));

  await signIn(page);
  await navigateFromSidebar(page, "Resume");
  await expect(page.getByText(resume.original_name, { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Analyze", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "This PDF contains no extractable text. OCR is required." })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Resume analysis results" })).toBeVisible();
});

test("Jobs page creates a job and displays authenticated job-specific match evidence", async ({ page }) => {
  let savedJobs: Array<Record<string, unknown>> = [];
  const matchStarted = deferred();
  const releaseMatch = deferred();
  let createRequest: { authorization?: string; body?: unknown } = {};
  let matchRequest: { authorization?: string; body?: unknown; path?: string } = {};
  const savedJob = {
    id: 51,
    user_id: 7,
    title: "Software Developer",
    description: "Develop and maintain software applications.",
    target_occupation: "Software Developer",
    required_skills: [
      { skill_name: "Python", importance: "essential", canonical_uri: null },
      { skill_name: "SQL", importance: "optional", canonical_uri: null },
    ],
    created_at: "2026-11-12T10:00:00Z",
    updated_at: "2026-11-12T10:00:00Z",
  };

  await page.route("**/jobs", async (route) => {
    if (route.request().method() === "GET") return jsonResponse(route, 200, savedJobs);
    createRequest = {
      authorization: route.request().headers().authorization,
      body: route.request().postDataJSON(),
    };
    savedJobs = [savedJob];
    await jsonResponse(route, 201, savedJob);
  });
  await page.route(/\/jobs\/\d+\/matches\/?$/, async (route) => {
    matchRequest = {
      authorization: route.request().headers().authorization,
      body: route.request().postDataJSON(),
      path: new URL(route.request().url()).pathname,
    };
    matchStarted.resolve();
    await releaseMatch.promise;
    await jsonResponse(route, 200, {
      job: savedJob,
      run: {
        id: 81,
        status: "completed",
        selection_mode: "explicit",
        target_occupation_uri: null,
        target_occupation_title: "Software Developer",
        overall_skill_coverage_score: 0.5,
        essential_skill_coverage_score: 1,
        optional_skill_coverage_score: 0,
        readiness_class: null,
        is_ood: false,
        canonical_output: {},
        error_code: null,
        error_stage: null,
        error_message: null,
        created_at: "2026-11-12T10:00:00Z",
        completed_at: "2026-11-12T10:01:00Z",
      },
      matching_basis: "Job-specific skills are compared separately from occupation analysis.",
      job_specific_required_skills_applied: true,
      job_specific_matching: {
        job_id: 51,
        pipeline_run_id: 81,
        status: "completed",
        candidate_skill_source: "pipeline.skills.extracted_skills",
        candidate_skills_are_verified: false,
        matching_method: "semantic_skill_matcher",
        canonical_uri_matching: "not_used",
        thresholds_are_provisional: true,
        requirements: [
          { name: "Python", importance: "essential", canonical_uri: null, matched: true, candidate_skill: "Python", match_status: "confirmed_match", similarity_score: 1, evidence: "Canonical/exact equality", related_evidence: [] },
          { name: "SQL", importance: "optional", canonical_uri: null, matched: false, candidate_skill: "PostgreSQL", match_status: "related_skill", similarity_score: 0.71, evidence: "Database-related candidate skill", related_evidence: [{ candidate_skill: "PostgreSQL", similarity_score: 0.71, relation: "Database ecosystem", is_equivalent: false }] },
        ],
        scores: { essential: 1, optional: 0, overall: 0.5 },
      },
    });
  });
  await page.route("**/resumes", (route) => jsonResponse(route, 200, [resume]));

  await signIn(page);
  await navigateFromSidebar(page, "Jobs");
  await expect(page.getByRole("heading", { name: "Jobs", exact: true })).toBeVisible();
  await page.getByLabel("Job title").fill(savedJob.title);
  await page.getByLabel("Description").fill(savedJob.description);
  await page.getByLabel("Target occupation").fill(savedJob.target_occupation);
  await page.locator("#job-skill-0").fill("Python");
  await page.locator("#job-importance-0").selectOption("essential");
  await page.getByRole("button", { name: "Add a skill" }).click();
  await page.locator("#job-skill-1").fill("SQL");
  await page.locator("#job-importance-1").selectOption("optional");
  await page.getByRole("button", { name: "Save job" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Saved Software Developer." })).toBeVisible();
  expect(createRequest.authorization).toBe("Bearer e2e-access-token");
  expect(createRequest.body).toEqual({
    title: savedJob.title,
    description: savedJob.description,
    target_occupation: savedJob.target_occupation,
    required_skills: [
      { skill_name: "Python", importance: "essential" },
      { skill_name: "SQL", importance: "optional" },
    ],
  });

  await page.getByLabel("Saved resume").selectOption(String(resume.id));
  await page.getByRole("button", { name: "Run job matching" }).click();
  await matchStarted.promise;
  await expect(page.getByRole("button", { name: "Matching resume…" })).toBeDisabled();
  releaseMatch.resolve();
  await expect(page.getByRole("heading", { name: "Software Developer", exact: true })).toBeVisible();
  await expect(page.getByText("overall coverage", { exact: false })).toBeVisible();
  await expect(page.getByText("confirmed match", { exact: true })).toBeVisible();
  await expect(page.getByText("related skill", { exact: true })).toBeVisible();
  await expect(page.getByText(/Only confirmed matches count toward coverage/)).toBeVisible();
  expect(matchRequest).toEqual({
    authorization: "Bearer e2e-access-token",
    body: { resume_id: resume.id },
    path: "/jobs/51/matches",
  });
});

test("Career Readiness shows loading then the signed-in user's backend assessment", async ({ page }) => {
  const started = deferred();
  const release = deferred();
  let authorization: string | undefined;
  await page.route("**/career-readiness", async (route) => {
    authorization = route.request().headers().authorization;
    started.resolve();
    await release.promise;
    await jsonResponse(route, 200, readiness);
  });

  await signIn(page);
  await navigateFromSidebar(page, "Career Readiness");
  await started.promise;
  await expect(page.getByText("Loading your latest career-readiness prediction...")).toBeVisible();
  release.resolve();

  await expect(page.locator("#prediction-heading")).toHaveText("Developing");
  await expect(page.getByText("Class probabilities")).toBeVisible();
  await expect(page.getByRole("progressbar", { name: "Developing probability" })).toBeVisible();
  await expect(page.getByText("Pipeline run")).toBeVisible();
  await expect(page.getByText("#27", { exact: true })).toBeVisible();
  await expect(page.getByRole("main").getByText("Resume", { exact: true })).toBeVisible();
  await expect(page.getByText("#12", { exact: true })).toBeVisible();
  await expect(page.getByText("Experimental model")).toBeVisible();
  expect(authorization).toBe("Bearer e2e-access-token");
});

test("Career Readiness shows an empty state when no completed assessment exists", async ({ page }) => {
  await page.route("**/career-readiness", (route) => jsonResponse(route, 404, {
    detail: "No completed readiness assessment exists.",
  }));
  await signIn(page);
  await navigateFromSidebar(page, "Career Readiness");
  await expect(page.getByRole("heading", { name: "No completed readiness assessment yet" })).toBeVisible();
  await expect(page.getByText("Complete a Skill Gap analysis first. Career readiness becomes available after the AI pipeline completes successfully.")).toBeVisible();
});
test("Career Readiness displays a backend error", async ({ page }) => {
  await page.route("**/career-readiness", (route) => jsonResponse(route, 503, { detail: "Assessment temporarily unavailable" }));
  await signIn(page);
  await navigateFromSidebar(page, "Career Readiness");
  await expect(page.getByRole("heading", { name: "Career readiness could not be loaded" })).toBeVisible();
  await expect(page.getByText("Assessment temporarily unavailable")).toBeVisible();
});

const roadmapFixture = (skillName: string, taskId: number, status: string, progress: number) => ({
  pipeline_run_id: 27,
  target_occupation_title: "Software Developer",
  target_occupation_uri: null,
  total_roadmap_skills: 1,
  total_estimated_weeks: "2",
  phases: [
    {
      phase_number: 1,
      phase_name: "Foundations",
      description: "Build the foundations for the target occupation.",
      estimated_weeks: "2",
      items: [
        {
          logical_item_key: skillName.toLowerCase(),
          roadmap_phase_number: 1,
          roadmap_phase_name: "Foundations",
          skill_name: skillName,
          skill_uri: null,
          priority: "high",
          roadmap_item_data: {},
          current_status: null,
          importance_rationale: null,
          learning_outcome: null,
          suggested_activities: [],
          practical_project: null,
          estimated_duration_weeks: "2",
          prerequisites: [],
          completion_criteria: null,
          resource_categories: [],
          status,
          progress,
          task_id: taskId,
          updated_at: "2026-10-20T08:15:00Z",
        },
      ],
    },
  ],
  disclaimers: [],
});

test("Learning Roadmap maps backend task states and refreshes after a progress update", async ({ page }) => {
  let progress = 20;
  const patchRequest: { method?: string; authorization?: string; body?: string; path?: string } = {};
  let getCount = 0;
  const patchStarted = deferred();
  const releasePatch = deferred();

  await page.route("http://127.0.0.1:8001/learning-roadmap**", async (route) => {
    getCount += 1;
    await jsonResponse(route, 200, roadmapFixture("Java", 41, "in_progress", progress));
  });
  await page.route("**/tasks/41", async (route) => {
    patchRequest.method = route.request().method();
    patchRequest.authorization = route.request().headers().authorization;
    patchRequest.body = route.request().postData() ?? "";
    patchRequest.path = new URL(route.request().url()).pathname;
    patchStarted.resolve();
    await releasePatch.promise;
    progress = 65;
    await jsonResponse(route, 200, {
      id: 41,
      pipeline_run_id: 27,
      logical_item_key: "java",
      roadmap_phase_number: 1,
      roadmap_phase_name: "Foundations",
      skill_name: "Java",
      skill_uri: null,
      priority: "high",
      status: "in_progress",
      progress,
      roadmap_item_data: {},
      updated_at: "2026-10-20T08:15:00Z",
    });
  });

  await signIn(page);
  await navigateFromSidebar(page, "Learning Roadmap");
  await expect(page.getByText("Task ID 41")).toBeVisible();
  await expect(page.locator("ol").getByText("In progress", { exact: true }).first()).toBeVisible();
  await expect(page.getByRole("progressbar", { name: "Java task progress" })).toHaveAttribute("aria-valuenow", "20");

  await page.getByLabel("Progress for Java").fill("65");
  await page.getByRole("button", { name: "Save progress" }).click();
  await patchStarted.promise;
  await expect(page.getByRole("button", { name: "Saving..." })).toBeDisabled();
  releasePatch.resolve();

  await expect(page.getByRole("progressbar", { name: "Java task progress" })).toHaveAttribute("aria-valuenow", "65");
  expect(getCount).toBe(2);
  expect(patchRequest).toEqual({
    method: "PATCH",
    authorization: "Bearer e2e-access-token",
    body: JSON.stringify({ status: "in_progress", progress: 65 }),
    path: "/tasks/41",
  });
});

test("Learning Roadmap explains when no skill-gap analysis exists", async ({ page }) => {
  await page.route("**/learning-roadmap", (route) => jsonResponse(route, 404, {
    detail: "No completed learning roadmap exists.",
  }));
  await signIn(page);
  await navigateFromSidebar(page, "Learning Roadmap");
  await expect(page.getByRole("heading", { name: "No completed analysis found" })).toBeVisible();
});

test("Learning Roadmap validates progress values before submitting", async ({ page }) => {
  await page.route("**/learning-roadmap", (route) => jsonResponse(route, 200,
    roadmapFixture("SQL", 42, "not_started", 0),
  ));
  await signIn(page);
  await navigateFromSidebar(page, "Dashboard");
  await navigateFromSidebar(page, "Learning Roadmap");
  await page.getByLabel("Progress for SQL").fill("101");
  await page.getByRole("button", { name: "Save progress" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Enter a whole-number progress value from 0 to 100" })).toBeVisible();
});

test("Learning Roadmap displays a backend error", async ({ page }) => {
  await page.route("**/learning-roadmap", (route) => jsonResponse(route, 503, { detail: "Roadmap temporarily unavailable" }));
  await signIn(page);
  await navigateFromSidebar(page, "Learning Roadmap");
  await expect(page.getByRole("heading", { name: "Learning roadmap could not be loaded" })).toBeVisible();
  await expect(page.getByText("Roadmap temporarily unavailable")).toBeVisible();
});

test("live skill-gap analysis shows loading and renders the mocked backend result", async ({ page }) => {
  const started = deferred();
  const release = deferred();
  let authorization: string | undefined;
  let requestMethod: string | undefined;
  let requestBody: unknown;

  await page.route("**/resumes", (route) => jsonResponse(route, 200, [resume]));
  await page.route(/\/skill-gaps\/analyze\/?$/, async (route) => {
    authorization = route.request().headers().authorization;
    requestMethod = route.request().method();
    requestBody = route.request().postDataJSON();

    started.resolve();
    await release.promise;

    await jsonResponse(route, 200, {
      pipeline_run_id: 27,
      status: "completed",
      matching_basis: "Skills were compared with the target occupation.",
      warnings: [],
      target_occupation: {
        occupation_label: "Software Developer",
      },
      skill_gap: {
        matched_skills: [{ candidate_skill: "Java" }],
        partially_matched_skills: [],
        missing_essential_skills: [{ target_skill: "SQL" }],
        missing_optional_skills: [],
      },
      learning_roadmap: null,
      knowledge_graph: null,
      error: null,
    });
  });

  await signIn(page);
  await navigateFromSidebar(page, "Skill Gap");
  await page.getByLabel("Saved resume").selectOption(String(resume.id));
  await page.getByRole("textbox", { name: "Target occupation" }).fill("Software Developer");
  await page.getByRole("button", { name: "Run AI analysis" }).click();

  await started.promise;
  await expect(page.getByRole("status").filter({
    hasText: /Running the unified AI pipeline/,
  })).toBeVisible();

  release.resolve();

  await expect(page.getByRole("heading", {
    name: "Software Developer",
    exact: true,
  })).toBeVisible();
  await expect(page.getByText("Java", { exact: true })).toBeVisible();
  await expect(page.getByRole("listitem").filter({ hasText: /^SQL$/ })).toBeVisible();

  expect(authorization).toBe("Bearer e2e-access-token");
  expect(requestMethod).toBe("POST");
  expect(requestBody).toEqual({
    resume_id: resume.id,
    target_occupation: "Software Developer",
  });
});

test("skill-gap API errors are displayed without crashing the page", async ({ page }) => {
  await page.route("**/resumes", (route) => jsonResponse(route, 200, [resume]));
  await page.route(/\/skill-gaps\/analyze\/?$/, (route) => jsonResponse(route, 503, {
    detail: "Skill-gap analysis temporarily unavailable",
  }));

  await signIn(page);
  await navigateFromSidebar(page, "Skill Gap");
  await page.getByLabel("Saved resume").selectOption(String(resume.id));
  await page.getByRole("textbox", { name: "Target occupation" }).fill("Software Developer");
  await page.getByRole("button", { name: "Run AI analysis" }).click();

  await expect(page.getByRole("alert").filter({
    hasText: "Skill-gap analysis temporarily unavailable",
  })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Your skill gap" })).toBeVisible();
});

test("Career Assistant remains a local demo and does not send messages to an AI service", async ({ page }) => {
  const assistantRequests: string[] = [];
  page.on("request", (request) => {
    if (/\/assistant\/messages|openai|azure|anthropic/i.test(request.url())) assistantRequests.push(request.url());
  });

  await page.goto("/career-assistant");
  await expect(page.getByText("Demonstration mode")).toBeVisible();
  await page.getByLabel("Your message").fill("Which skill gap should I focus on first?");
  await page.getByRole("button", { name: /Send/ }).click();
  await expect(page.getByText("Demo response").first()).toBeVisible();
  expect(assistantRequests).toEqual([]);
});

test("skill filters preserve the no-results empty state", async ({ page }) => {
  await page.goto("/skill-gap");
  await page.getByRole("button", { name: "Medium priority" }).click();
  await page.getByLabel("Filter by category").selectOption("Career Skills");
  await expect(page.getByText(/No skills match both filters/)).toBeVisible();
  await expect(page.getByText("0 skills", { exact: true })).toBeVisible();
});
