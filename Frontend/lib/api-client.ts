
import { API_BASE_URL } from "./api-config.ts";

export type RegistrationRequest = {
  name: string;
  email: string;
  password: string;
};

export type LoginRequest = {
  email: string;
  password: string;
};

export type AuthUser = {
  id: number;
  name: string;
  email: string;
};

export type ProfileUpdate = Partial<Pick<AuthUser, "name" | "email">>;

export type AuthToken = {
  access_token: string;
  token_type: "bearer";
};

export type ResumeRecord = {
  id: number;
  user_id: number;
  original_name: string;
  stored_name: string;
  uploaded_at: string;
  download_url?: string;
};

export type CandidateProfileResponse = {
  id: number;
  user_id: number;
  resume_id: number | null;
  skills: Array<{
    skill: string;
    source_sections: string[];
    occurrences: Array<{
      section: string;
      text: string;
      start: number;
      end: number;
    }>;
  }>;
  education: string[];
  experience: string[];
  projects: string[];
  certifications: string[];
  updated_at: string;
};

export type JobSkillRequirement = {
  skill_name: string;
  importance: "essential" | "optional";
  canonical_uri: string | null;
};

export type JobCreateRequest = {
  title: string;
  description: string;
  target_occupation: string;
  required_skills: Array<
    Pick<JobSkillRequirement, "skill_name" | "importance"> & {
      canonical_uri?: string | null;
    }
  >;
};

export type JobRecord = {
  id: number;
  user_id: number;
  title: string;
  description: string;
  target_occupation: string;
  required_skills: JobSkillRequirement[];
  created_at: string;
  updated_at: string;
};

export type JobPipelineRun = {
  id: number;
  status: "pending" | "running" | "completed" | "failed";
  selection_mode: "explicit" | "auto_selected";
  target_occupation_uri: string | null;
  target_occupation_title: string | null;
  overall_skill_coverage_score: number | null;
  essential_skill_coverage_score: number | null;
  optional_skill_coverage_score: number | null;
  readiness_class: string | null;
  is_ood: boolean;
  canonical_output: Record<string, unknown>;
  error_code: string | null;
  error_stage: string | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
};

export type JobRequirementMatch = {
  name: string;
  importance: "essential" | "optional";
  canonical_uri: string | null;
  matched: boolean;
  candidate_skill: string | null;
  match_status:
    | "confirmed_match"
    | "uncertain_match"
    | "related_skill"
    | "non_match"
    | "missing";
  similarity_score: number | null;
  evidence: string | null;
  related_evidence: Array<{
    candidate_skill: string;
    similarity_score: number;
    relation: string;
    is_equivalent: boolean;
  }>;
};

export type JobSpecificMatching = {
  job_id: number;
  pipeline_run_id: number;
  status: "completed" | "no_requirements";
  candidate_skill_source: "pipeline.skills.extracted_skills";
  matching_method: "semantic_skill_matcher";
  canonical_uri_matching:
    | "not_used"
    | "unavailable"
    | "used"
    | "unresolved_or_unmatched";
  requirements: JobRequirementMatch[];
  scores: {
    essential: number | null;
    optional: number | null;
    overall: number | null;
  };
  candidate_skills_are_verified?: boolean;
  thresholds_are_provisional?: boolean;
};

export type JobMatchingResponse = {
  job: JobRecord;
  run: JobPipelineRun;
  matching_basis: string;
  job_specific_required_skills_applied: boolean;
  job_specific_matching: JobSpecificMatching | null;
};

export type ResumeUploadResponse = {
  message: string;
  resume: ResumeRecord;
};

export type ResumeSkillOccurrence = {
  section: string;
  text: string;
  start: number;
  end: number;
};

export type ResumeExtractedSkill = {
  skill: string;
  source_sections: string[];
  occurrences: ResumeSkillOccurrence[];
};

export type ResumeAnalysisResponse = {
  resume_id: number;
  original_name: string;
  status: "completed";
  pipeline_version: string;
  extraction_status: "success";
  page_count: number;
  sections: Record<string, string>;
  detected_section_names: string[];
  extracted_skills: ResumeExtractedSkill[];
  skill_count: number;
  skill_extraction_method: string;
};



export type LearningTaskStatus =
  | "not_started"
  | "in_progress"
  | "completed";





