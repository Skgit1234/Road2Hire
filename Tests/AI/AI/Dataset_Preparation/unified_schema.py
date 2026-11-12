"""Unified Candidate-Occupation Dataset Schema for Road2Hire (M4.2).

Defines the structure of unified candidate-occupation records combining:
1. Standardized candidate profile (schema v1.1.0).
2. Grounded target occupation metadata (ESCO / Job Posting).
3. Hybrid skill gap features (coverage scores, counts, credits, evidence).
4. Personalized knowledge graph topological features (node/edge counts, provenance).
5. Ground truth alignment data (when available from gold_labels.json).

Adheres strictly to explainable, non-probabilistic principles. Does not synthesize
fake readiness scores or artificial training labels.
"""

from __future__ import annotations

from typing import Any, TypedDict

from AI.Candidate_Profile.profile_schema import CandidateProfile
from AI.Skill_Gap.gap_schema import MatchEvidence, SkillItem


class SkillGapSummaryFeatures(TypedDict, total=False):
    """Explainable skill gap numerical and categorical features."""

    overall_skill_coverage_score: float
    essential_skill_coverage_score: float
    optional_skill_coverage_score: float | None
    essential_weight: float
    optional_weight: float
    matched_skills_count: int
    partially_matched_skills_count: int
    missing_essential_skills_count: int
    missing_optional_skills_count: int
    unmapped_candidate_skills_count: int
    surplus_candidate_skills_count: int


class GraphTopologicalFeatures(TypedDict, total=False):
    """Topological features extracted from the candidate's personalized knowledge graph."""

    total_nodes: int
    total_edges: int
    provenance_edges_count: int  # applies_skill + uses_skill
    candidate_skill_nodes_count: int
    esco_skill_nodes_count: int
    taxonomy_edges_count: int  # broader + narrower + related


class GroundTruthAlignment(TypedDict, total=False):
    """Annotated ground-truth labels from verified human or gold datasets."""

    pair_id: str
    skills_score: float | None
    seniority_score: float | None
    domain_score: float | None
    location_score: float | None
    composite_score: float | None
    overqualified: bool | None
    reasoning: str | None


class OccupationRequirementSummary(TypedDict, total=False):
    """Target occupation requirement breakdown."""

    occupation_id: str  # ESCO URI or Job ID
    occupation_title: str
    source_type: str  # "esco" or "scraped_jobs"
    total_required_skills: int
    essential_skills: list[str]
    optional_skills: list[str]
    description: str | None


class CandidateOccupationRecord(TypedDict, total=False):
    """Complete unified record representing a candidate-occupation alignment pair."""

    pair_id: str
    candidate_id: str
    candidate_source: str  # "master_resumes" | "synthetic_profiles" | "resume_pdf"
    candidate_profile: CandidateProfile | dict[str, Any]
    candidate_skills_normalized: list[str]
    target_occupation: OccupationRequirementSummary
    skill_gap_features: SkillGapSummaryFeatures
    graph_features: GraphTopologicalFeatures | None
    matched_skills_evidence: list[MatchEvidence]
    partially_matched_skills_evidence: list[MatchEvidence]
    missing_essential_skills: list[SkillItem]
    missing_optional_skills: list[SkillItem]
    ground_truth: GroundTruthAlignment | None
    metadata: dict[str, Any]

