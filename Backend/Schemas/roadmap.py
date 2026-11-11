from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class CareerRecommendationsResponse(BaseModel):
    pipeline_run_id: int
    target_occupation: dict[str, Any] | None
    recommendations: list[dict[str, Any]]
    candidate_skills: list[dict[str, Any]]
    skill_gap: dict[str, Any] | None


class RoadmapItemResponse(BaseModel):
    logical_item_key: str
    roadmap_phase_number: int
    roadmap_phase_name: str | None
    skill_name: str
    skill_uri: str | None
    priority: str | None
    roadmap_item_data: dict[str, Any]
    current_status: str | None
    importance_rationale: str | None
    learning_outcome: str | None
    suggested_activities: list[str]
    practical_project: str | None
    estimated_duration_weeks: str | None
    prerequisites: list[str]
    completion_criteria: str | None
    resource_categories: list[dict[str, str]]
    status: Literal["not_started", "in_progress", "completed"]
    progress: int = Field(ge=0, le=100)
    task_id: int
    updated_at: datetime


class RoadmapPhaseResponse(BaseModel):
    phase_number: int
    phase_name: str
    description: str
    estimated_weeks: str
    items: list[RoadmapItemResponse]


class LearningRoadmapResponse(BaseModel):
    pipeline_run_id: int
    target_occupation_title: str | None
    target_occupation_uri: str | None
    total_roadmap_skills: int | None
    total_estimated_weeks: str | None
    phases: list[RoadmapPhaseResponse]
    disclaimers: list[str]


class RoadmapResourcesResponse(BaseModel):
    pipeline_run_id: int
    logical_item_key: str | None
    skill_name: str | None
    resource_categories: list[dict[str, str]]
    suggested_activities: list[str]
    practical_project: str | None
    learning_outcome: str | None
    completion_criteria: str | None