export type DashboardResponse = {
  resume_count: number;
  skill_gap_count: number;
  average_match_score: number | null;
  latest_resume: {
    id: number;
    original_name: string;
    uploaded_at: string;
  } | null;
  latest_skill_gap: {
    id: number;
    resume_id: number;
    target_role: string | null;
    match_score: number | null;
    created_at: string;
  } | null;
};

export type ActivityItem =
  | {
      type: "resume_uploaded";
      id: number;
      timestamp: string;
      resume_name: string;
    }
  | {
      type: "skill_gap_analyzed";
      id: number;
      timestamp: string;
      resume_id: number;
      target_role: string | null;
      match_score: number | null;
    }
  | {
      type: "task_progress_updated";
      id: number;
      timestamp: string;
      pipeline_run_id: number;
      skill_name: string;
      status: LearningTaskStatus;
      progress: number;
    };

export type ActivityResponse = {
  items: ActivityItem[];
  limit: number;
};

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function detailMessage(payload: unknown): string | undefined {
  if (
    typeof payload !== "object" ||
    payload === null ||
    !("detail" in payload)
  ) {
    return undefined;
  }

  const detail = payload.detail;

  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail.flatMap((issue: unknown) => {
      if (
        typeof issue === "object" &&
        issue !== null &&
        "msg" in issue &&
        typeof issue.msg === "string"
      ) {
        return [issue.msg];
      }

      return [];
    });

    if (messages.length) {
      return messages.join(" ");
    }
  }

  return undefined;
}

export async function requestJson(
  path: string,
  init: RequestInit,
  fetchRequest: typeof fetch,
): Promise<unknown> {
  let response: Response;

  try {
    response = await fetchRequest(`${API_BASE_URL}${path}`, init);
  } catch {
    throw new Error(
      "Could not connect to the Road2Hire API. Check that the backend is running and the API URL is correct.",
    );
  }

  let payload: unknown;

  try {
    payload = await response.json();
  } catch {
    if (!response.ok) {
      throw new ApiError(
        `The API request failed with HTTP ${response.status}.`,
        response.status,
      );
    }

    throw new Error("The API returned an invalid JSON response.");
  }

  if (!response.ok) {
    throw new ApiError(
      detailMessage(payload) ??
        `The API request failed with HTTP ${response.status}.`,
      response.status,
    );
  }

  return payload;
}

function parseAuthUser(payload: unknown): AuthUser {
  if (
    typeof payload !== "object" ||
    payload === null ||
    !("id" in payload) ||
    typeof payload.id !== "number" ||
    !("name" in payload) ||
    typeof payload.name !== "string" ||
    !("email" in payload) ||
    typeof payload.email !== "string"
  ) {
    throw new Error("The API returned an invalid user profile.");
  }

  return {
    id: payload.id,
    name: payload.name,
    email: payload.email,
  };
}

export async function registerUser(
  registration: RegistrationRequest,
  fetchRequest: typeof fetch = fetch,
): Promise<AuthUser> {
  const payload = await requestJson(
    "/auth/register",
    {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(registration),
    },
    fetchRequest,
  );

  return parseAuthUser(payload);
}

export async function loginUser(
  credentials: LoginRequest,
  fetchRequest: typeof fetch = fetch,
): Promise<AuthToken> {
  const payload = await requestJson(
    "/auth/login",
    {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(credentials),
    },
    fetchRequest,
  );

  if (
    typeof payload !== "object" ||
    payload === null ||
    !("access_token" in payload) ||
    typeof payload.access_token !== "string" ||
    !payload.access_token ||
    !("token_type" in payload) ||
    typeof payload.token_type !== "string" ||
    payload.token_type.toLowerCase() !== "bearer"
  ) {
    throw new Error("The API returned an invalid login response.");
  }

  return {
    access_token: payload.access_token,
    token_type: "bearer",
  };
}

export async function getCurrentProfile(
  accessToken: string,
  fetchRequest: typeof fetch = fetch,
): Promise<AuthUser> {
  if (!accessToken.trim()) {
    throw new Error("A bearer token is required to retrieve the profile.");
  }

  const payload = await requestJson(
    "/profile",
    {
      method: "GET",
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
    },
    fetchRequest,
  );

  return parseAuthUser(payload);
}

