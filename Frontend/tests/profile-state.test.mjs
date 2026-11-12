import assert from "node:assert/strict";
import test from "node:test";
import {
  sampleMetrics,
  sampleReadinessCategories,
  sampleRoadmapCompletions,
  sampleRoadmapRecommendations,
  sampleSkills,
} from "../app/data/sample-data.ts";
import {
  calculateRoadmapProgress,
  applyExtractionPayloadToCandidateProfile,
  completeRoadmapItem,
  createInitialCandidateProfile,
  getRoadmapPhases,
  replaceRoadmapRecommendations,
  resetResumeMetadata,
  updateResumeMetadata,
} from "../components/profile/candidate-profile-state.ts";
import {
  createResumeExtractedProvenance,
  extractionContractVersion,
  isValidConfidence,
  isVerifiedExtractedField,
  mapExtractionStatusToResumeStatus,
  validateResumeExtractionPayload,
} from "../components/profile/resume-extraction-contract.ts";
import { MAX_RESUME_BYTES, validateResumeFile } from "../components/profile/resume-upload-service.ts";

test("resume upload validation accepts supported files and rejects invalid type, empty, and oversized files", () => {
  assert.equal(validateResumeFile({ name: "candidate.PDF", size: 2048 }), null);
  assert.match(validateResumeFile({ name: "candidate.docx", size: 2048 }), /PDF file/);
  assert.match(validateResumeFile({ name: "candidate.pdf", size: 2048, type: "text/plain" }), /recognized as a PDF/);
  assert.match(validateResumeFile({ name: "candidate.exe", size: 2048 }), /not supported/);
  assert.match(validateResumeFile({ name: "candidate.pdf", size: 0 }), /empty/);
  assert.match(validateResumeFile({ name: "candidate.pdf", size: MAX_RESUME_BYTES + 1 }), /5 MiB/);
});

function createProfile(overrides = {}) {
  return createInitialCandidateProfile({
    targetRole: "Frontend Developer",
    targetRoleProvenance: { kind: "sample", label: "Road2Hire demo profile" },
    skills: sampleSkills,
    readiness: {
      overall: sampleMetrics.careerReadiness,
      interview: sampleMetrics.interviewReadiness,
      status: "sample",
      provenance: sampleMetrics.provenance,
      categories: sampleReadinessCategories,
    },
    roadmap: {
      recommendations: sampleRoadmapRecommendations,
      completions: sampleRoadmapCompletions,
      status: "sample",
      sourceFingerprint: null,
      provenance: sampleMetrics.provenance,
    },
    analysis: {
      status: "sample",
      sourceFingerprint: null,
      version: 1,
      provenance: sampleMetrics.provenance,
    },
    ...overrides,
  });
}

function createValidExtractionPayload(overrides = {}) {
  const provenance = createResumeExtractedProvenance("sha256:phase8", "extractor-2026-10");
  return {
    contractVersion: extractionContractVersion,
    extractionVersion: "extractor-2026-10",
    sourceFingerprint: "sha256:phase8",
    status: "partial",
    profileResumeStatus: "ready",
    profileAnalysisStatus: "insufficient-data",
    provenance,
    candidate: {
      name: { state: "present", value: "Avery Candidate", confidence: 1, evidence: [{ section: "contact", page: 1, snippet: "Avery Candidate" }] },
      email: { state: "missing" },
      phone: { state: "ambiguous", value: "555-0100", confidence: 0.4 },
      location: { state: "rejected", value: "Maybe City", rejectionReason: "Conflicting locations found." },
      links: [{ state: "present", value: "https://example.test", confidence: 0.8 }],
    },
    education: [
      {
        id: "education-1",
        institution: { state: "present", value: "Central College", confidence: 0.9 },
        degree: { state: "present", value: "BS", confidence: 0.8 },
        fieldOfStudy: { state: "missing" },
        dates: {
          start: { state: "present", value: { value: "2020", precision: "year" } },
          end: { state: "present", value: { value: "2024-05", precision: "month" } },
        },
        provenance,
      },
    ],
    experience: [
      {
        id: "experience-1",
        organization: { state: "present", value: "Example Co", confidence: 0.85 },
        title: { state: "present", value: "Frontend Intern", confidence: 0.8 },
        dates: {
          start: { state: "present", value: { value: "2024-06-01", precision: "day" } },
          end: { state: "missing" },
          isCurrent: true,
        },
        highlights: [{ state: "present", value: "Built UI components.", confidence: 0.75 }],
        provenance,
      },
    ],
    projects: [],
    skills: [
      {
        id: "skill-typescript",
        name: { state: "present", value: "TypeScript", confidence: 0.92 },
        normalizedName: "TypeScript",
        aliases: ["TS"],
        source: "explicit",
        provenance,
      },
      {
        id: "skill-react-inferred",
        name: { state: "present", value: "React", confidence: 0.62 },
        normalizedName: "React",
        aliases: [],
        source: "inferred_from_title",
        provenance,
      },
    ],
    certifications: [],
    languages: [],
    warnings: [{ code: "partial_section", severity: "info", message: "Some fields were not found.", fieldPath: "candidate.email" }],
    ...overrides,
  };
}

