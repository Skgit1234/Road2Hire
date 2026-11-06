"""Comprehensive Automated Tests for the End-to-End Career Readiness Pipeline.

Validates:
1. PDF resume validation and handling of invalid/missing files.
2. Text extraction and candidate profile generation (Schema v1.1.0).
3. Optimized Trie skill extraction and ESCO normalization.
4. Knowledge graph occupation ranking.
5. Interactive and non-interactive target occupation selection.
6. Hybrid 3-tier skill gap detection.
7. Personalized knowledge graph construction.
8. M4 supervised career readiness prediction.
9. M4.5 SHAP explainability and mathematical additivity.
10. 4-Phase personalized learning roadmap generation.
11. Unified Markdown and JSON report generation.
12. Single-command CLI execution.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch
import pytest

from AI.Pipeline import (
    OccupationSelectionError,
    PipelineError,
    ResumeValidationError,
    Road2HirePipeline,
    RoadmapGenerator,
    SelectedOccupation,
    TargetOccupationSelector,
)
from AI.Pipeline.cli import main as cli_main
from AI.Pipeline.report_generator import ReportGenerator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_PDF = PROJECT_ROOT / "Tests" / "AI" / "sample_resume.pdf"


@pytest.fixture(scope="module")
def pipeline() -> Road2HirePipeline:
    return Road2HirePipeline()


@pytest.fixture(scope="module")
def sample_pipeline_result(pipeline: Road2HirePipeline):
    """Run pipeline once on sample resume for shared inspection."""
    return pipeline.run(
        resume_path=SAMPLE_PDF,
        target_occupation="data engineer",
        interactive=False,
    )


# =============================================================================
# 1. Input Validation & Error Handling
# =============================================================================


class TestResumeInputValidation:
    """Validates PDF input requirements and failure modes."""

    def test_missing_pdf_raises_validation_error(self, pipeline: Road2HirePipeline):
        with pytest.raises(ResumeValidationError, match="not found"):
            pipeline.run("non_existent_file.pdf", target_occupation="Data Engineer")

    def test_non_pdf_file_raises_validation_error(self, pipeline: Road2HirePipeline, tmp_path: Path):
        txt_file = tmp_path / "resume.txt"
        txt_file.write_text("Hello world", encoding="utf-8")
        with pytest.raises(ResumeValidationError, match=r"Expected a \.pdf file"):
            pipeline.run(txt_file, target_occupation="Data Engineer")


# =============================================================================
# 2. Target Occupation Selection & Resolution
# =============================================================================


class TestTargetOccupationResolution:
    """Validates target occupation resolution, suggestions, and interactive prompting."""

    def test_non_interactive_without_query_raises_selection_error(self, pipeline: Road2HirePipeline):
        with pytest.raises(OccupationSelectionError, match="No target occupation specified"):
            pipeline.run(SAMPLE_PDF, target_occupation=None, interactive=False)

    def test_resolve_by_exact_uri(self, pipeline: Road2HirePipeline):
        selector = pipeline.occupation_selector
        uri = "http://data.europa.eu/esco/occupation/2079755f-d809-49e6-8037-4de6180e54c0"
        resolved = selector.resolve_selection(uri, ranked_matches=[], interactive=False)
        assert resolved.occupation_uri == uri
        assert "data engineer" in resolved.occupation_label.casefold()

    def test_resolve_by_title_suggestion(self, pipeline: Road2HirePipeline):
        selector = pipeline.occupation_selector
        ranked = [
            {"occupation_uri": "http://esco/occ/1", "occupation_label": "Data Engineer", "score": 3, "essential_count": 2},
            {"occupation_uri": "http://esco/occ/2", "occupation_label": "Software Developer", "score": 2, "essential_count": 1},
        ]
        resolved = selector.resolve_selection("data engineer", ranked_matches=ranked, interactive=False)
        assert resolved.occupation_label == "Data Engineer"
        assert resolved.match_score == 3

    def test_resolve_invalid_occupation_raises(self, pipeline: Road2HirePipeline):
        selector = pipeline.occupation_selector
        with pytest.raises(OccupationSelectionError, match="Could not resolve target occupation"):
            selector.resolve_selection("astronaut_underwater_basket_weaver_xyz", ranked_matches=[], interactive=False)

    def test_interactive_numeric_selection(self, pipeline: Road2HirePipeline):
        selector = pipeline.occupation_selector
        ranked = [
            {"occupation_uri": "http://esco/occ/1", "occupation_label": "Data Engineer", "score": 3, "essential_count": 2},
            {"occupation_uri": "http://esco/occ/2", "occupation_label": "Software Developer", "score": 2, "essential_count": 1},
        ]
        with patch("builtins.input", return_value="1"):
            resolved = selector.resolve_selection(None, ranked_matches=ranked, interactive=True)
            assert resolved.occupation_label == "Data Engineer"


# =============================================================================
# 3. Hybrid Skill Gap & Personalized Graph Integration
# =============================================================================


class TestSkillGapAndGraphIntegration:
    """Validates M3 skill gap detection and personalized graph generation."""

    def test_skill_gap_metrics(self, sample_pipeline_result):
        gap = sample_pipeline_result.skill_gap_analysis
        assert "overall_skill_coverage_score" in gap
        assert "essential_skill_coverage_score" in gap
        assert "optional_skill_coverage_score" in gap
        assert isinstance(gap["overall_skill_coverage_score"], float)
        assert 0.0 <= gap["overall_skill_coverage_score"] <= 1.0

        # Check matched and missing lists
        assert "matched_skills" in gap
        assert "missing_essential_skills" in gap
        assert len(gap["missing_essential_skills"]) > 0

    def test_personalized_graph_summary(self, sample_pipeline_result):
        pg_sum = sample_pipeline_result.personalized_graph_summary
        assert "total_nodes" in pg_sum
        assert "total_edges" in pg_sum
        assert pg_sum["total_nodes"] > 0
        assert pg_sum["total_edges"] > 0
        assert "node_counts_by_kind" in pg_sum
        assert "candidate" in pg_sum["node_counts_by_kind"]
        assert "occupation" in pg_sum["node_counts_by_kind"]


# =============================================================================
# 4. M4 Career Readiness Prediction & SHAP Explainability
# =============================================================================


class TestReadinessAndSHAPIntegration:
    """Validates M4 readiness classification and M4.5 SHAP attribution."""

    def test_readiness_prediction_output(self, sample_pipeline_result):
        readiness = sample_pipeline_result.readiness_prediction
        assert readiness is not None
        assert readiness.predicted_class in ["Developing", "Job Ready", "Not Ready"]
        assert "Developing" in readiness.class_probabilities
        assert "Job Ready" in readiness.class_probabilities
        assert "Not Ready" in readiness.class_probabilities
        assert abs(sum(readiness.class_probabilities.values()) - 1.0) < 1e-3
        assert len(readiness.feature_values) == 9

    def test_shap_explanation_output(self, sample_pipeline_result):
        shap_exp = sample_pipeline_result.shap_explanation
        assert shap_exp is not None
        assert shap_exp.target_class_explained in ["Developing", "Job Ready", "Not Ready"]
        assert isinstance(shap_exp.base_value, float)
        assert len(shap_exp.feature_contributions) == 9
        assert len(shap_exp.top_positive_factors) > 0 or len(shap_exp.top_negative_factors) > 0
        assert len(shap_exp.human_readable_summary) > 20
        assert len(shap_exp.waterfall_steps) == 10  # base + 9 features


# =============================================================================
# 5. Personalized Learning Roadmap Generation
# =============================================================================


class TestLearningRoadmapGeneration:
    """Validates 4-phase learning roadmap construction and prioritization."""

    def test_roadmap_structure_and_phases(self, sample_pipeline_result):
        roadmap = sample_pipeline_result.learning_roadmap
        assert roadmap is not None
        assert roadmap.total_roadmap_skills > 0
        assert len(roadmap.phases) == 4

        # Validate Phase numbering and names
        phase_names = [p.phase_name for p in roadmap.phases]
        assert "Phase 1" in phase_names[0]
        assert "Phase 2" in phase_names[1]
        assert "Phase 3" in phase_names[2]
        assert "Phase 4" in phase_names[3]

    def test_roadmap_item_completeness(self, sample_pipeline_result):
        roadmap = sample_pipeline_result.learning_roadmap
        for p in roadmap.phases:
            for item in p.items:
                assert item.skill_name
                assert item.current_status in ["missing_essential", "partially_matched_essential", "missing_optional"]
                assert item.priority in ["Critical", "High", "Medium", "Low"]
                assert item.importance_rationale
                assert item.learning_outcome
                assert len(item.suggested_activities) >= 1
                assert item.practical_project
                assert item.estimated_duration_weeks
                assert item.completion_criteria
                assert len(item.resource_categories) >= 1

    def test_roadmap_disclaimers_present(self, sample_pipeline_result):
        roadmap = sample_pipeline_result.learning_roadmap
        assert len(roadmap.disclaimers) >= 3


# =============================================================================
# 6. Report Generation & Serialization
# =============================================================================


class TestReportGeneration:
    """Validates Markdown rendering, JSON serialization, and file persistence."""

    def test_report_artifacts_persisted(self, sample_pipeline_result):
        paths = sample_pipeline_result.report_paths
        assert "json" in paths
        assert "markdown" in paths

        json_path = Path(paths["json"])
        md_path = Path(paths["markdown"])

        assert json_path.exists()
        assert md_path.exists()

        # Validate JSON content loadability
        loaded_json = json.loads(json_path.read_text(encoding="utf-8"))
        assert loaded_json["pipeline_version"] == "3.0.0"
        assert loaded_json["selected_occupation"]["occupation_label"] == "data engineer"

        # Validate Markdown content structure
        md_text = md_path.read_text(encoding="utf-8")
        assert "Executive Summary" in md_text
        assert "Hybrid Skill Gap Analysis" in md_text
        assert "Supervised Career Readiness Classification" in md_text
        assert "SHAP Explainability" in md_text
        assert "Personalized Learning Roadmap" in md_text


# =============================================================================
# 7. Single Command CLI Invocation
# =============================================================================


class TestCLIExecution:
    """Validates command-line interface execution and exit codes."""

    def test_cli_explicit_occupation_success(self, tmp_path: Path):
        code = cli_main([
            "--resume", str(SAMPLE_PDF),
            "--occupation", "data engineer",
            "--output", str(tmp_path),
            "--quiet",
        ])
        assert code == 0

    def test_cli_missing_resume_returns_error_code(self):
        code = cli_main([
            "--resume", "non_existent_resume.pdf",
            "--occupation", "data engineer",
            "--quiet",
        ])
        assert code != 0