function isCandidateProfile(
  value: unknown,
): value is CandidateProfileResponse {
  const isStringArray = (item: unknown): item is string[] =>
    Array.isArray(item) &&
    item.every((entry) => typeof entry === "string");

  const isTimestamp = (item: unknown): item is string =>
    typeof item === "string" && !Number.isNaN(Date.parse(item));

  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value) &&
    "id" in value &&
    typeof value.id === "number" &&
    Number.isInteger(value.id) &&
    value.id > 0 &&
    "user_id" in value &&
    typeof value.user_id === "number" &&
    Number.isInteger(value.user_id) &&
    value.user_id > 0 &&
    "resume_id" in value &&
    (value.resume_id === null ||
      (typeof value.resume_id === "number" &&
        Number.isInteger(value.resume_id) &&
        value.resume_id > 0)) &&
    "skills" in value &&
    Array.isArray(value.skills) &&
    value.skills.every(
      (skill: unknown) =>
        typeof skill === "object" &&
        skill !== null &&
        !Array.isArray(skill) &&
        "skill" in skill &&
        typeof skill.skill === "string" &&
        "source_sections" in skill &&
        isStringArray(skill.source_sections) &&
        "occurrences" in skill &&
        Array.isArray(skill.occurrences) &&
        skill.occurrences.every(
          (occurrence: unknown) =>
            typeof occurrence === "object" &&
            occurrence !== null &&
            !Array.isArray(occurrence) &&
            "section" in occurrence &&
            typeof occurrence.section === "string" &&
            "text" in occurrence &&
            typeof occurrence.text === "string" &&
            "start" in occurrence &&
            typeof occurrence.start === "number" &&
            Number.isInteger(occurrence.start) &&
            occurrence.start >= 0 &&
            "end" in occurrence &&
            typeof occurrence.end === "number" &&
            Number.isInteger(occurrence.end) &&
            occurrence.end >= occurrence.start,
        ),
    ) &&
    "education" in value &&
    isStringArray(value.education) &&
    "experience" in value &&
    isStringArray(value.experience) &&
    "projects" in value &&
    isStringArray(value.projects) &&
    "certifications" in value &&
    isStringArray(value.certifications) &&
    "updated_at" in value &&
    isTimestamp(value.updated_at)
  );
}

export async function getCandidateProfile(
  accessToken: string,
  fetchRequest: typeof fetch = fetch,
): Promise<CandidateProfileResponse> {
  if (!accessToken.trim()) {
    throw new Error("Sign in to view your candidate profile.");
  }

  const payload = await requestJson(
    "/profile/candidate",
    {
      method: "GET",
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
    },
    fetchRequest,
  );

  if (!isCandidateProfile(payload)) {
    throw new Error(
      "The API returned an invalid candidate profile response.",
    );
  }

  return payload;
}

export async function updateCurrentProfile(
  updates: ProfileUpdate,
  accessToken: string,
  fetchRequest: typeof fetch = fetch,
): Promise<AuthUser> {
  if (!accessToken.trim()) {
    throw new Error("Sign in to update your profile.");
  }

  const entries = Object.entries(updates).filter(
    ([, value]) => value !== undefined,
  );

  if (
    entries.length === 0 ||
    entries.some(
      ([key]) => key !== "name" && key !== "email",
    ) ||
    entries.some(
      ([, value]) =>
        typeof value !== "string" || !value.trim(),
    )
  ) {
    throw new Error(
      "Provide a non-empty name or email to update your profile.",
    );
  }

  const payload = await requestJson(
    "/profile",
    {
      method: "PATCH",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify(Object.fromEntries(entries)),
    },
    fetchRequest,
  );

  return parseAuthUser(payload);
}

function isResumeRecord(value: unknown): value is ResumeRecord {
  return (
    typeof value === "object" &&
    value !== null &&
    "id" in value &&
    typeof value.id === "number" &&
    "user_id" in value &&
    typeof value.user_id === "number" &&
    "original_name" in value &&
    typeof value.original_name === "string" &&
    "stored_name" in value &&
    typeof value.stored_name === "string" &&
    "uploaded_at" in value &&
    typeof value.uploaded_at === "string" &&
    (!("download_url" in value) ||
      typeof value.download_url === "string")
  );
}

export async function listResumes(
  accessToken: string,
  fetchRequest: typeof fetch = fetch,
): Promise<ResumeRecord[]> {
  if (!accessToken.trim()) {
    throw new Error("Sign in to view your resumes.");
  }

  const payload = await requestJson(
    "/resumes",
    {
      method: "GET",
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
    },
    fetchRequest,
  );

  if (!Array.isArray(payload) || !payload.every(isResumeRecord)) {
    throw new Error("The API returned an invalid resume list.");
  }

  return payload;
}