test("initial profile reuses the established demo values and resets resume metadata", () => {
  const profile = createProfile();
  const roadmapPhases = getRoadmapPhases(profile.roadmap);

  assert.equal(profile.targetRole, "Frontend Developer");
  assert.equal(profile.targetRoleProvenance.kind, "sample");
  assert.deepEqual(profile.resume, {
    fileName: null,
    fileSize: null,
    fileType: null,
    status: "empty",
    sourceFingerprint: null,
    provenance: { kind: "sample", label: "Road2Hire demo profile" },
  });
  assert.deepEqual(profile.skills, sampleSkills);
  assert.equal(profile.skills.every((skill) => skill.provenance.kind === "sample"), true);
  assert.equal(profile.readiness.overall, sampleMetrics.careerReadiness);
  assert.equal(profile.readiness.interview, sampleMetrics.interviewReadiness);
  assert.equal(profile.readiness.status, "sample");
  assert.equal(profile.readiness.provenance.kind, "sample");
  assert.deepEqual(profile.readiness.categories, sampleReadinessCategories);
  assert.deepEqual(roadmapPhases.flatMap((phase) => phase.items).map((item) => item.id), sampleRoadmapCompletions.map((item) => item.recommendationId));
  assert.equal(profile.roadmap.provenance.kind, "sample");
  assert.equal(profile.analysis.provenance.kind, "sample");
  assert.notStrictEqual(profile.skills, sampleSkills);
  assert.notStrictEqual(profile.roadmap.recommendations, sampleRoadmapRecommendations);
  assert.notStrictEqual(profile.roadmap.recommendations[0], sampleRoadmapRecommendations[0]);
  assert.notStrictEqual(profile.roadmap.recommendations[0].recommendations[0], sampleRoadmapRecommendations[0].recommendations[0]);
});

test("resume metadata updates only supported fields and identical updates are no-ops", () => {
  const profile = createProfile();
  const selected = updateResumeMetadata(profile, {
    fileName: "candidate.pdf",
    fileSize: 2048,
    status: "selected",
    unexpected: "discard me",
  });

  assert.deepEqual(selected.resume, {
    fileName: "candidate.pdf",
    fileSize: 2048,
    fileType: null,
    status: "selected",
    sourceFingerprint: "demo:candidate.pdf:2048:unknown",
    provenance: { kind: "user_provided", updatedAt: "demo:candidate.pdf:2048:unknown" },
  });
  assert.equal(Object.hasOwn(selected.resume, "unexpected"), false);
  assert.equal(profile.resume.status, "empty");
  assert.equal(selected.analysis.sourceFingerprint, "demo:candidate.pdf:2048:unknown");
  assert.equal(selected.analysis.provenance.kind, "sample");
  assert.strictEqual(selected.skills, profile.skills);
  assert.strictEqual(selected.readiness, profile.readiness);
  assert.strictEqual(selected.roadmap, profile.roadmap);
  assert.strictEqual(updateResumeMetadata(selected, {
    fileName: "candidate.pdf",
    fileSize: 2048,
    status: "selected",
  }), selected);
});

