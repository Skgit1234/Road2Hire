import { expect, test, type Page, type Route } from "@playwright/test";

const routes = [
  ["/", "Welcome to Road2Hire"],
  ["/resume", "Resume and candidate profile"],
  ["/jobs", "Jobs"],
  ["/skill-gap", "Skill gap dashboard"],
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

async function installAuthMocks(page: Page, emptyDashboard = false) {
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
    latest_skill_gap: { id: 18, resume_id: 31, target_role: "Software Developer", match_score: null, created_at: readiness.completed_at },
  }));
  await page.route(/\/activity(?:\?.*)?$/, (route) => jsonResponse(route, 200, {
    items: [
      { type: "resume_uploaded", id: 31, timestamp: resume.uploaded_at, resume_name: resume.original_name },
      { type: "skill_gap_analyzed", id: 18, timestamp: readiness.completed_at, resume_id: 31, target_role: "Software Developer", match_score: null },
    ],
    limit: 20,
  }));
  await page.route(/\/career-readiness\/runs\/18$/, (route) => jsonResponse(route, 200, { ...readiness, pipeline_run_id: 18 }));
  await page.route(/\/learning-roadmap\/runs\/18$/, (route) => jsonResponse(route, 200, {
    pipeline_run_id: 18,
    target_occupation_title: "Software Developer",
    target_occupation_uri: null,
    total_roadmap_skills: emptyDashboard ? 0 : 1,
    total_estimated_weeks: null,
    phases: emptyDashboard ? [] : [{ phase_number: 1, phase_name: "Core skills", description: "Build foundational skills", estimated_weeks: "2", items: [{ logical_item_key: "java", roadmap_phase_number: 1, roadmap_phase_name: "Core skills", skill_name: "Java", skill_uri: null, priority: "high", roadmap_item_data: {}, current_status: null, importance_rationale: null, learning_outcome: null, suggested_activities: [], practical_project: null, estimated_duration_weeks: null, prerequisites: [], completion_criteria: null, resource_categories: [], status: "in_progress", progress: 25, task_id: 9, updated_at: "2026-10-20T10:00:00Z" }] }],
    disclaimers: [],
  }));
  await page.route(/\/skill-gaps\/runs\/18\/priorities$/, (route) => jsonResponse(route, 200, {
    pipeline_run_id: 18,
    target_occupation: { occupation_label: "Software Developer" },
    items: emptyDashboard ? [] : [{ skill_name: "Java", priority: "high" }],
  }));
  await page.route(/\/skill-gaps\/runs\/18\/knowledge-graph$/, (route) => jsonResponse(route, 200, {
    pipeline_run_id: 18,
    summary: {},
    nodes: emptyDashboard ? [] : [{ id: "missing:sql", label: "SQL", kind: "esco_skill", gap_status: "missing" }],
    relationships: emptyDashboard ? [] : [{ source: "candidate:java", target: "occupation:java", type: "matches_skill" }],
    scope: "Persisted skill graph",
  }));
}

