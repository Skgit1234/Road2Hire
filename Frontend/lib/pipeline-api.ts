import { requestJson } from "./api-client.ts";
import type {
  CareerReadinessPredictionResponse,
  KnowledgeGraphResponse,
  LearningTaskStatus,
  PipelineLearningRoadmapResponse,
  PipelineLearningTaskResponse,
  PipelineRunResultResponse,
  PipelineStatus,
  RoadmapItemResponse,
  RoadmapPhaseResponse,
  RoadmapResourcesResponse,
  SkillGapAnalysisRequest,
  SkillGapAnalysisResponse,
  SkillGapHistoryResponse,
  SkillPriorityResponse,
  TaskProgressUpdate,
} from "./pipeline-types.ts";

type FetchRequest = typeof fetch;

function requireToken(accessToken: string): void {
  if (!accessToken.trim()) {
    throw new Error("Sign in to access pipeline results.");
  }
}

function requirePositiveId(value: number, label: string): void {
  if (!Number.isInteger(value) || value <= 0) {
    throw new Error(`A valid ${label} is required.`);
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isString(value: unknown): value is string {
  return typeof value === "string";
}

function isNullableString(value: unknown): value is string | null {
  return value === null || isString(value);
}

function isNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isNullableNumber(value: unknown): value is number | null {
  return value === null || isNumber(value);
}

function isNullableInteger(value: unknown): value is number | null {
  return value === null || (isNumber(value) && Number.isInteger(value));
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every(isString);
}

function isStringNumberRecord(value: unknown): value is Record<string, number> {
  return isRecord(value) && Object.values(value).every(isNumber);
}

function isStringIntegerRecord(value: unknown): value is Record<string, number> {
  return isRecord(value) &&
    Object.values(value).every((item) => isNumber(item) && Number.isInteger(item));
}

function isRecordArray(value: unknown): value is Record<string, unknown>[] {
  return Array.isArray(value) && value.every(isRecord);
}

function isResourceCategoryArray(value: unknown): value is Record<string, string>[] {
  return Array.isArray(value) &&
    value.every((item) => isRecord(item) &&
      Object.values(item).every(isString));
}

const taskStatuses: readonly LearningTaskStatus[] = [
  "not_started",
  "in_progress",
  "completed",
];

function isTaskStatus(value: unknown): value is LearningTaskStatus {
  return typeof value === "string" &&
    taskStatuses.includes(value as LearningTaskStatus);
}

function isPipelineStatus(value: unknown): value is PipelineStatus {
  return value === "pending" ||
    value === "running" ||
    value === "completed" ||
    value === "failed";
}

function isSkillGapAnalysisResponse(
  value: unknown,
): value is SkillGapAnalysisResponse {
  return isRecord(value) &&
    isNumber(value.pipeline_run_id) &&
    isPipelineStatus(value.status) &&
    isString(value.matching_basis) &&
    isStringArray(value.warnings) &&
    (value.target_occupation === null || isRecord(value.target_occupation)) &&
    (value.skill_gap === null || isRecord(value.skill_gap)) &&
    (value.learning_roadmap === null || isRecord(value.learning_roadmap)) &&
    (value.knowledge_graph === null || isRecord(value.knowledge_graph)) &&
    (value.error === null || isRecord(value.error));
}

function isSkillGapHistoryItem(value: unknown): boolean {
  return isRecord(value) &&
    isNumber(value.id) &&
    isNumber(value.resume_id) &&
    isPipelineStatus(value.status) &&
    isNullableString(value.target_occupation_uri) &&
    isNullableString(value.target_occupation_title) &&
    isNullableNumber(value.overall_skill_coverage_score) &&
    isNullableNumber(value.essential_skill_coverage_score) &&
    isNullableNumber(value.optional_skill_coverage_score) &&
    isNullableString(value.readiness_class) &&
    isString(value.created_at) &&
    isNullableString(value.completed_at);
}

function isSkillGapHistoryResponse(
  value: unknown,
): value is SkillGapHistoryResponse {
  return isRecord(value) &&
    Array.isArray(value.items) &&
    value.items.every(isSkillGapHistoryItem) &&
    isNumber(value.total) &&
    isNumber(value.limit) &&
    isNumber(value.offset);
}

function isPipelineRunResultResponse(
  value: unknown,
): value is PipelineRunResultResponse {
  return isRecord(value) &&
    isNumber(value.pipeline_run_id) &&
    isPipelineStatus(value.status) &&
    isNumber(value.resume_id) &&
    isRecord(value.canonical_output) &&
    (value.error === null || isRecord(value.error));
}

function isSkillPriorityResponse(value: unknown): value is SkillPriorityResponse {
  return isRecord(value) &&
    isNumber(value.pipeline_run_id) &&
    (value.target_occupation === null || isRecord(value.target_occupation)) &&
    isRecordArray(value.items);
}

function isKnowledgeGraphResponse(value: unknown): value is KnowledgeGraphResponse {
  return isRecord(value) &&
    isNumber(value.pipeline_run_id) &&
    isRecord(value.summary) &&
    isRecordArray(value.nodes) &&
    isRecordArray(value.relationships) &&
    isString(value.scope);
}

function isCareerReadinessPredictionResponse(
  value: unknown,
): value is CareerReadinessPredictionResponse {
  return isRecord(value) &&
    isNumber(value.pipeline_run_id) &&
    isNumber(value.resume_id) &&
    isNullableString(value.completed_at) &&
    isString(value.predicted_class) &&
    isStringNumberRecord(value.class_probabilities) &&
    isNullableString(value.model_version) &&
    isNullableString(value.model_type) &&
    (value.is_experimental === null || typeof value.is_experimental === "boolean") &&
    (value.is_ood === null || typeof value.is_ood === "boolean") &&
    isStringArray(value.ood_warnings) &&
    isStringArray(value.pipeline_warnings) &&
    isNullableInteger(value.training_sample_count) &&
    isStringIntegerRecord(value.training_class_distribution) &&
    isStringNumberRecord(value.feature_values) &&
    isRecord(value.feature_diagnostics) &&
    isStringArray(value.limitations);
}

function isRoadmapItemResponse(value: unknown): value is RoadmapItemResponse {
  return isRecord(value) &&
    isString(value.logical_item_key) &&
    isNumber(value.roadmap_phase_number) &&
    isNullableString(value.roadmap_phase_name) &&
    isString(value.skill_name) &&
    isNullableString(value.skill_uri) &&
    isNullableString(value.priority) &&
    isRecord(value.roadmap_item_data) &&
    isNullableString(value.current_status) &&
    isNullableString(value.importance_rationale) &&
    isNullableString(value.learning_outcome) &&
    isStringArray(value.suggested_activities) &&
    isNullableString(value.practical_project) &&
    isNullableString(value.estimated_duration_weeks) &&
    isStringArray(value.prerequisites) &&
    isNullableString(value.completion_criteria) &&
    isResourceCategoryArray(value.resource_categories) &&
    isTaskStatus(value.status) &&
    isNumber(value.progress) &&
    value.progress >= 0 && value.progress <= 100 &&
    isNumber(value.task_id) &&
    isString(value.updated_at);
}

function isRoadmapPhaseResponse(value: unknown): value is RoadmapPhaseResponse {
  return isRecord(value) &&
    isNumber(value.phase_number) &&
    isString(value.phase_name) &&
    isString(value.description) &&
    isString(value.estimated_weeks) &&
    Array.isArray(value.items) &&
    value.items.every(isRoadmapItemResponse);
}

function isPipelineLearningRoadmapResponse(
  value: unknown,
): value is PipelineLearningRoadmapResponse {
  return isRecord(value) &&
    isNumber(value.pipeline_run_id) &&
    isNullableString(value.target_occupation_title) &&
    isNullableString(value.target_occupation_uri) &&
    isNullableInteger(value.total_roadmap_skills) &&
    isNullableString(value.total_estimated_weeks) &&
    Array.isArray(value.phases) &&
    value.phases.every(isRoadmapPhaseResponse) &&
    isStringArray(value.disclaimers);
}

function isPipelineLearningTaskResponse(
  value: unknown,
): value is PipelineLearningTaskResponse {
  return isRecord(value) &&
    isNumber(value.id) &&
    isNumber(value.pipeline_run_id) &&
    isString(value.logical_item_key) &&
    isNumber(value.roadmap_phase_number) &&
    isNullableString(value.roadmap_phase_name) &&
    isString(value.skill_name) &&
    isNullableString(value.skill_uri) &&
    isNullableString(value.priority) &&
    isTaskStatus(value.status) &&
    isNumber(value.progress) &&
    value.progress >= 0 && value.progress <= 100 &&
    isRecord(value.roadmap_item_data) &&
    isString(value.updated_at);
}

function isRoadmapResourcesResponse(
  value: unknown,
): value is RoadmapResourcesResponse {
  return isRecord(value) &&
    isNumber(value.pipeline_run_id) &&
    isNullableString(value.logical_item_key) &&
    isNullableString(value.skill_name) &&
    isResourceCategoryArray(value.resource_categories) &&
    isStringArray(value.suggested_activities) &&
    isNullableString(value.practical_project) &&
    isNullableString(value.learning_outcome) &&
    isNullableString(value.completion_criteria);
}

function expectResponse<T>(
  payload: unknown,
  guard: (value: unknown) => value is T,
  label: string,
): T {
  if (!guard(payload)) {
    throw new Error(`The API returned an invalid ${label} response.`);
  }
  return payload;
}

async function authenticatedRequest(
  path: string,
  accessToken: string,
  method: "GET" | "POST" | "PATCH",
  fetchRequest: FetchRequest,
  body?: unknown,
): Promise<unknown> {
  requireToken(accessToken);

  const hasBody = body !== undefined;
  return requestJson(path, {
    method,
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${accessToken}`,
      ...(hasBody ? { "Content-Type": "application/json" } : {}),
    },
    ...(hasBody ? { body: JSON.stringify(body) } : {}),
  }, fetchRequest);
}

export async function analyzeSkillGap(
  accessToken: string,
  details: SkillGapAnalysisRequest,
  fetchRequest: FetchRequest = fetch,
): Promise<SkillGapAnalysisResponse> {
  requirePositiveId(details.resume_id, "resume");

  const occupation = details.target_occupation?.trim();
  const autoSelect = details.auto_select_top_occupation === true;

  if (!occupation && !autoSelect) {
    throw new Error("Provide a target occupation or enable automatic occupation selection.");
  }

  const request: SkillGapAnalysisRequest = {
    resume_id: details.resume_id,
    ...(occupation ? { target_occupation: occupation } : {}),
    ...(autoSelect ? { auto_select_top_occupation: true } : {}),
  };

  const payload = await authenticatedRequest(
    "/skill-gaps/analyze",
    accessToken,
    "POST",
    fetchRequest,
    request,
  );

  return expectResponse(payload, isSkillGapAnalysisResponse, "skill-gap analysis");
}

export async function getPipelineSkillGapHistory(
  accessToken: string,
  limit = 20,
  offset = 0,
  fetchRequest: FetchRequest = fetch,
): Promise<SkillGapHistoryResponse> {
  if (!Number.isInteger(limit) || limit < 1 || limit > 100) {
    throw new Error("History limit must be from 1 to 100.");
  }
  if (!Number.isInteger(offset) || offset < 0) {
    throw new Error("History offset must be zero or greater.");
  }

  const query = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  const payload = await authenticatedRequest(
    `/skill-gaps/history?${query.toString()}`,
    accessToken,
    "GET",
    fetchRequest,
  );
  return expectResponse(payload, isSkillGapHistoryResponse, "skill-gap history");
}

export async function getPipelineSkillGapHistoryItem(
  accessToken: string,
  analysisId: number,
  fetchRequest: FetchRequest = fetch,
): Promise<SkillGapAnalysisResponse> {
  requirePositiveId(analysisId, "analysis ID");
  const payload = await authenticatedRequest(
    `/skill-gaps/history/${analysisId}`,
    accessToken,
    "GET",
    fetchRequest,
  );
  return expectResponse(payload, isSkillGapAnalysisResponse, "skill-gap analysis");
}

export async function getPipelineRunResult(
  accessToken: string,
  runId: number,
  fetchRequest: FetchRequest = fetch,
): Promise<PipelineRunResultResponse> {
  requirePositiveId(runId, "pipeline run ID");
  const payload = await authenticatedRequest(
    `/skill-gaps/runs/${runId}`,
    accessToken,
    "GET",
    fetchRequest,
  );
  return expectResponse(payload, isPipelineRunResultResponse, "pipeline run");
}

export async function getSkillPriorities(
  accessToken: string,
  runId: number,
  fetchRequest: FetchRequest = fetch,
): Promise<SkillPriorityResponse> {
  requirePositiveId(runId, "pipeline run ID");
  const payload = await authenticatedRequest(
    `/skill-gaps/runs/${runId}/priorities`,
    accessToken,
    "GET",
    fetchRequest,
  );
  return expectResponse(payload, isSkillPriorityResponse, "skill priorities");
}

export async function getPipelineKnowledgeGraph(
  accessToken: string,
  runId: number,
  fetchRequest: FetchRequest = fetch,
): Promise<KnowledgeGraphResponse> {
  requirePositiveId(runId, "pipeline run ID");
  const payload = await authenticatedRequest(
    `/skill-gaps/runs/${runId}/knowledge-graph`,
    accessToken,
    "GET",
    fetchRequest,
  );
  return expectResponse(payload, isKnowledgeGraphResponse, "knowledge graph");
}

export async function getPipelineCareerReadiness(
  accessToken: string,
  runId?: number,
  fetchRequest: FetchRequest = fetch,
): Promise<CareerReadinessPredictionResponse> {
  const path = runId === undefined
    ? "/career-readiness"
    : `/career-readiness/runs/${runId}`;

  if (runId !== undefined) requirePositiveId(runId, "pipeline run ID");

  const payload = await authenticatedRequest(
    path,
    accessToken,
    "GET",
    fetchRequest,
  );
  return expectResponse(payload, isCareerReadinessPredictionResponse, "career-readiness");
}

export async function getPipelineLearningRoadmap(
  accessToken: string,
  runId?: number,
  fetchRequest: FetchRequest = fetch,
): Promise<PipelineLearningRoadmapResponse> {
  const path = runId === undefined
    ? "/learning-roadmap"
    : `/learning-roadmap/runs/${runId}`;

  if (runId !== undefined) requirePositiveId(runId, "pipeline run ID");

  const payload = await authenticatedRequest(
    path,
    accessToken,
    "GET",
    fetchRequest,
  );
  return expectResponse(payload, isPipelineLearningRoadmapResponse, "learning roadmap");
}

export async function getRoadmapPhase(
  accessToken: string,
  runId: number,
  phaseNumber: number,
  fetchRequest: FetchRequest = fetch,
): Promise<RoadmapPhaseResponse> {
  requirePositiveId(runId, "pipeline run ID");
  requirePositiveId(phaseNumber, "roadmap phase number");

  const payload = await authenticatedRequest(
    `/learning-roadmap/runs/${runId}/phases/${phaseNumber}`,
    accessToken,
    "GET",
    fetchRequest,
  );
  return expectResponse(payload, isRoadmapPhaseResponse, "roadmap phase");
}

export async function getRoadmapItem(
  accessToken: string,
  runId: number,
  logicalItemKey: string,
  fetchRequest: FetchRequest = fetch,
): Promise<RoadmapItemResponse> {
  requirePositiveId(runId, "pipeline run ID");
  if (!logicalItemKey.trim()) throw new Error("A roadmap item key is required.");

  const payload = await authenticatedRequest(
    `/learning-roadmap/runs/${runId}/items/${encodeURIComponent(logicalItemKey)}`,
    accessToken,
    "GET",
    fetchRequest,
  );
  return expectResponse(payload, isRoadmapItemResponse, "roadmap item");
}

export async function getRoadmapResources(
  accessToken: string,
  runId: number,
  fetchRequest: FetchRequest = fetch,
): Promise<RoadmapResourcesResponse[]> {
  requirePositiveId(runId, "pipeline run ID");

  const payload = await authenticatedRequest(
    `/learning-roadmap/runs/${runId}/resources`,
    accessToken,
    "GET",
    fetchRequest,
  );

  if (!Array.isArray(payload) || !payload.every(isRoadmapResourcesResponse)) {
    throw new Error("The API returned an invalid roadmap resources response.");
  }
  return payload;
}

export async function getRoadmapItemResources(
  accessToken: string,
  runId: number,
  logicalItemKey: string,
  fetchRequest: FetchRequest = fetch,
): Promise<RoadmapResourcesResponse> {
  requirePositiveId(runId, "pipeline run ID");
  if (!logicalItemKey.trim()) throw new Error("A roadmap item key is required.");

  const payload = await authenticatedRequest(
    `/learning-roadmap/runs/${runId}/items/${encodeURIComponent(logicalItemKey)}/resources`,
    accessToken,
    "GET",
    fetchRequest,
  );
  return expectResponse(payload, isRoadmapResourcesResponse, "roadmap item resources");
}

export async function getPipelineTasks(
  accessToken: string,
  runId?: number,
  fetchRequest: FetchRequest = fetch,
): Promise<PipelineLearningTaskResponse[]> {
  if (runId !== undefined) requirePositiveId(runId, "pipeline run ID");

  const query = runId === undefined ? "" : `?pipeline_run_id=${runId}`;
  const payload = await authenticatedRequest(
    `/tasks${query}`,
    accessToken,
    "GET",
    fetchRequest,
  );

  if (!Array.isArray(payload) || !payload.every(isPipelineLearningTaskResponse)) {
    throw new Error("The API returned an invalid learning tasks response.");
  }
  return payload;
}

export async function getPipelineTask(
  accessToken: string,
  taskId: number,
  fetchRequest: FetchRequest = fetch,
): Promise<PipelineLearningTaskResponse> {
  requirePositiveId(taskId, "task ID");
  const payload = await authenticatedRequest(
    `/tasks/${taskId}`,
    accessToken,
    "GET",
    fetchRequest,
  );
  return expectResponse(payload, isPipelineLearningTaskResponse, "learning task");
}

export async function updatePipelineTaskProgress(
  accessToken: string,
  taskId: number,
  update: TaskProgressUpdate,
  fetchRequest: FetchRequest = fetch,
): Promise<PipelineLearningTaskResponse> {
  requirePositiveId(taskId, "task ID");

  if (update.status !== undefined && !isTaskStatus(update.status)) {
    throw new Error("Invalid learning task status.");
  }
  if (update.progress !== undefined &&
      (!Number.isInteger(update.progress) || update.progress < 0 || update.progress > 100)) {
    throw new Error("Task progress must be an integer from 0 to 100.");
  }
  if (update.status === undefined || update.progress === undefined) {
    throw new Error("Provide both a task status and progress value so the task remains consistent.");
  }
  const consistent = update.status === "completed"
    ? update.progress === 100
    : update.status === "not_started"
      ? update.progress === 0
      : update.progress >= 1 && update.progress <= 99;
  if (!consistent) {
    throw new Error("Task status and progress are inconsistent. Completed tasks must be 100%, not started tasks must be 0%, and in-progress tasks must be 1–99%.");
  }

  const payload = await authenticatedRequest(
    `/tasks/${taskId}`,
    accessToken,
    "PATCH",
    fetchRequest,
    update,
  );
  return expectResponse(payload, isPipelineLearningTaskResponse, "updated learning task");
}