test("reset clears only resume metadata and is itself idempotent", () => {
  const profile = updateResumeMetadata(createProfile(), {
    fileName: "candidate.pdf",
    fileSize: 2048,
    status: "sample-preview",
  });
  const reset = resetResumeMetadata(profile);

  assert.deepEqual(reset.resume, {
    fileName: null,
    fileSize: null,
    fileType: null,
    status: "empty",
    sourceFingerprint: null,
    provenance: { kind: "sample", label: "Road2Hire demo profile" },
  });
  assert.equal(reset.analysis.sourceFingerprint, null);
  assert.strictEqual(reset.skills, profile.skills);
  assert.strictEqual(reset.readiness, profile.readiness);
  assert.strictEqual(reset.roadmap, profile.roadmap);
  assert.strictEqual(resetResumeMetadata(reset), reset);
});

test("roadmap completion immutably updates one task and duplicate or unknown titles are no-ops", () => {
  const profile = createProfile();
  const title = "Type-safe application features";
  const completed = completeRoadmapItem(profile, title);
  const completedItem = getRoadmapPhases(completed.roadmap).flatMap((phase) => phase.items).find((item) => item.title === title);
  const originalItem = getRoadmapPhases(profile.roadmap).flatMap((phase) => phase.items).find((item) => item.title === title);

  assert.deepEqual({ status: completedItem.status, progress: completedItem.progress }, { status: "Completed", progress: 100 });
  assert.deepEqual({ status: originalItem.status, progress: originalItem.progress }, { status: "In progress", progress: 55 });
  assert.notStrictEqual(completed, profile);
  assert.notStrictEqual(completed.roadmap.completions, profile.roadmap.completions);
  assert.strictEqual(completed.roadmap.recommendations, profile.roadmap.recommendations);
  assert.strictEqual(completeRoadmapItem(completed, title), completed);
  assert.strictEqual(completeRoadmapItem(completed, "missing task"), completed);
});

test("shared roadmap progress advances for multiple completions without duplicate inflation", () => {
  const profile = createProfile();
  const once = completeRoadmapItem(profile, "Type-safe application features");
  const twice = completeRoadmapItem(once, "Routing and server rendering");
  const duplicate = completeRoadmapItem(twice, "Routing and server rendering");

  assert.equal(calculateRoadmapProgress(profile.roadmap), 23);
  assert.equal(calculateRoadmapProgress(once.roadmap), 28);
  assert.equal(calculateRoadmapProgress(twice.roadmap), 38);
  assert.equal(calculateRoadmapProgress(duplicate.roadmap), 38);
  assert.strictEqual(duplicate, twice);
});

test("empty profile collections and roadmap progress are safe", () => {
  const profile = createProfile({
    skills: [],
    readiness: { overall: 0, interview: 0, status: "insufficient-data", provenance: sampleMetrics.provenance, categories: [] },
    roadmap: { recommendations: [], completions: [], status: "insufficient-data", sourceFingerprint: null, provenance: sampleMetrics.provenance },
  });
  const selected = updateResumeMetadata(profile, {
    fileName: "empty-profile.pdf",
    fileSize: 1,
    status: "selected",
  });

  assert.deepEqual(profile.skills, []);
  assert.deepEqual(profile.readiness.categories, []);
  assert.deepEqual(getRoadmapPhases(profile.roadmap), []);
  assert.equal(calculateRoadmapProgress(profile.roadmap), 0);
  assert.strictEqual(completeRoadmapItem(profile, "anything"), profile);
  assert.deepEqual(selected.skills, []);
  assert.deepEqual(selected.readiness.categories, []);
  assert.deepEqual(getRoadmapPhases(selected.roadmap), []);
  assert.deepEqual(resetResumeMetadata(profile).resume, {
    fileName: null,
    fileSize: null,
    fileType: null,
    status: "empty",
    sourceFingerprint: null,
    provenance: { kind: "sample", label: "Road2Hire demo profile" },
  });
});

