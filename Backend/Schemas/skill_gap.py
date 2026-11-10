from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class SkillGapAnalysisRequest(BaseModel):
    resume_id: int = Field(gt=0)
    target_occupation: str | None = Field(default=None, min_length=1, max_length=512)
    auto_select_top_occupation: bool = False

    @field_validator("target_occupation")
    @classmethod
    def strip_target_occupation(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Target occupation cannot be blank")
        return value

    @model_validator(mode="after")
    def require_occupation_or_auto_select(self) -> "SkillGapAnalysisRequest":
        if self.target_occupation is None and not self.auto_select_top_occupation:
            raise ValueError(
                "Provide target_occupation or enable auto_select_top_occupation."
            )
        return self


class SkillGapAnalysisResponse(BaseModel):
    pipeline_run_id: int
    status: str
    matching_basis: str
    warnings: list[str]
    target_occupation: dict[str, Any] | None
    skill_gap: dict[str, Any] | None
    learning_roadmap: dict[str, Any] | None
    knowledge_graph: dict[str, Any] | None
    error: dict[str, Any] | None


class SkillGapHistoryItem(BaseModel):
    id: int
    resume_id: int
    status: str
    target_occupation_uri: str | None
    target_occupation_title: str | None
    overall_skill_coverage_score: float | None
    essential_skill_coverage_score: float | None
    optional_skill_coverage_score: float | None
    readiness_class: str | None
    created_at: datetime
    completed_at: datetime | None


class SkillGapHistoryResponse(BaseModel):
    items: list[SkillGapHistoryItem]
    total: int
    limit: int
    offset: int


class PipelineRunResultResponse(BaseModel):
    pipeline_run_id: int
    status: str
    resume_id: int
    canonical_output: dict[str, Any]
    error: dict[str, Any] | None


class SkillPriorityResponse(BaseModel):
    pipeline_run_id: int
    target_occupation: dict[str, Any] | None
    items: list[dict[str, Any]]


class KnowledgeGraphResponse(BaseModel):
    pipeline_run_id: int
    summary: dict[str, Any]
    nodes: list[dict[str, Any]]
    relationships: list[dict[str, Any]]
    scope: str