async function signIn(page: Page, emptyDashboard = false) {
  await installAuthMocks(page, emptyDashboard);
  await page.goto("/login");
  await page.getByLabel("Email").fill("avery@example.test");
  await page.getByLabel("Password").fill("e2e-test-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.locator("main").getByRole("button", { name: "Sign out" })).toBeVisible();
  await expect(page.getByText("Avery Candidate", { exact: true })).toBeVisible();
  await expect(page.getByRole("img", { name: "Account avatar: Avery Candidate" })).toHaveText("AC");
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

test("transient session restoration failure keeps the token and allows retry", async ({ page }) => {
  await signIn(page);

  let profileChecks = 0;
  await page.unroute(/\/profile\/?$/);
  await page.route(/\/profile\/?$/, async (route) => {
    profileChecks += 1;
    // Next dev's React Strict Mode can start restoration twice on a full reload.
    if (profileChecks <= 2) {
      return jsonResponse(route, 503, { detail: "Temporarily unavailable" });
    }
    return jsonResponse(route, 200, {
      id: 7,
      name: "Avery Candidate",
      email: "avery@example.test",
    });
  });

  await page.reload();

  await expect(page.getByRole("heading", { name: "Session could not be restored" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Retry session check" })).toBeVisible();
  await expect.poll(() =>
    page.evaluate(() => window.sessionStorage.getItem("road2hire_access_token"))
  ).toBe("e2e-access-token");

  await page.getByRole("button", { name: "Retry session check" }).click();
  await expect(page.locator("main").getByRole("button", { name: "Sign out" })).toBeVisible();
  await expect(page.getByText("Avery Candidate", { exact: true })).toBeVisible();
  expect(profileChecks).toBeGreaterThanOrEqual(3);
});

test("rejected session token is removed and returns to sign-in", async ({ page }) => {
  await signIn(page);
  await page.unroute(/\/profile\/?$/);
  await page.route(/\/profile\/?$/, (route) =>
    jsonResponse(route, 401, { detail: "Invalid or expired token" }));

  await page.reload();

  await expect(page.getByLabel("Email")).toBeVisible();
  await expect.poll(() =>
    page.evaluate(() => window.sessionStorage.getItem("road2hire_access_token"))
  ).toBeNull();
});

test("forbidden session token is removed and returns to sign-in", async ({ page }) => {
  await signIn(page);
  await page.unroute(/\/profile\/?$/);
  await page.route(/\/profile\/?$/, (route) =>
    jsonResponse(route, 403, { detail: "Session is not permitted" }));

  await page.reload();

  await expect(page.getByLabel("Email")).toBeVisible();
  await expect.poll(() =>
    page.evaluate(() => window.sessionStorage.getItem("road2hire_access_token"))
  ).toBeNull();
});

test("network failure during session restoration preserves the saved token", async ({ page }) => {
  await signIn(page);
  await page.unroute(/\/profile\/?$/);
  await page.route(/\/profile\/?$/, (route) => route.abort("failed"));

  await page.reload();

  await expect(page.getByRole("heading", { name: "Session could not be restored" })).toBeVisible();
  await expect.poll(() =>
    page.evaluate(() => window.sessionStorage.getItem("road2hire_access_token"))
  ).toBe("e2e-access-token");
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
  await expect(page.getByRole("img", { name: "Dashboard avatar: Avery Candidate" })).toHaveText("AC");

  const summary = page.getByLabel("Account summary");
  await expect(summary.getByText("Saved resumes")).toBeVisible();
  await expect(summary.getByRole("paragraph").filter({ hasText: /^2$/ })).toBeVisible();
  await expect(summary.getByText("Average skill match")).toBeVisible();
  await expect(summary.getByText("Match score unavailable")).toBeVisible();
  await expect(page.getByText(`Resume uploaded: ${resume.original_name}`)).toBeVisible();
  await expect(page.getByText("Skill gap analyzed for Software Developer (match score unavailable)")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Career readiness", exact: true })).toBeVisible();
  await expect(page.getByText("developing", { exact: true })).toBeVisible();
  await expect(page.getByText("Java", { exact: true }).first()).toBeVisible();
  const learningTask = page.getByRole("list", { name: "Learning progress chart" }).getByRole("listitem");
  await expect(learningTask).toContainText("Java");
  await expect(learningTask).toContainText("in progress");
  await expect(learningTask).toContainText("25%");
  await expect(page.getByText("Historical readiness data is not available yet.")).toBeVisible();
  await expect(page.getByText("Matched skills", { exact: true })).toBeVisible();
  await expect(page.getByText("Missing skills", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Skill priority chart" })).toBeVisible();
  await expect(page.getByText("high", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Learning progress" })).toBeVisible();
  await expect(page.getByText("in progress (25%)")).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  await expect(page.getByRole("heading", { name: "Skill coverage chart" })).toBeVisible();
  await expectNoHorizontalOverflow(page);
});

test("dashboard visualizations show empty states when the backend has no chart data", async ({ page }) => {
  await signIn(page, true);
  await navigateFromSidebar(page, "Dashboard");
  await expect(page.getByText("Matched and missing skill data is not available for the latest analysis.")).toBeVisible();
  await expect(page.getByText("No saved roadmap priority data is available for the latest analysis.")).toBeVisible();
  await expect(page.getByText("No saved learning task progress is available.")).toBeVisible();
});

test("resume flow validates PDFs, uploads through mocked API, refreshes the list, and displays analysis", async ({ page }) => {
  let savedResumes: typeof resume[] = [];
  let savedCandidateProfile: Record<string, unknown> | null = null;
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
  await page.route(`**/resume/${resume.id}/analysis`, async (route) => {
    savedCandidateProfile = {
      id: 4,
      user_id: 7,
      resume_id: resume.id,
      skills: [{ skill: "Python", source_sections: ["skills"], occurrences: [{ section: "skills", text: "Python", start: 0, end: 6 }] }],
      education: ["BSc Computer Science"],
      experience: ["Software Developer at Example Co."],
      projects: ["Road2Hire integration"],
      certifications: ["Cloud Fundamentals"],
      updated_at: "2026-11-12T10:00:00Z",
    };
    await jsonResponse(route, 200, analysis);
  });
  await page.route("**/profile/candidate", (route) => savedCandidateProfile
    ? jsonResponse(route, 200, savedCandidateProfile)
    : jsonResponse(route, 404, { detail: "Candidate profile not found" }));

  await signIn(page);
  await navigateFromSidebar(page, "Resume");
  await expect(page.getByText("No resumes have been uploaded yet.")).toBeVisible();
  await expect(page.getByText("No candidate profile is available yet. Analyze a saved resume to populate it.")).toBeVisible();

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
  await expect(page.getByRole("region", { name: "Extracted skills" }).getByText("Python", { exact: true })).toBeVisible();
  await expect(page.getByRole("region", { name: "education" }).getByText("BSc Computer Science")).toBeVisible();
});

test("in-memory resume metadata is cleared when the authenticated user signs out", async ({ page }) => {
  await signIn(page);
  await navigateFromSidebar(page, "Resume");
  await page.locator('input[type="file"]').setInputFiles({
    name: "private-resume.pdf",
    mimeType: "application/pdf",
    buffer: minimalPdfFixture(),
  });
  await expect(page.getByText("private-resume.pdf", { exact: true })).toBeVisible();
  await navigateFromSidebar(page, "Dashboard");
  await page.locator("aside").getByRole("button", { name: "Sign out" }).click();
  await page.goto("/resume");
  await expect(page.getByText("Sign in before uploading or viewing saved resumes.")).toBeVisible();
  await expect(page.getByText("private-resume.pdf", { exact: true })).toHaveCount(0);
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
          { name: "SQL", importance: "optional", canonical_uri: null, matched: false, candidate_skill: "PostgreSQL", match_status: "related_skill", similarity_score: -0.24, evidence: "Database-related candidate skill", related_evidence: [{ candidate_skill: "PostgreSQL", similarity_score: -0.24, relation: "Database ecosystem", is_equivalent: false }] },
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
  await expect(page.getByText("cosine similarity -0.240", { exact: false })).toBeVisible();
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

  await page.route("http://127.0.0.1:8000/learning-roadmap**", async (route) => {
    getCount += 1;
    await jsonResponse(route, 200, roadmapFixture("Java", 41, "in_progress", progress));
  });
  await page.route("http://127.0.0.1:8000/tasks/41", async (route) => {
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

  await page.getByLabel("Status for SQL").selectOption("completed");
  await page.getByLabel("Progress for SQL").fill("55");
  await page.getByRole("button", { name: "Save progress" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Completed tasks must be 100%" })).toBeVisible();
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
        overall_skill_coverage_score: 0.75,
        essential_skill_coverage_score: 0.8,
        optional_skill_coverage_score: 0.6,
        matched_skills: [{ candidate_skill: "Java runtime", occupation_skill: "Java" }],
        partially_matched_skills: [{ candidate_skill: "PostgreSQL", occupation_skill: "SQL", graph_relationship: "related_skill" }],
        missing_essential_skills: [{ skill_label: "Cloud Computing" }],
        missing_optional_skills: [{ skill_label: "Communication" }],
      },
      learning_roadmap: null,
      knowledge_graph: null,
      error: null,
    });
  });
  await page.route(/\/skill-gaps\/runs\/27\/priorities\/?$/, (route) => jsonResponse(route, 200, {
    pipeline_run_id: 27,
    target_occupation: { occupation_label: "Software Developer" },
    items: [{ skill_name: "Cloud Computing", priority: "High", phase_number: 1, phase_name: "Foundations", importance_rationale: "Required for the selected occupation." }],
  }));
  await page.route(/\/skill-gaps\/runs\/27\/knowledge-graph\/?$/, (route) => jsonResponse(route, 200, {
    pipeline_run_id: 27,
    summary: { total_nodes: 4, total_edges: 2 },
    nodes: [
      { id: "candidate:java", label: "Java", kind: "candidate_skill" },
      { id: "esco:java", label: "Java", kind: "esco_skill" },
      { id: "candidate:postgres", label: "PostgreSQL", kind: "candidate_skill" },
      { id: "esco:sql", label: "SQL", kind: "esco_skill" },
    ],
    relationships: [
      { source: "candidate:java", target: "esco:java", type: "matches_skill", explanation: "Exact skill match" },
      { source: "candidate:postgres", target: "esco:sql", type: "partially_matches_skill", explanation: "Related database skill" },
    ],
    scope: "Skill-match relationships are derived from canonical matched and partially matched evidence.",
  }));

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
  await expect(page.getByText("Java", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("SQL", { exact: true })).toBeVisible();
  await expect(page.getByText("Cloud Computing", { exact: true }).first()).toBeVisible();
  const breakdown = page.getByRole("region", { name: "Skill match breakdown" });
  await expect(breakdown.getByRole("listitem").filter({ hasText: "Java runtime" }).locator("span").first()).toHaveText("Java runtime → Java");
  await expect(breakdown.getByRole("listitem").filter({ hasText: "PostgreSQL" }).locator("span").first()).toHaveText("PostgreSQL → SQL");
  await expect(breakdown.getByRole("heading", { name: "Missing essential skills" }).locator("xpath=../..").getByRole("listitem")).toContainText("Cloud Computing");
  await expect(breakdown.getByRole("heading", { name: "Missing optional skills" }).locator("xpath=../..").getByRole("listitem")).toContainText("Communication");
  await expect(page.getByText("Overall skill coverage")).toBeVisible();
  await expect(page.getByText("75%", { exact: true })).toBeVisible();
  await expect(page.getByText("80%", { exact: true })).toBeVisible();
  await expect(page.getByText("60%", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Skill priorities" })).toBeVisible();
  await expect(page.getByText("Required for the selected occupation.")).toBeVisible();
  await expect(page.getByRole("region", { name: "Interactive skill relationship graph" })).toBeVisible();
  await expect(page.getByText("partial · candidate skill", { exact: false }).first()).toBeVisible();
  const partialNode = page.getByRole("button", { name: "PostgreSQL, partial candidate skill" });
  await partialNode.focus();
  await expect(partialNode).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByText("PostgreSQL · partial · candidate skill", { exact: true })).toBeVisible();

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
  await expect(page.getByRole("heading", { name: "Skill gap dashboard" })).toBeVisible();
});

test("late priority and graph responses from an earlier run cannot replace the active run", async ({ page }) => {
  const oldRequestsStarted = deferred();
  const releaseOldResponses = deferred();
  const oldResponsesFinished = deferred();
  let oldRequestCount = 0;
  let oldResponseCount = 0;

  await page.route("**/resumes", (route) => jsonResponse(route, 200, [resume]));
  await page.route(/\/skill-gaps\/analyze\/?$/, (route) => {
    const target = route.request().postDataJSON().target_occupation;
    const isSecondRun = target === "Role B";
    return jsonResponse(route, 200, {
      pipeline_run_id: isSecondRun ? 31 : 30,
      status: "completed",
      matching_basis: "Analysis uses the selected occupation.",
      warnings: [],
      target_occupation: { occupation_label: target },
      skill_gap: {
        overall_skill_coverage_score: isSecondRun ? 0.9 : 0.4,
        essential_skill_coverage_score: isSecondRun ? 0.9 : 0.4,
        optional_skill_coverage_score: isSecondRun ? 0.9 : 0.4,
        matched_skills: [], partially_matched_skills: [], missing_essential_skills: [], missing_optional_skills: [],
      },
      learning_roadmap: null, knowledge_graph: null, error: null,
    });
  });
  await page.route(/\/skill-gaps\/runs\/(30|31)\/priorities\/?$/, async (route) => {
    const runId = Number(route.request().url().match(/runs\/(30|31)\//)?.[1]);
    if (runId === 30) {
      oldRequestCount += 1;
      if (oldRequestCount === 2) oldRequestsStarted.resolve();
      await releaseOldResponses.promise;
      await jsonResponse(route, 200, { pipeline_run_id: 30, target_occupation: null, items: [{ skill_name: "Role A priority", priority: "High" }] });
      oldResponseCount += 1;
      if (oldResponseCount === 2) oldResponsesFinished.resolve();
      return;
    }
    await jsonResponse(route, 200, { pipeline_run_id: 31, target_occupation: null, items: [{ skill_name: "Role B priority", priority: "High" }] });
  });
  await page.route(/\/skill-gaps\/runs\/(30|31)\/knowledge-graph\/?$/, async (route) => {
    const runId = Number(route.request().url().match(/runs\/(30|31)\//)?.[1]);
    if (runId === 30) {
      oldRequestCount += 1;
      if (oldRequestCount === 2) oldRequestsStarted.resolve();
      await releaseOldResponses.promise;
      await jsonResponse(route, 200, { pipeline_run_id: 30, summary: {}, nodes: [{ id: "a", label: "Role A graph", kind: "esco_skill" }], relationships: [], scope: "Run 30 graph." });
      oldResponseCount += 1;
      if (oldResponseCount === 2) oldResponsesFinished.resolve();
      return;
    }
    await jsonResponse(route, 200, { pipeline_run_id: 31, summary: {}, nodes: [{ id: "b", label: "Role B graph", kind: "esco_skill" }], relationships: [], scope: "Run 31 graph." });
  });

  await signIn(page);
  await navigateFromSidebar(page, "Skill Gap");
  await page.getByLabel("Saved resume").selectOption(String(resume.id));
  const target = page.getByRole("textbox", { name: "Target occupation" });
  await target.fill("Role A");
  await page.getByRole("button", { name: "Run AI analysis" }).click();
  await oldRequestsStarted.promise;

  await target.fill("Role B");
  await page.getByRole("button", { name: "Run AI analysis" }).click();
  await expect(page.getByRole("heading", { name: "Role B", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Role B priority" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Role B graph, neutral esco skill" })).toBeVisible();

  releaseOldResponses.resolve();
  await oldResponsesFinished.promise;
  await expect(page.getByRole("heading", { name: "Role B priority" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Role B graph, neutral esco skill" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Role A priority" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Role A graph, neutral esco skill" })).toHaveCount(0);
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

test("Skill Gap priority and category filters show the no-results state", async ({ page }) => {
  await page.route("**/resumes", (route) => jsonResponse(route, 200, [resume]));
  await page.route(/\/skill-gaps\/analyze\/?$/, (route) => jsonResponse(route, 200, {
    pipeline_run_id: 28,
    status: "completed",
    matching_basis: "Analysis uses the selected occupation.",
    warnings: [],
    target_occupation: { occupation_label: "Software Developer" },
    skill_gap: {
      overall_skill_coverage_score: 0.5,
      essential_skill_coverage_score: 0.5,
      optional_skill_coverage_score: null,
      matched_skills: [],
      partially_matched_skills: [],
      missing_essential_skills: [],
      missing_optional_skills: [],
    },
    learning_roadmap: null,
    knowledge_graph: null,
    error: null,
  }));
  await page.route(/\/skill-gaps\/runs\/28\/priorities\/?$/, (route) => jsonResponse(route, 200, {
    pipeline_run_id: 28,
    target_occupation: { occupation_label: "Software Developer" },
    items: [
      { skill_name: "TypeScript", priority: "Medium", phase_number: 1, phase_name: "Technical Skills" },
      { skill_name: "Collaboration", priority: "High", phase_number: 2, phase_name: "Career Skills" },
    ],
  }));
  await page.route(/\/skill-gaps\/runs\/28\/knowledge-graph\/?$/, (route) => jsonResponse(route, 200, {
    pipeline_run_id: 28,
    summary: {},
    nodes: [],
    relationships: [],
    scope: "No graph topology for this analysis.",
  }));

  await signIn(page);
  await navigateFromSidebar(page, "Skill Gap");
  await page.getByLabel("Saved resume").selectOption(String(resume.id));
  await page.getByRole("textbox", { name: "Target occupation" }).fill("Software Developer");
  await page.getByRole("button", { name: "Run AI analysis" }).click();
  await expect(page.getByRole("heading", { name: "Skill priorities" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Medium priority" })).toBeVisible();

  await page.getByRole("button", { name: "Medium priority" }).click();
  await page.getByLabel("Filter by category").selectOption("Career Skills");
  await expect(page.getByText(/No skills match both filters/)).toBeVisible();
  await expect(page.getByText("0 skills", { exact: true })).toBeVisible();
});

test("skill-gap dashboard retries failed graph and priority loads and handles empty data", async ({ page }) => {
  let priorityAttempts = 0;
  let graphAttempts = 0;
  await page.route("**/resumes", (route) => jsonResponse(route, 200, [resume]));
  await page.route(/\/skill-gaps\/analyze\/?$/, (route) => jsonResponse(route, 200, {
    pipeline_run_id: 29, status: "completed", matching_basis: "No requirements matched.", warnings: [],
    target_occupation: { occupation_label: "Role without matches" },
    skill_gap: { overall_skill_coverage_score: 0, essential_skill_coverage_score: 0, optional_skill_coverage_score: null, matched_skills: [], partially_matched_skills: [], missing_essential_skills: [], missing_optional_skills: [] },
    learning_roadmap: null, knowledge_graph: null, error: null,
  }));
  await page.route(/\/skill-gaps\/runs\/29\/priorities\/?$/, (route) => {
    priorityAttempts += 1;
    return priorityAttempts === 1
      ? jsonResponse(route, 503, { detail: "Priorities unavailable" })
      : jsonResponse(route, 200, { pipeline_run_id: 29, target_occupation: null, items: [] });
  });
  await page.route(/\/skill-gaps\/runs\/29\/knowledge-graph\/?$/, (route) => {
    graphAttempts += 1;
    return graphAttempts === 1
      ? jsonResponse(route, 503, { detail: "Graph unavailable" })
      : jsonResponse(route, 200, { pipeline_run_id: 29, summary: {}, nodes: [], relationships: [], scope: "No graph topology." });
  });
  await page.goto("/skill-gap");
  await signIn(page);
  await navigateFromSidebar(page, "Skill Gap");
  await page.getByLabel("Saved resume").selectOption(String(resume.id));
  await page.getByRole("textbox", { name: "Target occupation" }).fill("Role without matches");
  await page.getByRole("button", { name: "Run AI analysis" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Priorities unavailable" })).toBeVisible();
  await expect(page.getByRole("alert").filter({ hasText: "Graph unavailable" })).toBeVisible();
  await page.getByRole("button", { name: "Retry priorities" }).click();
  await page.getByRole("button", { name: "Retry graph" }).click();
  await expect(page.getByText("No graph nodes were returned for this analysis.")).toBeVisible();
  await expect(page.getByText("No priority items were returned for this analysis.")).toBeVisible();
  await expect(page.getByText("Optional skill coverage")).toBeVisible();
  await expect(page.getByText("Unavailable", { exact: true })).toBeVisible();
});