test("roadmap regeneration preserves completion only for matching stable recommendation ids", () => {
  const profile = completeRoadmapItem(createProfile(), "Type-safe application features");
  const regenerated = replaceRoadmapRecommendations(profile, [
    {
      phase: "01",
      name: "Frontend foundations",
      timeframe: "Weeks 1-3",
      recommendations: [
        sampleRoadmapRecommendations[0].recommendations[1],
        {
          id: "brand-new-task",
          title: "Brand new task",
          skill: "New skill",
          duration: "2 hours",
          statusDetail: "sample",
          provenance: sampleMetrics.provenance,
        },
      ],
    },
  ]);
  const items = getRoadmapPhases(regenerated.roadmap).flatMap((phase) => phase.items);

  assert.deepEqual(items.map((item) => ({ id: item.id, status: item.status, progress: item.progress })), [
    { id: "frontend-foundations-type-safe-features", status: "Completed", progress: 100 },
    { id: "brand-new-task", status: "Upcoming", progress: 0 },
  ]);
  assert.equal(regenerated.roadmap.completions.some((completion) => completion.recommendationId === "frontend-foundations-react-patterns"), false);
});

test("sample values are never represented as resume-extracted facts", () => {
  const selected = updateResumeMetadata(createProfile(), {
    fileName: "candidate.pdf",
    fileSize: 2048,
    fileType: "application/pdf",
    status: "sample-preview",
  });

  assert.equal(selected.resume.provenance.kind, "user_provided");
  assert.equal(selected.skills.every((skill) => skill.provenance.kind === "sample"), true);
  assert.equal(selected.readiness.provenance.kind, "sample");
  assert.equal(selected.readiness.categories.every((category) => category.provenance.kind === "sample"), true);
  assert.equal(selected.roadmap.provenance.kind, "sample");
  assert.equal(getRoadmapPhases(selected.roadmap).flatMap((phase) => phase.items).every((item) => item.provenance.kind === "sample"), true);
});

test("resume extraction contract examples preserve version, provenance, and evidence boundaries", () => {
  const provenance = createResumeExtractedProvenance("sha256:demo", "extractor-2026-10");
  const result = {
    contractVersion: extractionContractVersion,
    extractionVersion: "extractor-2026-10",
    sourceFingerprint: "sha256:demo",
    status: "partial",
    profileResumeStatus: mapExtractionStatusToResumeStatus("partial"),
    profileAnalysisStatus: "insufficient-data",
    provenance,
    candidate: {
      name: {
        state: "present",
        value: "Avery Candidate",
        confidence: 0.96,
        evidence: [{ section: "contact", page: 1, label: "resume header", snippet: "Avery Candidate" }],
      },
      email: { state: "missing" },
      phone: { state: "ambiguous", confidence: 0.42, warnings: [{ code: "ambiguous_field", severity: "warning", message: "Multiple phone-like values found.", fieldPath: "candidate.phone" }] },
      location: { state: "missing" },
      links: [],
    },
    education: [
      {
        id: "education-1",
        institution: { state: "present", value: "Central College", confidence: 0.88 },
        degree: { state: "present", value: "BS", confidence: 0.8 },
        fieldOfStudy: { state: "missing" },
        dates: {
          start: { state: "present", value: { value: "2020", precision: "year" } },
          end: { state: "present", value: { value: "2024-05", precision: "month" } },
        },
        provenance,
      },
    ],
    experience: [],
    projects: [],
    skills: [
      {
        id: "skill-react",
        name: { state: "present", value: "React", confidence: 0.93 },
        normalizedName: "React",
        aliases: ["React.js"],
        source: "explicit",
        provenance,
      },
    ],
    certifications: [],
    languages: [],
    warnings: [{ code: "partial_section", severity: "info", message: "Education field of study was not found.", fieldPath: "education[0].fieldOfStudy" }],
  };

  assert.equal(result.contractVersion, "resume-extraction.v1");
  assert.deepEqual(result.provenance, { kind: "resume_extracted", sourceFingerprint: "sha256:demo", extractionVersion: "extractor-2026-10" });
  assert.equal(result.profileResumeStatus, "ready");
  assert.equal(result.profileAnalysisStatus, "insufficient-data");
  assert.equal(isVerifiedExtractedField(result.candidate.name), true);
  assert.equal(isVerifiedExtractedField(result.candidate.email), false);
  assert.equal(result.education[0].dates.start.value.precision, "year");
  assert.equal(result.education[0].dates.end.value.precision, "month");
});