export async function uploadResume(
  file: File,
  userId: number,
  accessToken: string,
  fetchRequest: typeof fetch = fetch,
): Promise<ResumeUploadResponse> {
  if (!accessToken.trim()) {
    throw new Error("Sign in to upload a resume.");
  }

  if (!Number.isInteger(userId) || userId <= 0) {
    throw new Error(
      "A valid signed-in user is required to upload a resume.",
    );
  }

  const formData = new FormData();
  formData.append("user_id", String(userId));
  formData.append("file", file);

  const payload = await requestJson(
    "/resume/upload",
    {
      method: "POST",
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      body: formData,
    },
    fetchRequest,
  );

  if (
    typeof payload !== "object" ||
    payload === null ||
    !("message" in payload) ||
    typeof payload.message !== "string" ||
    !("resume" in payload) ||
    !isResumeRecord(payload.resume)
  ) {
    throw new Error(
      "The API returned an invalid resume upload response.",
    );
  }

  return {
    message: payload.message,
    resume: payload.resume,
  };
}

export type ResumeDeleteResponse = {
  message: string;
  resume_id: number;
};

export async function downloadResume(
  resumeId: number,
  accessToken: string,
  fetchRequest: typeof fetch = fetch,
): Promise<Blob> {
  if (!accessToken.trim()) {
    throw new Error("Sign in to download your resume.");
  }

  if (!Number.isInteger(resumeId) || resumeId <= 0) {
    throw new Error("A valid resume is required to download.");
  }

  let response: Response;

  try {
    response = await fetchRequest(
      `${API_BASE_URL}/resume/${resumeId}/download`,
      {
        method: "GET",
        headers: {
          Accept: "application/pdf",
          Authorization: `Bearer ${accessToken}`,
        },
      },
    );
  } catch {
    throw new Error(
      "Could not connect to the Road2Hire API. Check that the backend is running and the API URL is correct.",
    );
  }

  if (!response.ok) {
    let message = `The API request failed with HTTP ${response.status}.`;

    try {
      const payload: unknown = await response.json();
      message = detailMessage(payload) ?? message;
    } catch {
      // Keep the safe HTTP status message when the error body is not JSON.
    }

    throw new ApiError(message, response.status);
  }

  return response.blob();
}

export async function deleteResume(
  resumeId: number,
  accessToken: string,
  fetchRequest: typeof fetch = fetch,
): Promise<ResumeDeleteResponse> {
  if (!accessToken.trim()) {
    throw new Error("Sign in to delete your resume.");
  }

  if (!Number.isInteger(resumeId) || resumeId <= 0) {
    throw new Error("A valid resume is required to delete.");
  }

  const payload = await requestJson(
    `/resumes/${resumeId}`,
    {
      method: "DELETE",
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
    },
    fetchRequest,
  );

  if (
    typeof payload !== "object" ||
    payload === null ||
    !("message" in payload) ||
    typeof payload.message !== "string" ||
    !payload.message.trim() ||
    !("resume_id" in payload) ||
    payload.resume_id !== resumeId
  ) {
    throw new Error(
      "The API returned an invalid resume deletion response.",
    );
  }

  return {
    message: payload.message,
    resume_id: payload.resume_id,
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value)
  );
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

function isNullableScore(value: unknown): value is number | null {
  return (
    value === null ||
    (typeof value === "number" &&
      Number.isFinite(value) &&
      value >= 0 &&
      value <= 1)
  );
}

function isNullableCosineSimilarity(
  value: unknown,
): value is number | null {
  return (
    value === null ||
    (typeof value === "number" &&
      Number.isFinite(value) &&
      value >= -1 &&
      value <= 1)
  );
}

function isJobSkillRequirement(
  value: unknown,
): value is JobSkillRequirement {
  return (
    isRecord(value) &&
    typeof value.skill_name === "string" &&
    value.skill_name.trim().length > 0 &&
    (value.importance === "essential" ||
      value.importance === "optional") &&
    isNullableString(value.canonical_uri)
  );
}

