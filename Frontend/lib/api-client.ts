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


export type CareerReadinessResponse = {
  score: number | null;
  formula: string;
  analysis_id: number | null;
  target_role: string | null;
  message?: string;
  matched_skills?: string[];
  required_skills?: string[];
  missing_skills?: string[];
  created_at?: string;
};

export type LearningResource = {
  resource_id: string;
  skill_name: string;
  category: string | null;
  provider: string | null;
  course_title: string;
  difficulty: string | null;
  duration_hours: string | null;
  certificate: string | null;
  course_url: string | null;
};

export type LearningTaskStatus = "not_started" | "in_progress" | "completed";

export type LearningTask = {
  id: number;
  skill_name: string;
  status: LearningTaskStatus;
  progress: number;
  resources: LearningResource[];
};

export type LearningRoadmapResponse = {
  analysis_id: number | null;
  target_role: string | null;
  tasks: LearningTask[];
  resource_availability: "awaiting_skill_gap_analysis" | "available" | "no_matching_resources" | "dataset_empty";
};

export type TaskProgressUpdate = {
  status?: LearningTaskStatus;
  progress?: number;
};

export type TaskProgressResponse = {
  id: number;
  skill_gap_id: number;
  skill_name: string;
  status: LearningTaskStatus;
  progress: number;
  updated_at: string;
};

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
    target_role: string;
    match_score: number;
    created_at: string;
  } | null;
};

export type ActivityItem =
  | { type: "resume_uploaded"; id: number; timestamp: string; resume_name: string }
  | { type: "skill_gap_analyzed"; id: number; timestamp: string; resume_id: number; target_role: string; match_score: number }
  | { type: "task_progress_updated"; id: number; timestamp: string; pipeline_run_id: number; skill_name: string; status: LearningTaskStatus; progress: number };

export type ActivityResponse = { items: ActivityItem[]; limit: number };

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function detailMessage(payload: unknown): string | undefined {
  if (typeof payload !== "object" || payload === null || !("detail" in payload)) {
    return undefined;
  }

  const detail = payload.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const messages = detail.flatMap((issue: unknown) => {
      if (typeof issue === "object" && issue !== null && "msg" in issue && typeof issue.msg === "string") {
        return [issue.msg];
      }
      return [];
    });
    if (messages.length) return messages.join(" ");
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
    throw new Error("Could not connect to the Road2Hire API. Check that the backend is running and the API URL is correct.");
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    if (!response.ok) {
      throw new ApiError(`The API request failed with HTTP ${response.status}.`, response.status);
    }
    throw new Error("The API returned an invalid JSON response.");
  }

  if (!response.ok) {
    throw new ApiError(
      detailMessage(payload) ?? `The API request failed with HTTP ${response.status}.`,
      response.status,
    );
  }

  return payload;
}

function parseAuthUser(payload: unknown): AuthUser {
  if (
    typeof payload !== "object" || payload === null ||
    !("id" in payload) || typeof payload.id !== "number" ||
    !("name" in payload) || typeof payload.name !== "string" ||
    !("email" in payload) || typeof payload.email !== "string"
  ) {
    throw new Error("The API returned an invalid user profile.");
  }
  return { id: payload.id, name: payload.name, email: payload.email };
}

export async function registerUser(
  registration: RegistrationRequest,
  fetchRequest: typeof fetch = fetch,
): Promise<AuthUser> {
  const payload = await requestJson("/auth/register", {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(registration),
  }, fetchRequest);
  return parseAuthUser(payload);
}

export async function loginUser(
  credentials: LoginRequest,
  fetchRequest: typeof fetch = fetch,
): Promise<AuthToken> {
  const payload = await requestJson("/auth/login", {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(credentials),
  }, fetchRequest);

  if (
    typeof payload !== "object" || payload === null ||
    !("access_token" in payload) || typeof payload.access_token !== "string" || !payload.access_token ||
    !("token_type" in payload) || typeof payload.token_type !== "string" || payload.token_type.toLowerCase() !== "bearer"
  ) {
    throw new Error("The API returned an invalid login response.");
  }
  return { access_token: payload.access_token, token_type: "bearer" };
}

