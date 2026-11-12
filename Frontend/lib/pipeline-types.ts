export type PipelineStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed";

export type PipelineOccupation = Record<string, unknown>;
export type PipelineSkillGapData = Record<string, unknown>;
export type PipelineRoadmapData = Record<string, unknown>;
export type PipelineKnowledgeGraph = Record<string, unknown>;
export type PipelineError = Record<string, unknown>;

export type SkillGapAnalysisRequest = {
  resume_id: number;
  target_occupation?: string;
  auto_select_top_occupation?: boolean;
};

export type SkillGapAnalysisResponse = {
  pipeline_run_id: number;
  status: PipelineStatus;
  matching_basis: string;
  warnings: string[];
  target_occupation: PipelineOccupation | null;
  skill_gap: PipelineSkillGapData | null;
  learning_roadmap: PipelineRoadmapData | null;
  knowledge_graph: PipelineKnowledgeGraph | null;
  error: PipelineError | null;
};

export type SkillGapHistoryItem = {
  id: number;
  resume_id: number;
  status: PipelineStatus;
  target_occupation_uri: string | null;
  target_occupation_title: string | null;
  overall_skill_coverage_score: number | null;
  essential_skill_coverage_score: number | null;
  optional_skill_coverage_score: number | null;
  readiness_class: string | null;
  created_at: string;
  completed_at: string | null;
};

export type SkillGapHistoryResponse = {
  items: SkillGapHistoryItem[];
  total: number;
  limit: number;
  offset: number;
};

export type PipelineRunResultResponse = {
  pipeline_run_id: number;
  status: PipelineStatus;
  resume_id: number;
  canonical_output: Record<string, unknown>;
  error: PipelineError | null;
};

export type SkillPriorityResponse = {
  pipeline_run_id: number;
  target_occupation: PipelineOccupation | null;
  items: Record<string, unknown>[];
};

export type KnowledgeGraphResponse = {
  pipeline_run_id: number;
  summary: Record<string, unknown>;
  nodes: Record<string, unknown>[];
  relationships: Record<string, unknown>[];
  scope: string;
};

export type CareerReadinessPredictionResponse = {
  pipeline_run_id: number;
  resume_id: number;
  completed_at: string | null;
  predicted_class: string;
  class_probabilities: Record<string, number>;
  model_version: string | null;
  model_type: string | null;
  is_experimental: boolean | null;
  is_ood: boolean | null;
  ood_warnings: string[];
  pipeline_warnings: string[];
  training_sample_count: number | null;
  training_class_distribution: Record<string, number>;
  feature_values: Record<string, number>;
  feature_diagnostics: Record<string, unknown>;
  limitations: string[];
};

export type RoadmapItemResponse = {
  logical_item_key: string;
  roadmap_phase_number: number;
  roadmap_phase_name: string | null;
  skill_name: string;
  skill_uri: string | null;
  priority: string | null;
  roadmap_item_data: Record<string, unknown>;
  current_status: string | null;
  importance_rationale: string | null;
  learning_outcome: string | null;
  suggested_activities: string[];
  practical_project: string | null;
  estimated_duration_weeks: string | null;
  prerequisites: string[];
  completion_criteria: string | null;
  resource_categories: Record<string, string>[];
  status: LearningTaskStatus;
  progress: number;
  task_id: number;
  updated_at: string;
};

export type RoadmapPhaseResponse = {
  phase_number: number;
  phase_name: string;
  description: string;
  estimated_weeks: string;
  items: RoadmapItemResponse[];
};

export type PipelineLearningRoadmapResponse = {
  pipeline_run_id: number;
  target_occupation_title: string | null;
  target_occupation_uri: string | null;
  total_roadmap_skills: number | null;
  total_estimated_weeks: string | null;
  phases: RoadmapPhaseResponse[];
  disclaimers: string[];
};

export type RoadmapResourcesResponse = {
  pipeline_run_id: number;
  logical_item_key: string | null;
  skill_name: string | null;
  resource_categories: Record<string, string>[];
  suggested_activities: string[];
  practical_project: string | null;
  learning_outcome: string | null;
  completion_criteria: string | null;
};

export type LearningTaskStatus =
  | "not_started"
  | "in_progress"
  | "completed";

export type PipelineLearningTaskResponse = {
  id: number;
  pipeline_run_id: number;
  logical_item_key: string;
  roadmap_phase_number: number;
  roadmap_phase_name: string | null;
  skill_name: string;
  skill_uri: string | null;
  priority: string | null;
  status: LearningTaskStatus;
  progress: number;
  roadmap_item_data: Record<string, unknown>;
  updated_at: string;
};

export type TaskProgressUpdate = {
  status: LearningTaskStatus;
  progress: number;
};
