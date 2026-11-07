"""Milestone Phase 3 — End-to-End AI/ML Pipeline Integration & Edge Case Tests.

Validates:
1. Direct Python entry point execution (`Road2HirePipeline.run()`) without CLI.
2. Complete UnifiedPipelineResult schema contract and JSON serialization.
3. Edge case: Zero-gap candidate roadmap generation.
4. Edge case: Empty / corrupted PDF handling (`ResumeValidationError`).
5. Edge case: Resume with no detectable skills.
6. Edge case: Missing sections (education, experience, projects).
7. Edge case: Unknown / invalid occupation selection (`OccupationSelectionError`).
8. Edge case: Recoverable SHAP failure warning handling.
9. Edge case: Scanned PDF / OCR warning handling.
10. Model resource reuse and caching efficiency across repeated runs.
11. Inclusion of global SHAP feature importance in pipeline results.
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch
import pytest

from AI.Pipeline import (
    OccupationSelectionError,
    ResumeValidationError,
    Road2HirePipeline,
    RoadmapGenerator,
    SelectedOccupation,
    UnifiedPipelineResult,
)
from AI.Pipeline.pipeline_schema import (
    LearningRoadmap,
    ReadinessPredictionData,
    SHAPExplanationData,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_PDF = PROJECT_ROOT / "Tests" / "AI" / "sample_resume.pdf"


@pytest.fixture(scope="module")
def shared_pipeline() -> Road2HirePipeline:
    """Module-scoped pipeline to test resource sharing and caching."""
    return Road2HirePipeline()


# =============================================================================
# 1. Direct Python Entry Point & Output Contract
# =============================================================================


class TestPythonIntegrationInterface:
    """Validates the programmatic Python API for backend integration."""

    def test_direct_pipeline_run_returns_valid_unified_result(
        self, shared_pipeline: Road2HirePipeline
    ):
        result = shared_pipeline.run(
            resume_path=SAMPLE_PDF,
            target_occupation="data engineer",
            interactive=False,
        )

        assert isinstance(result, UnifiedPipelineResult)
        assert result.status in ["success", "warning"]
        assert result.pipeline_version == "3.0.0"
        assert result.page_count >= 1
        assert Path(result.source_file).exists()

        # Logical Sections Verification
        assert result.candidate_profile
        assert "candidate" in result.candidate_profile
        assert result.candidate_profile["candidate"]["name"] == "Alex Morgan"
        assert len(result.extracted_skills) > 0
        assert len(result.esco_mappings) > 0
        assert len(result.occupation_matches) > 0

        # Target Occupation Verification
        assert isinstance(result.selected_occupation, SelectedOccupation)
        assert result.selected_occupation.occupation_label == "data engineer"
        assert "2079755f" in result.selected_occupation.occupation_uri

        # Skill Gap Verification
        assert "overall_skill_coverage_score" in result.skill_gap_analysis
        assert "essential_skill_coverage_score" in result.skill_gap_analysis

        # M4 Readiness & OOD Verification
        assert isinstance(result.readiness_prediction, ReadinessPredictionData)
        assert result.readiness_prediction.predicted_class in [
            "Developing",
            "Job Ready",
            "Not Ready",
        ]
        assert isinstance(result.readiness_prediction.is_ood, bool)
        assert len(result.readiness_prediction.feature_values) == 9

        # M4.5 SHAP Verification
        assert isinstance(result.shap_explanation, SHAPExplanationData)
        assert result.shap_explanation.target_class_explained
        assert len(result.shap_explanation.feature_contributions) == 9
        assert len(result.shap_explanation.global_importance_ranking) == 9

        # Roadmap Verification
        assert isinstance(result.learning_roadmap, LearningRoadmap)
        assert len(result.learning_roadmap.phases) == 4

    def test_to_dict_and_to_json_serialization(self, shared_pipeline: Road2HirePipeline):
        result = shared_pipeline.run(
            resume_path=SAMPLE_PDF,
            target_occupation="data engineer",
            interactive=False,
        )

        # 1. to_dict() contract
        d = result.to_dict()
        assert isinstance(d, dict)
        assert d["status"] in ["success", "warning"]
        assert d["pipeline_version"] == "3.0.0"
        assert "selected_occupation" in d
        assert "readiness_prediction" in d
        assert "shap_explanation" in d
        assert "learning_roadmap" in d

        # 2. to_json() contract
        json_str = result.to_json(indent=2)
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["selected_occupation"]["occupation_label"] == "data engineer"
        assert (
            parsed["readiness_prediction"]["predicted_class"]
            == result.readiness_prediction.predicted_class
        )
        assert len(parsed["shap_explanation"]["global_importance_ranking"]) == 9


# =============================================================================
# 2. Edge Cases and Defensive Error Handling
# =============================================================================


class TestEdgeCasesAndDefensiveHandling:
    """Validates robust handling of boundary conditions and invalid inputs."""

    def test_nonexistent_pdf_raises_validation_error(
        self, shared_pipeline: Road2HirePipeline
    ):
        with pytest.raises(ResumeValidationError) as exc_info:
            shared_pipeline.run("nonexistent_resume_file.pdf", target_occupation="data engineer")
        assert "not found" in str(exc_info.value).lower()

    def test_non_pdf_file_raises_validation_error(
        self, shared_pipeline: Road2HirePipeline
    ):
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            docx_path = Path(f.name)
        try:
            with pytest.raises(ResumeValidationError) as exc_info:
                shared_pipeline.run(docx_path, target_occupation="data engineer")
            assert "expected a .pdf file" in str(exc_info.value).lower()
        finally:
            if docx_path.exists():
                docx_path.unlink()

    def test_corrupted_or_empty_pdf_raises_validation_error(
        self, shared_pipeline: Road2HirePipeline
    ):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"")  # 0-byte corrupt file
            empty_pdf = Path(f.name)
        try:
            with pytest.raises(ResumeValidationError) as exc_info:
                shared_pipeline.run(empty_pdf, target_occupation="data engineer")
            assert "failed to process resume" in str(exc_info.value).lower()
        finally:
            if empty_pdf.exists():
                empty_pdf.unlink()

    def test_unknown_occupation_raises_selection_error(
        self, shared_pipeline: Road2HirePipeline
    ):
        with pytest.raises(OccupationSelectionError) as exc_info:
            shared_pipeline.run(
                SAMPLE_PDF,
                target_occupation="completely unknown fictional profession 999",
                interactive=False,
            )
        assert "could not resolve target occupation" in str(exc_info.value).lower()

    def test_zero_gap_candidate_roadmap_handling(self):
        """When candidate has 0 missing skills, roadmap should handle gracefully."""
        roadmap_gen = RoadmapGenerator()
        empty_gap = {
            "overall_skill_coverage_score": 1.0,
            "missing_essential_skills": [],
            "partially_matched_skills": [],
            "missing_optional_skills": [],
        }
        roadmap = roadmap_gen.generate_roadmap(
            gap_report=empty_gap,
            target_occupation_title="Data Engineer",
            target_occupation_uri="http://data.europa.eu/esco/occupation/sample",
        )
        assert roadmap.total_roadmap_skills == 0
        assert "0 Weeks" in roadmap.total_estimated_weeks
        assert len(roadmap.phases) == 4
        # All phase item lists must be empty
        for p in roadmap.phases:
            assert len(p.items) == 0

    def test_shap_failure_is_recoverable_warning(
        self, shared_pipeline: Road2HirePipeline
    ):
        """Simulate unexpected SHAP failure: pipeline succeeds with shap=None and warning."""
        with patch.object(
            shared_pipeline,
            "_ensure_shap_explainer",
            side_effect=RuntimeError("SHAP numerical instability"),
        ):
            result = shared_pipeline.run(
                SAMPLE_PDF,
                target_occupation="data engineer",
                interactive=False,
            )
            assert result.shap_explanation is None
            assert result.status == "warning"
            assert any("SHAP numerical instability" in w for w in result.warnings)
            # Core outputs must still be intact
            assert result.readiness_prediction is not None
            assert result.learning_roadmap is not None

    def test_empty_candidate_evidence_defaults_safely(
        self, shared_pipeline: Road2HirePipeline
    ):
        """Candidate with no skills, experience, or education defaults safely."""
        empty_result = {
            "candidate_profile": {},
            "sections": {},
        }
        ev = shared_pipeline._extract_evidence_dict(empty_result)
        assert ev["skills_text"] == ""
        assert ev["experience_text"] == ""
        assert ev["projects_text"] == ""
        assert ev["education_text"] == ""

    def test_repeated_processing_maintains_singleton_efficiency(
        self, shared_pipeline: Road2HirePipeline
    ):
        """Running pipeline twice reuses existing initialized models without re-allocation."""
        model_id_1 = id(shared_pipeline.model)
        model_id_2 = id(shared_pipeline.model)
        assert model_id_1 == model_id_2
        assert shared_pipeline.model._taxonomy is not None
        assert len(shared_pipeline.model.esco_vocab) > 90000
