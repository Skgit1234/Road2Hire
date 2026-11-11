from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class JobSkillRequirement(BaseModel):
    skill_name: str = Field(min_length=1, max_length=255)
    importance: Literal["essential", "optional"] = "essential"
    canonical_uri: str | None = Field(default=None, max_length=512)

    @field_validator("skill_name")
    @classmethod
    def strip_skill_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Skill name cannot be blank")
        return value


class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    target_occupation: str = Field(min_length=1, max_length=512)
    required_skills: list[JobSkillRequirement] = Field(default_factory=list)

    @field_validator("title", "description", "target_occupation")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value


class JobResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: str
    target_occupation: str
    required_skills: list[JobSkillRequirement]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobMatchRequest(BaseModel):
    resume_id: int = Field(gt=0)


class PipelineRunResponse(BaseModel):
    id: int
    status: Literal["pending", "running", "completed", "failed"]
    selection_mode: Literal["explicit", "auto_selected"]
    target_occupation_uri: str | None
    target_occupation_title: str | None
    overall_skill_coverage_score: float | None
    essential_skill_coverage_score: float | None
    optional_skill_coverage_score: float | None
    readiness_class: str | None
    is_ood: bool
    canonical_output: dict
    error_code: str | None
    error_stage: str | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class JobMatchingResponse(BaseModel):
    job: JobResponse
    run: PipelineRunResponse
    matching_basis: str
    job_specific_required_skills_applied: bool


class OccupationMatchesResponse(BaseModel):
    analysis_id: int | None
    candidate_skills: list[dict]
    matches: list[dict]
    message: str
