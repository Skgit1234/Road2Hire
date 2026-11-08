from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CandidateSkillOccurrence(BaseModel):
    section: str
    text: str
    start: int
    end: int


class CandidateSkill(BaseModel):
    skill: str
    source_sections: list[str]
    occurrences: list[CandidateSkillOccurrence]


class CandidateProfileResponse(BaseModel):
    id: int
    user_id: int
    resume_id: int | None
    skills: list[CandidateSkill]
    education: list[str]
    experience: list[str]
    projects: list[str]
    certifications: list[str]
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