function isJobRecord(value: unknown): value is JobRecord {
  return (
    isRecord(value) &&
    Number.isInteger(value.id) &&
    Number(value.id) > 0 &&
    Number.isInteger(value.user_id) &&
    Number(value.user_id) > 0 &&
    typeof value.title === "string" &&
    typeof value.description === "string" &&
    typeof value.target_occupation === "string" &&
    Array.isArray(value.required_skills) &&
    value.required_skills.every(isJobSkillRequirement) &&
    typeof value.created_at === "string" &&
    !Number.isNaN(Date.parse(value.created_at)) &&
    typeof value.updated_at === "string" &&
    !Number.isNaN(Date.parse(value.updated_at))
  );
}

function isPipelineRun(value: unknown): value is JobPipelineRun {
  const nullableNumber = (item: unknown) =>
    item === null ||
    (typeof item === "number" &&
      Number.isFinite(item) &&
      item >= 0 &&
      item <= 1);

  return (
    isRecord(value) &&
    Number.isInteger(value.id) &&
    Number(value.id) > 0 &&
    ["pending", "running", "completed", "failed"].includes(
      String(value.status),
    ) &&
    ["explicit", "auto_selected"].includes(
      String(value.selection_mode),
    ) &&
    isNullableString(value.target_occupation_uri) &&
    isNullableString(value.target_occupation_title) &&
    nullableNumber(value.overall_skill_coverage_score) &&
    nullableNumber(value.essential_skill_coverage_score) &&
    nullableNumber(value.optional_skill_coverage_score) &&
    isNullableString(value.readiness_class) &&
    typeof value.is_ood === "boolean" &&
    isRecord(value.canonical_output) &&
    isNullableString(value.error_code) &&
    isNullableString(value.error_stage) &&
    isNullableString(value.error_message) &&
    typeof value.created_at === "string" &&
    !Number.isNaN(Date.parse(value.created_at)) &&
    (value.completed_at === null ||
      (typeof value.completed_at === "string" &&
        !Number.isNaN(Date.parse(value.completed_at))))
  );
}

const jobMatchStatuses = [
  "confirmed_match",
  "uncertain_match",
  "related_skill",
  "non_match",
  "missing",
] as const;

const uriMatchStatuses = [
  "not_used",
  "unavailable",
  "used",
  "unresolved_or_unmatched",
] as const;

function isJobRequirementMatch(
  value: unknown,
): value is JobRequirementMatch {
  if (
    !isRecord(value) ||
    typeof value.name !== "string" ||
    !value.name.trim() ||
    !["essential", "optional"].includes(
      String(value.importance),
    ) ||
    !isNullableString(value.canonical_uri) ||
    typeof value.matched !== "boolean" ||
    !isNullableString(value.candidate_skill) ||
    !jobMatchStatuses.includes(
      value.match_status as (typeof jobMatchStatuses)[number],
    ) ||
    !isNullableCosineSimilarity(value.similarity_score) ||
    !isNullableString(value.evidence) ||
    !Array.isArray(value.related_evidence)
  ) {
    return false;
  }

  if (
    !value.related_evidence.every(
      (item: unknown) =>
        isRecord(item) &&
        typeof item.candidate_skill === "string" &&
        typeof item.similarity_score === "number" &&
        Number.isFinite(item.similarity_score) &&
        item.similarity_score >= -1 &&
        item.similarity_score <= 1 &&
        typeof item.relation === "string" &&
        typeof item.is_equivalent === "boolean",
    )
  ) {
    return false;
  }

  return (
    value.matched ===
    (value.match_status === "confirmed_match")
  );
}

function isJobSpecificMatching(
  value: unknown,
): value is JobSpecificMatching {
  if (
    !isRecord(value) ||
    !Number.isInteger(value.job_id) ||
    Number(value.job_id) <= 0 ||
    !Number.isInteger(value.pipeline_run_id) ||
    Number(value.pipeline_run_id) <= 0 ||
    !["completed", "no_requirements"].includes(
      String(value.status),
    ) ||
    value.candidate_skill_source !==
      "pipeline.skills.extracted_skills" ||
    value.matching_method !== "semantic_skill_matcher" ||
    !uriMatchStatuses.includes(
      value.canonical_uri_matching as (typeof uriMatchStatuses)[number],
    ) ||
    !Array.isArray(value.requirements) ||
    !value.requirements.every(isJobRequirementMatch) ||
    !isRecord(value.scores) ||
    !isNullableScore(value.scores.essential) ||
    !isNullableScore(value.scores.optional) ||
    !isNullableScore(value.scores.overall)
  ) {
    return false;
  }

  if (
    value.candidate_skills_are_verified !== undefined &&
    typeof value.candidate_skills_are_verified !== "boolean"
  ) {
    return false;
  }

  if (
    value.thresholds_are_provisional !== undefined &&
    typeof value.thresholds_are_provisional !== "boolean"
  ) {
    return false;
  }

  if (
    value.status === "no_requirements" &&
    value.requirements.length !== 0
  ) {
    return false;
  }

  return true;
}