test("missing, ambiguous, and rejected extraction fields do not become verified facts", () => {
  assert.equal(isVerifiedExtractedField({ state: "missing" }), false);
  assert.equal(isVerifiedExtractedField({ state: "ambiguous", value: "React", confidence: 0.5 }), false);
  assert.equal(isVerifiedExtractedField({ state: "rejected", value: "Definitely Maybe", rejectionReason: "Conflicts with validation rules." }), false);
  assert.equal(isVerifiedExtractedField({ state: "present", value: "TypeScript", confidence: 1 }), true);
  assert.equal(isVerifiedExtractedField({ state: "present", value: "TypeScript", confidence: 1.1 }), false);
});

test("extracted skills distinguish explicit evidence from inference", () => {
  const provenance = createResumeExtractedProvenance("sha256:skills", "extractor-2026-10");
  const explicitSkill = {
    id: "skill-typescript",
    name: { state: "present", value: "TypeScript", confidence: 0.91 },
    normalizedName: "TypeScript",
    aliases: ["TS"],
    source: "explicit",
    provenance,
  };
  const inferredSkill = {
    id: "skill-react",
    name: { state: "present", value: "React", confidence: 0.61 },
    normalizedName: "React",
    aliases: [],
    source: "inferred_from_title",
    provenance,
  };

  assert.equal(explicitSkill.source, "explicit");
  assert.equal(inferredSkill.source, "inferred_from_title");
  assert.equal(isVerifiedExtractedField(inferredSkill.name), true);
});

test("confidence validation accepts only finite values on the documented 0 to 1 scale", () => {
  assert.equal(isValidConfidence(undefined), true);
  assert.equal(isValidConfidence(0), true);
  assert.equal(isValidConfidence(0.5), true);
  assert.equal(isValidConfidence(1), true);
  assert.equal(isValidConfidence(-0.01), false);
  assert.equal(isValidConfidence(1.01), false);
  assert.equal(isValidConfidence(Number.NaN), false);
  assert.equal(isValidConfidence(Number.POSITIVE_INFINITY), false);
});

test("extraction payload validation accepts a valid partial payload and maps safe profile status", () => {
  const payload = createValidExtractionPayload();
  const validation = validateResumeExtractionPayload(payload);

  assert.equal(validation.ok, true);
  assert.equal(validation.value.status, "partial");
  assert.equal(mapExtractionStatusToResumeStatus(validation.value.status), "ready");
  assert.equal(validation.value.experience[0].dates.end.state, "missing");
  assert.equal(validation.value.experience[0].dates.isCurrent, true);
});

test("extraction payload validation reports wrong versions, bad statuses, and malformed collections", () => {
  const validation = validateResumeExtractionPayload(createValidExtractionPayload({
    contractVersion: "resume-extraction.v2",
    status: "done",
    skills: "TypeScript",
  }));

  assert.equal(validation.ok, false);
  assert.deepEqual(validation.issues.map((issue) => issue.path), ["$.contractVersion", "$.status", "$.skills"]);
  assert.deepEqual(validation.issues.map((issue) => issue.code), ["invalid_contract_version", "invalid_status", "invalid_type"]);
});

test("extraction validation rejects invalid field combinations, confidence, evidence, and warnings", () => {
  const payload = createValidExtractionPayload({
    candidate: {
      name: { state: "present", confidence: Number.POSITIVE_INFINITY, evidence: [{ section: "summary", page: 0 }] },
      email: { state: "missing", value: "avery@example.test" },
      phone: { state: "rejected" },
      location: { state: "absent" },
      links: [],
    },
    warnings: [{ code: "mystery", severity: "loud", message: 12 }],
  });
  const validation = validateResumeExtractionPayload(payload);

  assert.equal(validation.ok, false);
  assert.equal(validation.issues.some((issue) => issue.path === "$.candidate.name.value" && issue.code === "invalid_field_state"), true);
  assert.equal(validation.issues.some((issue) => issue.path === "$.candidate.name.confidence" && issue.code === "invalid_confidence"), true);
  assert.equal(validation.issues.some((issue) => issue.path === "$.candidate.name.evidence[0].section" && issue.code === "invalid_evidence"), true);
  assert.equal(validation.issues.some((issue) => issue.path === "$.candidate.email.value" && issue.code === "invalid_field_state"), true);
  assert.equal(validation.issues.some((issue) => issue.path === "$.candidate.phone.rejectionReason" && issue.code === "invalid_field_state"), true);
  assert.equal(validation.issues.some((issue) => issue.path === "$.candidate.location.state" && issue.code === "invalid_field_state"), true);
  assert.equal(validation.issues.some((issue) => issue.path === "$.warnings[0].code" && issue.code === "invalid_warning"), true);
});

