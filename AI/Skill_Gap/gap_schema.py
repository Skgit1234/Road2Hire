"""Schema definitions for Road2Hire M3 Hybrid Skill Gap Detection.

Defines TypedDict schemas for match evidence, target occupation metadata,
and the structured explainable skill gap report.
"""

from __future__ import annotations

from typing import Any, TypedDict


class MatchEvidence(TypedDict, total=False):
    """Detailed evidence for a candidate-to-target skill pairing."""

    tier: str  # "exact", "graph", "semantic"
    candidate_skill: str
    candidate_uri: str | None
    target_skill: str
    target_uri: str
    target_skill_type: str  # "essential" or "optional"
    graph_relationship: str | None
    similarity_score: float | None
    credit_assigned: float
    explanation: str


class TargetOccupationInfo(TypedDict, total=False):
    """Metadata regarding the selected target occupation."""

    uri: str
    preferred_label: str
    description: str | None
    essential_skills_count: int
    optional_skills_count: int
    total_skills_count: int


class SkillItem(TypedDict, total=False):
    """Representation of an occupation required skill."""

    skill_uri: str
    skill_label: str
    relation_type: str  # "essential" or "optional"
    skill_type: str


class SkillGapReport(TypedDict, total=False):
    """Complete structured and explainable skill gap report."""

    target_occupation: TargetOccupationInfo
    overall_skill_coverage_score: float
    essential_skill_coverage_score: float
    optional_skill_coverage_score: float | None
    scoring_weights: dict[str, float]
    matched_skills: list[MatchEvidence]
    partially_matched_skills: list[MatchEvidence]
    missing_essential_skills: list[SkillItem]
    missing_optional_skills: list[SkillItem]
    unmapped_candidate_skills: list[str]
    surplus_candidate_skills: list[str]
    matching_summary: dict[str, int]
    disclaimer: str
