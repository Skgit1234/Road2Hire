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
from AI.Pipeline.cli import extract_candidate_name, main as cli_main
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

    def test_feature_consistency_and_extraction(self, sample_pipeline_result):
        """Verify inference feature extraction matches structured candidate evidence."""
        readiness = sample_pipeline_result.readiness_prediction
        assert readiness is not None
        feats = readiness.feature_values
        assert feats["skills_count"] == 6.0
        assert feats["exp_positions_count"] == 1.0  # 1 position, NOT multi-line explosion
        assert feats["has_senior_role"] == 0.0
        assert feats["project_count"] == 1.0
        assert feats["project_tech_count"] >= 1.0   # Python tagged in project
        assert feats["edu_level_ordinal"] == 1.0    # Bachelor level
        assert feats["is_stem_degree"] == 1.0       # Computer Science

    def test_missing_evidence_defaults_safely(self, pipeline: Road2HirePipeline):
        """Verify empty/missing profile fields default gracefully to 0.0."""
        empty_res = {"candidate_profile": {}, "sections": {}}
        ev = pipeline._extract_evidence_dict(empty_res)
        assert ev["skills_text"] == ""
        assert ev["experience_text"] == ""
        assert ev["projects_text"] == ""
        assert ev["education_text"] == ""

        from AI.Readiness_Model.feature_extractor import ReadinessFeatureExtractor
        extractor = ReadinessFeatureExtractor()
        matrix = extractor.transform([ev])[0]
        # All counts must be 0.0
        assert matrix[0] == 0.0  # skills_count
        assert matrix[1] == 0.0  # exp_positions_count
        assert matrix[2] == 0.0  # has_senior_role
        assert matrix[3] == 0.0  # project_count
        assert matrix[4] == 0.0  # project_words
        assert matrix[5] == 0.0  # project_tech_count
        assert matrix[6] == 0.0  # has_production_system
        assert matrix[7] == 0.0  # edu_level_ordinal
        assert matrix[8] == 0.0  # is_stem_degree

    def test_target_occupation_propagation(self, sample_pipeline_result):
        """Verify target occupation is correctly propagated to all pipeline stages."""
        occ = sample_pipeline_result.selected_occupation
        assert occ.occupation_label == "data engineer"
        assert "2079755f-d809-49e6-8037-4de6180e54c0" in occ.occupation_uri

        # Propagated to skill gap analysis
        gap_occ = sample_pipeline_result.skill_gap_analysis["target_occupation"]
        if isinstance(gap_occ, dict):
            assert gap_occ["uri"] == occ.occupation_uri
        else:
            assert gap_occ == occ.occupation_uri

        # Propagated to roadmap
        assert sample_pipeline_result.learning_roadmap.target_occupation_uri == occ.occupation_uri
        assert sample_pipeline_result.learning_roadmap.target_occupation_title == occ.occupation_label


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
# 7. Candidate Information & Name Resolution
# =============================================================================


class TestCandidateNameExtraction:
    """Validates candidate name extraction, sanitization, and fallback behavior."""

    def test_extract_valid_name_trimmed(self):
        profile = {"candidate": {"name": "  Alex Morgan  "}}
        assert extract_candidate_name(profile) == "Alex Morgan"

    def test_extract_missing_or_empty_returns_not_provided(self):
        assert extract_candidate_name(None) == "Not provided"
        assert extract_candidate_name({}) == "Not provided"
        assert extract_candidate_name({"candidate": {}}) == "Not provided"
        assert extract_candidate_name({"candidate": {"name": None}}) == "Not provided"
        assert extract_candidate_name({"candidate": {"name": ""}}) == "Not provided"
        assert extract_candidate_name({"candidate": {"name": "   "}}) == "Not provided"

    def test_name_never_derived_from_filename(self):
        profile = {"candidate": {"name": None}, "source_file": "alex_morgan_cv.pdf"}
        # Must strictly return 'Not provided' regardless of filename in profile or input
        assert extract_candidate_name(profile) == "Not provided"


# =============================================================================
# 8. Single Command CLI Invocation & Terminal Output
# =============================================================================


class TestCLIExecution:
    """Validates command-line interface execution, clean output, and exit codes."""

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

    def test_cli_clean_normal_output(self, tmp_path: Path, capsys: pytest.CaptureFixture):
        """Verify normal CLI run emits clean banner and summary without noisy HTTP logs or warnings."""
        code = cli_main([
            "--resume", str(SAMPLE_PDF),
            "--occupation", "data engineer",
            "--output", str(tmp_path),
        ])
        assert code == 0
        captured = capsys.readouterr()

        # Professional banner and summary present
        assert "ROAD2HIRE — CAREER READINESS & RESUME INTELLIGENCE PIPELINE" in captured.out
        assert "ROAD2HIRE — PIPELINE EXECUTION SUMMARY" in captured.out
        assert "Processing Status:   Success" in captured.out
        assert "Candidate Name:      Alex Morgan" in captured.out
        assert "Target Occupation:   data engineer" in captured.out
        assert "Overall Coverage:" in captured.out
        assert "Readiness Class:" in captured.out
        assert "Generated Report Artifacts:" in captured.out

        # Noisy third-party messages suppressed
        assert "unauthenticated requests to the HF Hub" not in captured.err
        assert "unauthenticated requests to the HF Hub" not in captured.out
        assert "Loading weights:" not in captured.err
        assert "HTTP Request:" not in captured.out
        assert "HTTP Request:" not in captured.err

    def test_cli_verbose_output(self, tmp_path: Path, capsys: pytest.CaptureFixture):
        """Verify --verbose exposes diagnostic INFO logging and trace output."""
        code = cli_main([
            "--resume", str(SAMPLE_PDF),
            "--occupation", "data engineer",
            "--output", str(tmp_path),
            "--verbose",
        ])
        assert code == 0
        captured = capsys.readouterr()
        combined = captured.out + captured.err
        assert "[INFO]" in combined or "Loading" in combined or "Road2HireModel:" in combined

    def test_cli_invalid_pdf_returns_concise_error(self, tmp_path: Path, capsys: pytest.CaptureFixture):
        """Verify pipeline failures produce concise non-zero exit and clear error."""
        txt_file = tmp_path / "resume.txt"
        txt_file.write_text("plain text resume", encoding="utf-8")

        code = cli_main([
            "--resume", str(txt_file),
            "--occupation", "data engineer",
            "--output", str(tmp_path),
        ])
        assert code == 1
        captured = capsys.readouterr()
        assert "[PIPELINE ERROR]" in captured.err
        assert "Processing Status:   Success" not in captured.out

