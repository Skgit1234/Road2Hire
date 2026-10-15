"""Schema definition for structured Road2Hire candidate profiles."""

from typing import Any, TypedDict


class CandidateProfile(TypedDict):
    schema_version: str
    source_file: str | None
    candidate: dict[str, Any]
    skills: list[dict[str, Any]]
    education: list[dict[str, Any]]
    experience: list[dict[str, Any]]
    projects: list[dict[str, Any]]
    certifications: list[dict[str, Any]]
    metadata: dict[str, Any]