test("extraction validation rejects invalid skill sources and current roles with present end dates", () => {
  const payload = createValidExtractionPayload({
    experience: [
      {
        ...createValidExtractionPayload().experience[0],
        dates: {
          start: { state: "present", value: { value: "2024", precision: "decade" } },
          end: { state: "present", value: { value: "2025", precision: "year" } },
          isCurrent: true,
        },
      },
    ],
    skills: [
      {
        ...createValidExtractionPayload().skills[0],
        id: "",
        source: "guessed",
      },
    ],
  });
  const validation = validateResumeExtractionPayload(payload);

  assert.equal(validation.ok, false);
  assert.equal(validation.issues.some((issue) => issue.path === "$.experience[0].dates.start.value.precision" && issue.code === "invalid_date_precision"), true);
  assert.equal(validation.issues.some((issue) => issue.path === "$.experience[0].dates.end" && issue.code === "invalid_field_state"), true);
  assert.equal(validation.issues.some((issue) => issue.path === "$.skills[0].id" && issue.code === "invalid_type"), true);
  assert.equal(validation.issues.some((issue) => issue.path === "$.skills[0].source" && issue.code === "invalid_skill_source"), true);
});

test("safe extraction mapping stores only present facts and keeps inferred skills out of verified skills", () => {
  const selected = updateResumeMetadata(createProfile(), {
    fileName: "candidate.pdf",
    fileSize: 1024,
    fileType: "application/pdf",
    status: "selected",
    sourceFingerprint: "sha256:phase8",
  });
  const mapped = applyExtractionPayloadToCandidateProfile(selected, createValidExtractionPayload());

  assert.equal(mapped.accepted, true);
  assert.equal(mapped.profile.resume.status, "ready");
  assert.equal(mapped.profile.resume.provenance.kind, "resume_extracted");
  assert.equal(mapped.profile.analysis.status, "insufficient-data");
  assert.equal(mapped.profile.extraction.candidate.name, "Avery Candidate");
  assert.equal(mapped.profile.extraction.candidate.email, null);
  assert.equal(mapped.profile.extraction.candidate.phone, null);
  assert.equal(mapped.profile.extraction.candidate.location, null);
  assert.deepEqual(mapped.profile.extraction.candidate.links, ["https://example.test"]);
  assert.deepEqual(mapped.profile.extraction.skills.explicit.map((skill) => skill.name), ["TypeScript"]);
  assert.deepEqual(mapped.profile.extraction.skills.inferred.map((skill) => skill.name), ["React"]);
  assert.equal(mapped.profile.skills.every((skill) => skill.provenance.kind === "sample"), true);
});

test("safe extraction mapping rejects stale fingerprints and invalidates prior extraction after replacement", () => {
  const selected = updateResumeMetadata(createProfile(), {
    fileName: "candidate.pdf",
    fileSize: 1024,
    fileType: "application/pdf",
    status: "selected",
    sourceFingerprint: "sha256:phase8",
  });
  const mapped = applyExtractionPayloadToCandidateProfile(selected, createValidExtractionPayload());
  const replacement = updateResumeMetadata(mapped.profile, {
    fileName: "replacement.pdf",
    fileSize: 2048,
    fileType: "application/pdf",
    status: "selected",
    sourceFingerprint: "sha256:replacement",
  });
  const stale = applyExtractionPayloadToCandidateProfile(replacement, createValidExtractionPayload());

  assert.equal(replacement.extraction.status, "stale");
  assert.deepEqual(replacement.extraction.skills.explicit, []);
  assert.equal(stale.accepted, false);
  assert.equal(stale.issues[0].path, "$.sourceFingerprint");
  assert.equal(stale.profile.resume.sourceFingerprint, "sha256:replacement");
});