export async function getCurrentProfile(
  accessToken: string,
  fetchRequest: typeof fetch = fetch,
): Promise<AuthUser> {
  if (!accessToken.trim()) throw new Error("A bearer token is required to retrieve the profile.");

  const payload = await requestJson("/profile", {
    method: "GET",
    headers: { Accept: "application/json", Authorization: `Bearer ${accessToken}` },
  }, fetchRequest);
  return parseAuthUser(payload);
}

export async function updateCurrentProfile(
  updates: ProfileUpdate,
  accessToken: string,
  fetchRequest: typeof fetch = fetch,
): Promise<AuthUser> {
  if (!accessToken.trim()) throw new Error("Sign in to update your profile.");
  const entries = Object.entries(updates).filter(([, value]) => value !== undefined);
  if (entries.length === 0 || entries.some(([key]) => key !== "name" && key !== "email") ||
      entries.some(([, value]) => typeof value !== "string" || !value.trim())) {
    throw new Error("Provide a non-empty name or email to update your profile.");
  }

  const payload = await requestJson("/profile", {
    method: "PATCH",
    headers: { Accept: "application/json", "Content-Type": "application/json", Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify(Object.fromEntries(entries)),
  }, fetchRequest);
  return parseAuthUser(payload);
}

function isResumeRecord(value: unknown): value is ResumeRecord {
  return typeof value === "object" && value !== null &&
    "id" in value && typeof value.id === "number" &&
    "user_id" in value && typeof value.user_id === "number" &&
    "original_name" in value && typeof value.original_name === "string" &&
    "stored_name" in value && typeof value.stored_name === "string" &&
    "uploaded_at" in value && typeof value.uploaded_at === "string" &&
    (! ("download_url" in value) || typeof value.download_url === "string");
}

export async function listResumes(
  accessToken: string,
  fetchRequest: typeof fetch = fetch,
): Promise<ResumeRecord[]> {
  if (!accessToken.trim()) throw new Error("Sign in to view your resumes.");

  const payload = await requestJson("/resumes", {
    method: "GET",
    headers: { Accept: "application/json", Authorization: `Bearer ${accessToken}` },
  }, fetchRequest);
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
  if (!accessToken.trim()) throw new Error("Sign in to upload a resume.");
  if (!Number.isInteger(userId) || userId <= 0) throw new Error("A valid signed-in user is required to upload a resume.");

  const formData = new FormData();
  formData.append("user_id", String(userId));
  formData.append("file", file);
  const payload = await requestJson("/resume/upload", {
    method: "POST",
    headers: { Accept: "application/json", Authorization: `Bearer ${accessToken}` },
    body: formData,
  }, fetchRequest);

  if (typeof payload !== "object" || payload === null ||
      !("message" in payload) || typeof payload.message !== "string" ||
      !("resume" in payload) || !isResumeRecord(payload.resume)) {
    throw new Error("The API returned an invalid resume upload response.");
  }
  return { message: payload.message, resume: payload.resume as ResumeUploadResponse["resume"] };
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
  if (!accessToken.trim()) throw new Error("Sign in to download your resume.");
  if (!Number.isInteger(resumeId) || resumeId <= 0) {
    throw new Error("A valid resume is required to download.");
  }

  let response: Response;
  try {
    response = await fetchRequest(`${API_BASE_URL}/resume/${resumeId}/download`, {
      method: "GET",
      headers: {
        Accept: "application/pdf",
        Authorization: `Bearer ${accessToken}`,
      },
    });
  } catch {
    throw new Error("Could not connect to the Road2Hire API. Check that the backend is running and the API URL is correct.");
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
  if (!accessToken.trim()) throw new Error("Sign in to delete your resume.");
  if (!Number.isInteger(resumeId) || resumeId <= 0) {
    throw new Error("A valid resume is required to delete.");
  }

  const payload = await requestJson(`/resumes/${resumeId}`, {
    method: "DELETE",
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
  }, fetchRequest);

  if (
    typeof payload !== "object" || payload === null ||
    !("message" in payload) || typeof payload.message !== "string" || !payload.message.trim() ||
    !("resume_id" in payload) || payload.resume_id !== resumeId
  ) {
    throw new Error("The API returned an invalid resume deletion response.");
  }

  return { message: payload.message, resume_id: payload.resume_id as number };
}
function isResumeSkillOccurrence(value: unknown): value is ResumeSkillOccurrence {
  return typeof value === "object" && value !== null &&
    "section" in value && typeof value.section === "string" &&
    "text" in value && typeof value.text === "string" &&
    "start" in value && typeof value.start === "number" && Number.isInteger(value.start) && value.start >= 0 &&
    "end" in value && typeof value.end === "number" && Number.isInteger(value.end) && value.end >= value.start;
}

function isResumeExtractedSkill(value: unknown): value is ResumeExtractedSkill {
  return typeof value === "object" && value !== null &&
    "skill" in value && typeof value.skill === "string" &&
    "source_sections" in value && Array.isArray(value.source_sections) && value.source_sections.every((section) => typeof section === "string") &&
    "occurrences" in value && Array.isArray(value.occurrences) && value.occurrences.every(isResumeSkillOccurrence);
}

function parseResumeAnalysis(payload: unknown, requestedResumeId: number): ResumeAnalysisResponse {
  const isStringRecord = (value: unknown): value is Record<string, string> =>
    typeof value === "object" && value !== null && !Array.isArray(value) &&
    Object.values(value).every((section) => typeof section === "string");

  if (
    typeof payload !== "object" || payload === null ||
    !("resume_id" in payload) || payload.resume_id !== requestedResumeId ||
    !("original_name" in payload) || typeof payload.original_name !== "string" ||
    !("status" in payload) || payload.status !== "completed" ||
    !("pipeline_version" in payload) || typeof payload.pipeline_version !== "string" ||
    !("extraction_status" in payload) || payload.extraction_status !== "success" ||
    !("page_count" in payload) || typeof payload.page_count !== "number" || !Number.isInteger(payload.page_count) || payload.page_count < 0 ||
    !("sections" in payload) || !isStringRecord(payload.sections) ||
    !("detected_section_names" in payload) || !Array.isArray(payload.detected_section_names) || !payload.detected_section_names.every((name) => typeof name === "string") ||
    !("extracted_skills" in payload) || !Array.isArray(payload.extracted_skills) || !payload.extracted_skills.every(isResumeExtractedSkill) ||
    !("skill_count" in payload) || typeof payload.skill_count !== "number" || !Number.isInteger(payload.skill_count) || payload.skill_count !== payload.extracted_skills.length ||
    !("skill_extraction_method" in payload) || typeof payload.skill_extraction_method !== "string"
  ) {
    throw new Error("The API returned an invalid resume analysis response.");
  }
  return payload as ResumeAnalysisResponse;
}

export async function getResumeAnalysis(
  resumeId: number,
  accessToken: string,
  fetchRequest: typeof fetch = fetch,
): Promise<ResumeAnalysisResponse> {
  if (!accessToken.trim()) throw new Error("Sign in to view resume analysis.");
  if (!Number.isInteger(resumeId) || resumeId <= 0) throw new Error("A valid resume is required to retrieve analysis.");

  const payload = await requestJson(`/resume/${resumeId}/analysis`, {
    method: "GET",
    headers: { Accept: "application/json", Authorization: `Bearer ${accessToken}` },
  }, fetchRequest);
  return parseResumeAnalysis(payload, resumeId);
}

function parseCareerReadiness(payload: unknown): CareerReadinessResponse {
  const isSkillList = (value: unknown) => Array.isArray(value) && value.every((skill) => typeof skill === "string");
  if (
    typeof payload !== "object" || payload === null ||
    !("score" in payload) || (payload.score !== null && (typeof payload.score !== "number" || !Number.isFinite(payload.score))) ||
    !("formula" in payload) || typeof payload.formula !== "string" ||
    !("analysis_id" in payload) || (payload.analysis_id !== null && (typeof payload.analysis_id !== "number" || !Number.isInteger(payload.analysis_id))) ||
    !("target_role" in payload) || (payload.target_role !== null && typeof payload.target_role !== "string")
  ) {
    throw new Error("The API returned an invalid career-readiness response.");
  }

  if (payload.score === null) {
    if (!("message" in payload) || typeof payload.message !== "string" || payload.analysis_id !== null || payload.target_role !== null) {
      throw new Error("The API returned an invalid career-readiness response.");
    }
    return {
      score: null,
      formula: payload.formula,
      analysis_id: null,
      target_role: null,
      message: payload.message,
    };
  }

  if (
    payload.score < 0 || payload.score > 100 || payload.analysis_id === null ||
    !payload.target_role ||
    !("matched_skills" in payload) || !isSkillList(payload.matched_skills) ||
    !("required_skills" in payload) || !isSkillList(payload.required_skills) ||
    !("missing_skills" in payload) || !isSkillList(payload.missing_skills) ||
    !("created_at" in payload) || typeof payload.created_at !== "string" || Number.isNaN(Date.parse(payload.created_at))
  ) {
    throw new Error("The API returned an invalid career-readiness response.");
  }

  return payload as CareerReadinessResponse;
}

export async function getCareerReadiness(
  accessToken: string,
  fetchRequest: typeof fetch = fetch,
): Promise<CareerReadinessResponse> {
  if (!accessToken.trim()) throw new Error("Sign in to view career readiness.");
  const payload = await requestJson("/career-readiness", {
    method: "GET",
    headers: { Accept: "application/json", Authorization: `Bearer ${accessToken}` },
  }, fetchRequest);
  return parseCareerReadiness(payload);
}

const taskStatuses: readonly LearningTaskStatus[] = ["not_started", "in_progress", "completed"];

function isLearningResource(value: unknown): value is LearningResource {
  const optionalTextFields = ["category", "provider", "difficulty", "duration_hours", "certificate", "course_url"] as const;
  if (typeof value !== "object" || value === null) return false;
  const resource = value as Record<string, unknown>;
  return typeof resource.resource_id === "string" &&
    typeof resource.skill_name === "string" &&
    typeof resource.course_title === "string" &&
    optionalTextFields.every((field) => field in resource && (resource[field] === null || typeof resource[field] === "string"));
}

function isLearningTask(value: unknown): value is LearningTask {
  return typeof value === "object" && value !== null &&
    "id" in value && typeof value.id === "number" && Number.isInteger(value.id) && value.id > 0 &&
    "skill_name" in value && typeof value.skill_name === "string" &&
    "status" in value && typeof value.status === "string" && taskStatuses.includes(value.status as LearningTaskStatus) &&
    "progress" in value && typeof value.progress === "number" && Number.isInteger(value.progress) && value.progress >= 0 && value.progress <= 100 &&
    "resources" in value && Array.isArray(value.resources) && value.resources.every(isLearningResource);
}

function parseLearningRoadmap(payload: unknown): LearningRoadmapResponse {
  const resourceStates: LearningRoadmapResponse["resource_availability"][] = [
    "awaiting_skill_gap_analysis", "available", "no_matching_resources", "dataset_empty",
  ];
  if (
    typeof payload !== "object" || payload === null ||
    !("analysis_id" in payload) || (payload.analysis_id !== null && (typeof payload.analysis_id !== "number" || !Number.isInteger(payload.analysis_id) || payload.analysis_id <= 0)) ||
    !("target_role" in payload) || (payload.target_role !== null && typeof payload.target_role !== "string") ||
    !("tasks" in payload) || !Array.isArray(payload.tasks) || !payload.tasks.every(isLearningTask) ||
    !("resource_availability" in payload) || typeof payload.resource_availability !== "string" || !resourceStates.includes(payload.resource_availability as LearningRoadmapResponse["resource_availability"])
  ) {
    throw new Error("The API returned an invalid learning-roadmap response.");
  }

  if (payload.analysis_id === null) {
    if (payload.target_role !== null || payload.tasks.length !== 0 || payload.resource_availability !== "awaiting_skill_gap_analysis") {
      throw new Error("The API returned an invalid learning-roadmap response.");
    }
  } else if (typeof payload.target_role !== "string" || !payload.target_role || payload.resource_availability === "awaiting_skill_gap_analysis") {
    throw new Error("The API returned an invalid learning-roadmap response.");
  }
  return payload as LearningRoadmapResponse;
}

export async function getLearningRoadmap(
  accessToken: string,
  fetchRequest: typeof fetch = fetch,
): Promise<LearningRoadmapResponse> {
  if (!accessToken.trim()) throw new Error("Sign in to view your learning roadmap.");
  const payload = await requestJson("/learning-roadmap", {
    method: "GET",
    headers: { Accept: "application/json", Authorization: `Bearer ${accessToken}` },
  }, fetchRequest);
  return parseLearningRoadmap(payload);
}

export async function prepareLearningRoadmap(
  accessToken: string,
  fetchRequest: typeof fetch = fetch,
): Promise<LearningRoadmapResponse> {
  if (!accessToken.trim()) throw new Error("Sign in to view your learning roadmap.");
  const payload = await requestJson("/learning-roadmap/prepare", {
    method: "POST",
    headers: { Accept: "application/json", Authorization: `Bearer ${accessToken}` },
  }, fetchRequest);
  return parseLearningRoadmap(payload);
}

function parseTaskProgress(payload: unknown, requestedTaskId: number): TaskProgressResponse {
  if (
    typeof payload !== "object" || payload === null ||
    !("id" in payload) || payload.id !== requestedTaskId ||
    !("skill_gap_id" in payload) || typeof payload.skill_gap_id !== "number" || !Number.isInteger(payload.skill_gap_id) || payload.skill_gap_id <= 0 ||
    !("skill_name" in payload) || typeof payload.skill_name !== "string" ||
    !("status" in payload) || typeof payload.status !== "string" || !taskStatuses.includes(payload.status as LearningTaskStatus) ||
    !("progress" in payload) || typeof payload.progress !== "number" || !Number.isInteger(payload.progress) || payload.progress < 0 || payload.progress > 100 ||
    !("updated_at" in payload) || typeof payload.updated_at !== "string" || Number.isNaN(Date.parse(payload.updated_at))
  ) {
    throw new Error("The API returned an invalid task-progress response.");
  }
  return payload as TaskProgressResponse;
}

export async function updateTaskProgress(
  taskId: number,
  update: TaskProgressUpdate,
  accessToken: string,
  fetchRequest: typeof fetch = fetch,
): Promise<TaskProgressResponse> {
  if (!accessToken.trim()) throw new Error("Sign in to update task progress.");
  if (!Number.isInteger(taskId) || taskId <= 0) throw new Error("Choose a valid roadmap task.");
  const fields = Object.keys(update);
  if (fields.length === 0 || fields.some((field) => field !== "progress" && field !== "status")) {
    throw new Error("Provide a task status or progress update.");
  }
  if (update.progress !== undefined && (!Number.isInteger(update.progress) || update.progress < 0 || update.progress > 100)) {
    throw new Error("Task progress must be a whole number from 0 to 100.");
  }
  if (update.status !== undefined && !taskStatuses.includes(update.status)) {
    throw new Error("Choose a valid task status.");
  }
  if ((update.status === "completed" && update.progress !== undefined && update.progress !== 100) ||
      (update.status === "not_started" && update.progress !== undefined && update.progress !== 0) ||
      (update.status === "in_progress" && update.progress === 100)) {
    throw new Error("Task status and progress values are inconsistent.");
  }

  const payload = await requestJson(`/tasks/${taskId}`, {
    method: "PATCH",
    headers: { Accept: "application/json", "Content-Type": "application/json", Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify(update),
  }, fetchRequest);
  return parseTaskProgress(payload, taskId);
}

function parseDashboard(payload: unknown): DashboardResponse {
  const isRecord = (value: unknown): value is Record<string, unknown> =>
    typeof value === "object" && value !== null && !Array.isArray(value);
  const isTimestamp = (value: unknown): value is string =>
    typeof value === "string" && !Number.isNaN(Date.parse(value));
  if (
    !isRecord(payload) ||
    !Number.isInteger(payload.resume_count) || (payload.resume_count as number) < 0 ||
    !Number.isInteger(payload.skill_gap_count) || (payload.skill_gap_count as number) < 0 ||
    !(payload.average_match_score === null || (
      typeof payload.average_match_score === "number" && Number.isFinite(payload.average_match_score) &&
      payload.average_match_score >= 0 && payload.average_match_score <= 100
    ))
  ) {
    throw new Error("The API returned an invalid dashboard response.");
  }

  const latestResume = payload.latest_resume;
  if (latestResume !== null && (!isRecord(latestResume) ||
      !Number.isInteger(latestResume.id) || (latestResume.id as number) <= 0 ||
      typeof latestResume.original_name !== "string" || !isTimestamp(latestResume.uploaded_at))) {
    throw new Error("The API returned an invalid dashboard response.");
  }
  const latestSkillGap = payload.latest_skill_gap;
  if (latestSkillGap !== null && (!isRecord(latestSkillGap) ||
      !Number.isInteger(latestSkillGap.id) || (latestSkillGap.id as number) <= 0 ||
      !Number.isInteger(latestSkillGap.resume_id) || (latestSkillGap.resume_id as number) <= 0 ||
      typeof latestSkillGap.target_role !== "string" ||
      typeof latestSkillGap.match_score !== "number" || !Number.isFinite(latestSkillGap.match_score) ||
      latestSkillGap.match_score < 0 || latestSkillGap.match_score > 100 || !isTimestamp(latestSkillGap.created_at))) {
    throw new Error("The API returned an invalid dashboard response.");
  }
  return payload as DashboardResponse;
}

export async function getDashboard(
  accessToken: string,
  fetchRequest: typeof fetch = fetch,
): Promise<DashboardResponse> {
  if (!accessToken.trim()) throw new Error("Sign in to view your dashboard.");
  const payload = await requestJson("/dashboard", {
    method: "GET",
    headers: { Accept: "application/json", Authorization: `Bearer ${accessToken}` },
  }, fetchRequest);
  return parseDashboard(payload);
}

function parseActivity(payload: unknown): ActivityResponse {
  if (typeof payload !== "object" || payload === null || Array.isArray(payload) ||
      !("items" in payload) || !Array.isArray(payload.items) ||
      !("limit" in payload) || typeof payload.limit !== "number" || !Number.isInteger(payload.limit)) {
    throw new Error("The API returned an invalid activity response.");
  }
  const items: ActivityItem[] = payload.items.map((item: unknown) => {
    if (typeof item !== "object" || item === null || Array.isArray(item) ||
        !("type" in item) || typeof item.type !== "string" ||
        !("id" in item) || typeof item.id !== "number" || !Number.isInteger(item.id) ||
        !("timestamp" in item) || typeof item.timestamp !== "string" || Number.isNaN(Date.parse(item.timestamp))) {
      throw new Error("The API returned an invalid activity response.");
    }
    if (item.type === "resume_uploaded" && "resume_name" in item && typeof item.resume_name === "string") {
      return item as ActivityItem;
    }
    if (item.type === "skill_gap_analyzed" && "resume_id" in item && typeof item.resume_id === "number" &&
        "target_role" in item && typeof item.target_role === "string" &&
        "match_score" in item && typeof item.match_score === "number" && Number.isFinite(item.match_score)) {
      return item as ActivityItem;
    }
    if (item.type === "task_progress_updated" && "pipeline_run_id" in item &&
        typeof item.pipeline_run_id === "number" && Number.isInteger(item.pipeline_run_id) && item.pipeline_run_id > 0 &&
        "skill_name" in item && typeof item.skill_name === "string" &&
        "status" in item && typeof item.status === "string" && taskStatuses.includes(item.status as LearningTaskStatus) &&
        "progress" in item && typeof item.progress === "number" && Number.isInteger(item.progress) && item.progress >= 0 && item.progress <= 100) {
      return item as ActivityItem;
    }
    throw new Error("The API returned an invalid activity response.");
  });
  return { items, limit: payload.limit };
}

export async function getRecentActivity(
  accessToken: string,
  limit = 20,
  fetchRequest: typeof fetch = fetch,
): Promise<ActivityResponse> {
  if (!accessToken.trim()) throw new Error("Sign in to view recent activity.");
  if (!Number.isInteger(limit) || limit < 1 || limit > 100) throw new Error("Activity limit must be from 1 to 100.");
  const payload = await requestJson(`/activity?limit=${limit}`, {
    method: "GET",
    headers: { Accept: "application/json", Authorization: `Bearer ${accessToken}` },
  }, fetchRequest);
  return parseActivity(payload);
}