function parseJobMatchingResponse(
  value: unknown,
): JobMatchingResponse {
  if (
    !isRecord(value) ||
    !isJobRecord(value.job) ||
    !isPipelineRun(value.run) ||
    typeof value.matching_basis !== "string" ||
    typeof value.job_specific_required_skills_applied !== "boolean" ||
    !(
      value.job_specific_matching === null ||
      isJobSpecificMatching(value.job_specific_matching)
    )
  ) {
    throw new Error(
      "The API returned an invalid job matching response.",
    );
  }

  return value as unknown as JobMatchingResponse;
}

function authenticatedJobRequest(
  path: string,
  token: string,
  method: "GET" | "POST",
  fetchRequest: typeof fetch,
  body?: unknown,
) {
  if (!token.trim()) {
    throw new Error("Sign in to manage saved jobs.");
  }

  return requestJson(
    path,
    {
      method,
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${token}`,
        ...(body === undefined
          ? {}
          : { "Content-Type": "application/json" }),
      },
      ...(body === undefined
        ? {}
        : { body: JSON.stringify(body) }),
    },
    fetchRequest,
  );
}

export async function listJobs(
  accessToken: string,
  fetchRequest: typeof fetch = fetch,
): Promise<JobRecord[]> {
  const payload = await authenticatedJobRequest(
    "/jobs",
    accessToken,
    "GET",
    fetchRequest,
  );

  if (!Array.isArray(payload) || !payload.every(isJobRecord)) {
    throw new Error("The API returned an invalid job list.");
  }

  return payload;
}

export async function createJob(
  details: JobCreateRequest,
  accessToken: string,
  fetchRequest: typeof fetch = fetch,
): Promise<JobRecord> {
  if (
    !details.title.trim() ||
    !details.description.trim() ||
    !details.target_occupation.trim() ||
    !Array.isArray(details.required_skills) ||
    details.required_skills.some(
      (item) =>
        !item.skill_name.trim() ||
        !["essential", "optional"].includes(item.importance),
    )
  ) {
    throw new Error(
      "Provide a title, description, target occupation, and valid required skills.",
    );
  }

  const payload = await authenticatedJobRequest(
    "/jobs",
    accessToken,
    "POST",
    fetchRequest,
    details,
  );

  if (!isJobRecord(payload)) {
    throw new Error("The API returned an invalid job response.");
  }

  return payload;
}

export async function matchResumeToJob(
  jobId: number,
  resumeId: number,
  accessToken: string,
  fetchRequest: typeof fetch = fetch,
): Promise<JobMatchingResponse> {
  if (!accessToken.trim()) {
    throw new Error("Sign in to match a resume to a job.");
  }

  if (!Number.isInteger(jobId) || jobId <= 0) {
    throw new Error(
      "A valid saved job is required for matching.",
    );
  }

  if (!Number.isInteger(resumeId) || resumeId <= 0) {
    throw new Error(
      "A valid saved resume is required for matching.",
    );
  }

  const payload = await authenticatedJobRequest(
    `/jobs/${jobId}/matches`,
    accessToken,
    "POST",
    fetchRequest,
    { resume_id: resumeId },
  );

  return parseJobMatchingResponse(payload);
}

function isResumeSkillOccurrence(
  value: unknown,
): value is ResumeSkillOccurrence {
  return (
    typeof value === "object" &&
    value !== null &&
    "section" in value &&
    typeof value.section === "string" &&
    "text" in value &&
    typeof value.text === "string" &&
    "start" in value &&
    typeof value.start === "number" &&
    Number.isInteger(value.start) &&
    value.start >= 0 &&
    "end" in value &&
    typeof value.end === "number" &&
    Number.isInteger(value.end) &&
    value.end >= value.start
  );
}

function isResumeExtractedSkill(
  value: unknown,
): value is ResumeExtractedSkill {
  return (
    typeof value === "object" &&
    value !== null &&
    "skill" in value &&
    typeof value.skill === "string" &&
    "source_sections" in value &&
    Array.isArray(value.source_sections) &&
    value.source_sections.every(
      (section) => typeof section === "string",
    ) &&
    "occurrences" in value &&
    Array.isArray(value.occurrences) &&
    value.occurrences.every(isResumeSkillOccurrence)
  );
}

function parseResumeAnalysis(
  payload: unknown,
  requestedResumeId: number,
): ResumeAnalysisResponse {
  const isStringRecord = (
    value: unknown,
  ): value is Record<string, string> =>
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value) &&
    Object.values(value).every(
      (section) => typeof section === "string",
    );

  if (
    typeof payload !== "object" ||
    payload === null ||
    !("resume_id" in payload) ||
    payload.resume_id !== requestedResumeId ||
    !("original_name" in payload) ||
    typeof payload.original_name !== "string" ||
    !("status" in payload) ||
    payload.status !== "completed" ||
    !("pipeline_version" in payload) ||
    typeof payload.pipeline_version !== "string" ||
    !("extraction_status" in payload) ||
    payload.extraction_status !== "success" ||
    !("page_count" in payload) ||
    typeof payload.page_count !== "number" ||
    !Number.isInteger(payload.page_count) ||
    payload.page_count < 0 ||
    !("sections" in payload) ||
    !isStringRecord(payload.sections) ||
    !("detected_section_names" in payload) ||
    !Array.isArray(payload.detected_section_names) ||
    !payload.detected_section_names.every(
      (name) => typeof name === "string",
    ) ||
    !("extracted_skills" in payload) ||
    !Array.isArray(payload.extracted_skills) ||
    !payload.extracted_skills.every(isResumeExtractedSkill) ||
    !("skill_count" in payload) ||
    typeof payload.skill_count !== "number" ||
    !Number.isInteger(payload.skill_count) ||
    payload.skill_count !== payload.extracted_skills.length ||
    !("skill_extraction_method" in payload) ||
    typeof payload.skill_extraction_method !== "string"
  ) {
    throw new Error(
      "The API returned an invalid resume analysis response.",
    );
  }

  return payload as ResumeAnalysisResponse;
}

export async function getResumeAnalysis(
  resumeId: number,
  accessToken: string,
  fetchRequest: typeof fetch = fetch,
): Promise<ResumeAnalysisResponse> {
  if (!accessToken.trim()) {
    throw new Error("Sign in to view resume analysis.");
  }

  if (!Number.isInteger(resumeId) || resumeId <= 0) {
    throw new Error(
      "A valid resume is required to retrieve analysis.",
    );
  }

  const payload = await requestJson(
    `/resume/${resumeId}/analysis`,
    {
      method: "GET",
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
    },
    fetchRequest,
  );

  return parseResumeAnalysis(payload, resumeId);
}

const taskStatuses: readonly LearningTaskStatus[] = [
  "not_started",
  "in_progress",
  "completed",
];

function parseDashboard(payload: unknown): DashboardResponse {
  const isTimestamp = (value: unknown): value is string =>
    typeof value === "string" &&
    !Number.isNaN(Date.parse(value));

  if (
    !isRecord(payload) ||
    !Number.isInteger(payload.resume_count) ||
    (payload.resume_count as number) < 0 ||
    !Number.isInteger(payload.skill_gap_count) ||
    (payload.skill_gap_count as number) < 0 ||
    !(
      payload.average_match_score === null ||
      (typeof payload.average_match_score === "number" &&
        Number.isFinite(payload.average_match_score) &&
        payload.average_match_score >= 0 &&
        payload.average_match_score <= 100)
    )
  ) {
    throw new Error(
      "The API returned an invalid dashboard response.",
    );
  }

  const latestResume = payload.latest_resume;

  if (
    latestResume !== null &&
    (!isRecord(latestResume) ||
      !Number.isInteger(latestResume.id) ||
      (latestResume.id as number) <= 0 ||
      typeof latestResume.original_name !== "string" ||
      !isTimestamp(latestResume.uploaded_at))
  ) {
    throw new Error(
      "The API returned an invalid dashboard response.",
    );
  }

  const latestSkillGap = payload.latest_skill_gap;

  if (
    latestSkillGap !== null &&
    (!isRecord(latestSkillGap) ||
      !Number.isInteger(latestSkillGap.id) ||
      (latestSkillGap.id as number) <= 0 ||
      !Number.isInteger(latestSkillGap.resume_id) ||
      (latestSkillGap.resume_id as number) <= 0 ||
      !(
        latestSkillGap.target_role === null ||
        typeof latestSkillGap.target_role === "string"
      ) ||
      !(
        latestSkillGap.match_score === null ||
        (typeof latestSkillGap.match_score === "number" &&
          Number.isFinite(latestSkillGap.match_score) &&
          latestSkillGap.match_score >= 0 &&
          latestSkillGap.match_score <= 100)
      ) ||
      !isTimestamp(latestSkillGap.created_at))
  ) {
    throw new Error(
      "The API returned an invalid dashboard response.",
    );
  }

  return payload as DashboardResponse;
}

export async function getDashboard(
  accessToken: string,
  fetchRequest: typeof fetch = fetch,
): Promise<DashboardResponse> {
  if (!accessToken.trim()) {
    throw new Error("Sign in to view your dashboard.");
  }

  const payload = await requestJson(
    "/dashboard",
    {
      method: "GET",
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
    },
    fetchRequest,
  );

  return parseDashboard(payload);
}

function parseActivity(payload: unknown): ActivityResponse {
  if (
    typeof payload !== "object" ||
    payload === null ||
    Array.isArray(payload) ||
    !("items" in payload) ||
    !Array.isArray(payload.items) ||
    !("limit" in payload) ||
    typeof payload.limit !== "number" ||
    !Number.isInteger(payload.limit)
  ) {
    throw new Error(
      "The API returned an invalid activity response.",
    );
  }

  const items: ActivityItem[] = payload.items.map(
    (item: unknown) => {
      if (
        typeof item !== "object" ||
        item === null ||
        Array.isArray(item) ||
        !("type" in item) ||
        typeof item.type !== "string" ||
        !("id" in item) ||
        typeof item.id !== "number" ||
        !Number.isInteger(item.id) ||
        !("timestamp" in item) ||
        typeof item.timestamp !== "string" ||
        Number.isNaN(Date.parse(item.timestamp))
      ) {
        throw new Error(
          "The API returned an invalid activity response.",
        );
      }

      if (
        item.type === "resume_uploaded" &&
        "resume_name" in item &&
        typeof item.resume_name === "string"
      ) {
        return item as ActivityItem;
      }

      if (
        item.type === "skill_gap_analyzed" &&
        "resume_id" in item &&
        typeof item.resume_id === "number" &&
        "target_role" in item &&
        (typeof item.target_role === "string" ||
          item.target_role === null) &&
        "match_score" in item &&
        (item.match_score === null ||
          (typeof item.match_score === "number" &&
            Number.isFinite(item.match_score) &&
            item.match_score >= 0 &&
            item.match_score <= 100))
      ) {
        return item as ActivityItem;
      }

      if (
        item.type === "task_progress_updated" &&
        "pipeline_run_id" in item &&
        typeof item.pipeline_run_id === "number" &&
        Number.isInteger(item.pipeline_run_id) &&
        item.pipeline_run_id > 0 &&
        "skill_name" in item &&
        typeof item.skill_name === "string" &&
        "status" in item &&
        typeof item.status === "string" &&
        taskStatuses.includes(
          item.status as LearningTaskStatus,
        ) &&
        "progress" in item &&
        typeof item.progress === "number" &&
        Number.isInteger(item.progress) &&
        item.progress >= 0 &&
        item.progress <= 100
      ) {
        return item as ActivityItem;
      }

      throw new Error(
        "The API returned an invalid activity response.",
      );
    },
  );

  return {
    items,
    limit: payload.limit,
  };
}

export async function getRecentActivity(
  accessToken: string,
  limit = 20,
  fetchRequest: typeof fetch = fetch,
): Promise<ActivityResponse> {
  if (!accessToken.trim()) {
    throw new Error("Sign in to view recent activity.");
  }

  if (!Number.isInteger(limit) || limit < 1 || limit > 100) {
    throw new Error(
      "Activity limit must be from 1 to 100.",
    );
  }

  const payload = await requestJson(
    `/activity?limit=${limit}`,
    {
      method: "GET",
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
    },
    fetchRequest,
  );

  return parseActivity(payload);
}
