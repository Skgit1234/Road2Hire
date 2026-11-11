"""Schema definition for structured Road2Hire candidate profiles.

Phase 4 Enhancement:
Provides TypedDict structures for granular, validated candidate profiles:
- CandidateInfo (basic info + contact details + summary)
- EducationRecord (degree, field of study, institution, dates, grade, level)
- ExperienceRecord (title, company, employment type, dates, responsibilities, skills)
- ProjectRecord (name, description, tools, responsibilities, related skills)
- CertificationRecord (name, issuer, issue/expiration dates, credential ID)
- CandidateProfile (complete structured profile conforming to schema version 1.1.0)
"""

from typing import Any, TypedDict

SCHEMA_VERSION = "1.1.0"


class CandidateInfo(TypedDict, total=False):
    """Personal and contact details of the candidate."""

    name: str | None
    email: str | None
    phone: str | None
    location: str | None
    summary: str | None
    raw_contact_information: str
    raw_summary: str


class EducationRecord(TypedDict, total=False):
    """Structured academic record."""

    degree: str | None
    field_of_study: str | None
    institution: str | None
    start_year: int | None
    end_year: int | None
    cgpa: float | None
    percentage: float | None
    academic_level: str | None
    raw_text: str


class ExperienceRecord(TypedDict, total=False):
    """Structured professional work or internship experience record."""

    job_title: str | None
    organization: str | None
    employment_type: str | None
    start_date: str | None
    end_date: str | None
    responsibilities: list[str]
    skills_used: list[str]
    raw_text: str


class ProjectRecord(TypedDict, total=False):
    """Structured project record."""

    project_name: str | None
    description: str | None
    technologies: list[str]
    responsibilities: list[str]
    related_skills: list[str]
    raw_text: str


class CertificationRecord(TypedDict, total=False):
    """Structured certification or credential record."""

    name: str | None
    issuing_organization: str | None
    issue_date: str | None
    expiration_date: str | None
    credential_id: str | None
    raw_text: str


class CandidateProfile(TypedDict):
    """Complete structured Road2Hire candidate profile."""

    schema_version: str
    source_file: str | None
    candidate: CandidateInfo | dict[str, Any]
    skills: list[dict[str, Any]]
    education: list[EducationRecord | dict[str, Any]]
    experience: list[ExperienceRecord | dict[str, Any]]
    projects: list[ProjectRecord | dict[str, Any]]
    certifications: list[CertificationRecord | dict[str, Any]]
    metadata: dict[str, Any]
