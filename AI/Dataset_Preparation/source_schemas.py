"""Source dataset schemas for Road2Hire M4.2.

Defines TypedDict schemas reflecting the raw structure of ingested datasets:
1. Master Resumes (`Datasets/master_resumes.jsonl`)
2. Scraped Jobs (`Datasets/scraped_jobs.json`)
3. Synthetic Profiles (`Datasets/synthetic_profiles.json`)
4. Gold Labels (`Datasets/gold_labels.json`)
5. ESCO Skill Mapping (`Datasets/ESCO_ONET/Mappings/ESCO_Skill_Mapping.csv`)
6. O*NET Skill Mapping (`Datasets/ESCO_ONET/Mappings/ONET_Skill_Mapping.csv`)
"""

from __future__ import annotations

from typing import Any, TypedDict


# ---------------------------------------------------------------------------
# 1. Master Resumes Schema (Datasets/master_resumes.jsonl)
# ---------------------------------------------------------------------------

class ResumeLocation(TypedDict, total=False):
    city: str | None
    country: str | None
    remote_preference: str | None


class ResumePersonalInfo(TypedDict, total=False):
    name: str | None
    email: str | None
    phone: str | None
    location: ResumeLocation | dict[str, Any]
    summary: str | None
    linkedin: str | None
    github: str | None


class ExperienceDates(TypedDict, total=False):
    start: str | None
    end: str | None
    duration: str | None


class TechnicalEnvironment(TypedDict, total=False):
    technologies: list[str]
    methodologies: list[str]
    tools: list[str]


class ResumeExperienceItem(TypedDict, total=False):
    company: str | None
    company_info: dict[str, Any]
    title: str | None
    level: str | None
    employment_type: str | None
    dates: ExperienceDates | dict[str, Any]
    responsibilities: list[str]
    technical_environment: TechnicalEnvironment | dict[str, Any]


class DegreeInfo(TypedDict, total=False):
    level: str | None
    field: str | None
    major: str | None


class InstitutionInfo(TypedDict, total=False):
    name: str | None
    location: str | None
    accreditation: str | None


class ResumeEducationItem(TypedDict, total=False):
    degree: DegreeInfo | dict[str, Any]
    institution: InstitutionInfo | dict[str, Any]
    dates: dict[str, Any]
    achievements: dict[str, Any]


class SkillItemWithLevel(TypedDict, total=False):
    name: str
    level: str | None


class TechnicalSkills(TypedDict, total=False):
    programming_languages: list[SkillItemWithLevel]
    frameworks: list[SkillItemWithLevel]
    databases: list[SkillItemWithLevel]
    cloud: list[SkillItemWithLevel]


class ResumeSkillsBlock(TypedDict, total=False):
    technical: TechnicalSkills | dict[str, Any]
    languages: list[SkillItemWithLevel]


class ResumeProjectItem(TypedDict, total=False):
    name: str | None
    description: str | None
    technologies: list[str]
    role: str | None
    url: str | None
    impact: str | None


class MasterResumeRecord(TypedDict, total=False):
    """Schema of records in Datasets/master_resumes.jsonl."""

    personal_info: ResumePersonalInfo
    experience: list[ResumeExperienceItem]
    education: list[ResumeEducationItem]
    skills: ResumeSkillsBlock
    projects: list[ResumeProjectItem]
    certifications: list[dict[str, Any]] | list[str] | str


# ---------------------------------------------------------------------------
# 2. Scraped Jobs Schema (Datasets/scraped_jobs.json)
# ---------------------------------------------------------------------------

class ScrapedJobRecord(TypedDict, total=False):
    """Schema of records in Datasets/scraped_jobs.json."""

    id: str
    title: str
    company: str | None
    location: str | None
    description: str
    seniority_level: str | None
    employment_type: str | None
    job_function: str | None
    industry: str | None
    url: str | None
    posted_at: str | None
    scraped_at: str | None
    role_family_hint: str | None
    domain_hint: str | None
    experience_years_hint: int | float | None
    remote_hint: bool | None


# ---------------------------------------------------------------------------
# 3. Synthetic Profiles Schema (Datasets/synthetic_profiles.json)
# ---------------------------------------------------------------------------

class SyntheticPreferences(TypedDict, total=False):
    locations: list[str]
    remote: bool
    min_salary: float | None
    company_sizes: list[str]


class SyntheticProfileRecord(TypedDict, total=False):
    """Schema of records in Datasets/synthetic_profiles.json."""

    profile_id: int | str
    roles: list[str]
    skills_primary: list[str]
    skills_secondary: list[str]
    experience_years: int | float
    seniority: str
    domains: list[str]
    preferences: SyntheticPreferences | dict[str, Any]
    career_intent: str | None
    dealbreakers: list[str]


# ---------------------------------------------------------------------------
# 4. Gold Labels Schema (Datasets/gold_labels.json)
# ---------------------------------------------------------------------------

class GoldLabelRecord(TypedDict, total=False):
    """Schema of records in Datasets/gold_labels.json."""

    pair_id: str
    skills: float | int
    seniority: float | int
    domain: float | int
    location: float | int
    composite: float | int
    overqualified: bool
    reasoning: str


# ---------------------------------------------------------------------------
# 5. ESCO and O*NET Skill Mapping Schemas
# ---------------------------------------------------------------------------

class ESCOSkillMappingRecord(TypedDict, total=False):
    """Schema of rows in Datasets/ESCO_ONET/Mappings/ESCO_Skill_Mapping.csv."""

    ESCO_Skill_Id: str
    Skill_Name: str
    Skill_Category: str
    Occupation: str
    Importance: str  # "essential" or "optional"


class ONETSkillMappingRecord(TypedDict, total=False):
    """Schema of rows in Datasets/ESCO_ONET/Mappings/ONET_Skill_Mapping.csv."""

    ONET_SOC_Code: str
    ONET_Skill_Id: str
    Skill_Name: str
    Skill_Type: str
    Importance_Score: float
    Level_Score: float

