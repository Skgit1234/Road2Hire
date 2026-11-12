"""Unified Career Readiness Pipeline Schemas (Road2Hire).

Defines the structured data models, dataclasses, and TypedDicts for the
end-to-end resume intelligence, skill gap detection, readiness prediction,
SHAP explainability, and personalized learning roadmap pipeline.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import json
from typing import Any, Literal


@dataclass(slots=True)
class SelectedOccupation:
    """Represents a resolved target occupation for career readiness analysis."""

    occupation_uri: str
    occupation_label: str
    match_score: int = 0
    essential_matched: int = 0
    optional_matched: int = 0
    supporting_skills: list[str] = field(default_factory=list)
    resolution_source: str = "suggestion"  # 'suggestion', 'direct_uri', 'taxonomy_lookup'

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RoadmapItem:
    """Individual skill learning recommendation within the career roadmap."""

    skill_name: str
    esco_uri: str | None
    current_status: Literal["missing_essential", "partially_matched_essential", "missing_optional"]
    priority: Literal["Critical", "High", "Medium", "Low"]
    importance_rationale: str
    learning_outcome: str
    suggested_activities: list[str]
    practical_project: str
    estimated_duration_weeks: str
    prerequisites: list[str] = field(default_factory=list)
    completion_criteria: str = ""
    resource_categories: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RoadmapPhase:
    """A logical phase grouping prioritized roadmap learning items."""

    phase_number: int
    phase_name: str
    description: str
    estimated_weeks: str
    items: list[RoadmapItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase_number": self.phase_number,
            "phase_name": self.phase_name,
            "description": self.description,
            "estimated_weeks": self.estimated_weeks,
            "items": [item.to_dict() for item in self.items],
        }


@dataclass(slots=True)
class LearningRoadmap:
    """Personalized learning roadmap tailored to candidate skill gaps."""

    target_occupation_title: str
    target_occupation_uri: str
    total_roadmap_skills: int
    total_estimated_weeks: str
    phases: list[RoadmapPhase] = field(default_factory=list)
    disclaimers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_occupation_title": self.target_occupation_title,
            "target_occupation_uri": self.target_occupation_uri,
            "total_roadmap_skills": self.total_roadmap_skills,
            "total_estimated_weeks": self.total_estimated_weeks,
            "phases": [p.to_dict() for p in self.phases],
            "disclaimers": self.disclaimers,
        }


@dataclass(slots=True)
class ReadinessPredictionData:
    """Career readiness prediction output from the M4 supervised model."""

    predicted_class: str
    class_probabilities: dict[str, float]
    model_version: str
    model_type: str
    feature_values: dict[str, float]
    is_experimental: bool = True
    is_ood: bool = False
    ood_warnings: list[str] = field(default_factory=list)
    training_sample_count: int = 71
    training_class_distribution: dict[str, int] = field(default_factory=dict)
    feature_diagnostics: dict[str, Any] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SHAPExplanationData:
    """SHAP explainability breakdown for the readiness prediction."""

    target_class_explained: str
    base_value: float
    top_positive_factors: list[dict[str, Any]]
    top_negative_factors: list[dict[str, Any]]
    feature_contributions: list[dict[str, Any]]
    human_readable_summary: str
    waterfall_steps: list[dict[str, Any]]
    global_importance_ranking: list[dict[str, Any]] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class UnifiedPipelineResult:
    """Complete end-to-end career readiness result structure."""

    pipeline_version: str
    timestamp: str
    source_file: str
    page_count: int
    extraction_status: str
    candidate_profile: dict[str, Any]
    extracted_skills: list[dict[str, Any]]
    esco_mappings: list[dict[str, Any]]
    occupation_matches: list[dict[str, Any]]
    selected_occupation: SelectedOccupation
    skill_gap_analysis: dict[str, Any]
    personalized_graph_summary: dict[str, Any]
    readiness_prediction: ReadinessPredictionData | None
    shap_explanation: SHAPExplanationData | None
    learning_roadmap: LearningRoadmap | None
    execution_timings_seconds: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    report_paths: dict[str, str] = field(default_factory=dict)
    status: Literal["success", "warning", "error"] = "success"
    schema_version: str = "1.0.0"

    def to_canonical_dict(self) -> dict[str, Any]:
        """Return the clean canonical 10-section JSON contract matching pipeline_output.schema.json."""
        return {
            "schema_version": self.schema_version,
            "metadata": {
                "schema_version": self.schema_version,
                "pipeline_version": self.pipeline_version,
                "status": self.status,
                "timestamp": self.timestamp,
                "source_file": self.source_file,
                "page_count": self.page_count,
                "extraction_status": self.extraction_status,
                "execution_timings_seconds": self.execution_timings_seconds,
            },
            "candidate_profile": self.candidate_profile,
            "skills": {
                "extracted_skills": self.extracted_skills,
                "esco_mappings": self.esco_mappings,
                "extracted_skill_count": len(self.extracted_skills),
                "mapped_skill_count": len(self.esco_mappings),
            },
            "occupation_recommendations": self.occupation_matches,
            "target_occupation": (
                self.selected_occupation.to_dict()
                if self.selected_occupation
                else None
            ),
            "skill_gap": self.skill_gap_analysis,
            "readiness": (
                self.readiness_prediction.to_dict()
                if self.readiness_prediction
                else None
            ),
            "explanations": (
                self.shap_explanation.to_dict()
                if self.shap_explanation
                else None
            ),
            "knowledge_graph": self.personalized_graph_summary,
            "learning_roadmap": (
                self.learning_roadmap.to_dict()
                if self.learning_roadmap
                else None
            ),
            "warnings": self.warnings,
            "errors": self.errors,
            "report_paths": self.report_paths,
        }

    def to_dict(self, canonical: bool = False) -> dict[str, Any]:
        """Return the dictionary representation of the pipeline result.

        Parameters
        ----------
        canonical:
            If True, returns strictly the 10-section canonical output contract.
            If False (default), includes both canonical sections and top-level fields
            for complete backward compatibility.
        """
        if canonical:
            return self.to_canonical_dict()

        base = self.to_canonical_dict()
        # Merge top-level legacy fields for 100% backward compatibility
        base.update({
            "status": self.status,
            "pipeline_version": self.pipeline_version,
            "timestamp": self.timestamp,
            "source_file": self.source_file,
            "page_count": self.page_count,
            "extraction_status": self.extraction_status,
            "extracted_skills": self.extracted_skills,
            "esco_mappings": self.esco_mappings,
            "occupation_matches": self.occupation_matches,
            "selected_occupation": (
                self.selected_occupation.to_dict()
                if self.selected_occupation
                else None
            ),
            "skill_gap_analysis": self.skill_gap_analysis,
            "personalized_graph_summary": self.personalized_graph_summary,
            "readiness_prediction": (
                self.readiness_prediction.to_dict()
                if self.readiness_prediction
                else None
            ),
            "shap_explanation": (
                self.shap_explanation.to_dict()
                if self.shap_explanation
                else None
            ),
            "execution_timings_seconds": self.execution_timings_seconds,
        })
        return base

    def to_json(self, indent: int = 2, canonical: bool = False) -> str:
        """Serialize the complete pipeline result to a formatted JSON string."""
        return json.dumps(self.to_dict(canonical=canonical), indent=indent)


# ---------------------------------------------------------------------------
# Structured Pipeline Error Data Contracts
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class PipelineErrorDetails:
    """Standardized error payload for pipeline exceptions."""

    code: str
    message: str
    stage: str
    details: dict[str, Any] = field(default_factory=dict)
    recoverable: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def create_error_response(
    code: str,
    message: str,
    stage: str,
    details: dict[str, Any] | None = None,
    recoverable: bool = False,
    warnings: list[str] | None = None,
    schema_version: str = "1.0.0",
) -> dict[str, Any]:
    """Create a structured error dictionary matching pipeline_error.schema.json."""
    return {
        "schema_version": schema_version,
        "status": "error",
        "timestamp": datetime.now().isoformat(),
        "error": {
            "code": code,
            "message": message,
            "stage": stage,
            "details": details or {},
            "recoverable": recoverable,
        },
        "warnings": warnings or [],
    }

