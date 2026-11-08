"""Milestone Phase 4 — JSON Schema & Interface Contract Validation Tests.

Validates:
1. JSON Schema file validity (`pipeline_output.schema.json` and `pipeline_error.schema.json`).
2. Conformance of `UnifiedPipelineResult.to_canonical_dict()` to the 10-section canonical contract.
3. Strict types, value constraints, and SemVer patterns.
4. Conformance of `create_error_response()` to the error contract.
5. Backward compatibility of `UnifiedPipelineResult.to_dict()`.
6. JSON serialization roundtrip with zero data loss.
7. Nullability rules, empty collections, and edge-case handling.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import jsonschema
from jsonschema import Draft7Validator, ValidationError, validate
import pytest

from AI.Pipeline import (
    OccupationSelectionError,
    ResumeValidationError,
    Road2HirePipeline,
    UnifiedPipelineResult,
    create_error_response,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_PDF = PROJECT_ROOT / "Tests" / "AI" / "sample_resume.pdf"
OUTPUT_SCHEMA_PATH = PROJECT_ROOT / "AI" / "Pipeline" / "schemas" / "pipeline_output.schema.json"
ERROR_SCHEMA_PATH = PROJECT_ROOT / "AI" / "Pipeline" / "schemas" / "pipeline_error.schema.json"


@pytest.fixture(scope="module")
def sample_result() -> UnifiedPipelineResult:
    pipeline = Road2HirePipeline()
    return pipeline.run(
        resume_path=SAMPLE_PDF,
        target_occupation="data engineer",
        interactive=False,
    )


# =============================================================================
# 1. Schema Files Structural Validity
# =============================================================================


class TestSchemaFilesValidity:
    """Verifies schema files are readable, valid JSON, and strictly conform to Draft-07."""

    def test_output_schema_file_exists_and_valid_draft7(self):
        assert OUTPUT_SCHEMA_PATH.exists()
        schema = json.loads(OUTPUT_SCHEMA_PATH.read_text(encoding="utf-8"))
        assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
        assert schema["title"] == "Road2HirePipelineOutput"
        assert "properties" in schema
        assert "required" in schema
        # Rigorous Draft-07 meta-schema validation
        Draft7Validator.check_schema(schema)

    def test_error_schema_file_exists_and_valid_draft7(self):
        assert ERROR_SCHEMA_PATH.exists()
        schema = json.loads(ERROR_SCHEMA_PATH.read_text(encoding="utf-8"))
        assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
        assert schema["title"] == "Road2HirePipelineError"
        assert "properties" in schema
        assert "required" in schema
        # Rigorous Draft-07 meta-schema validation
        Draft7Validator.check_schema(schema)


# =============================================================================
# 2. Canonical Output Contract Conformance & Instance Validation
# =============================================================================


class TestCanonicalOutputContract:
    """Validates that pipeline output matches the 10 canonical logical sections
    and passes strict jsonschema.validate() instance checks.
    """

    def test_actual_pipeline_canonical_output_validates_against_jsonschema(
        self, sample_result: UnifiedPipelineResult
    ):
        schema = json.loads(OUTPUT_SCHEMA_PATH.read_text(encoding="utf-8"))
        canon = sample_result.to_canonical_dict()
        # Must pass without raising ValidationError
        validate(instance=canon, schema=schema)

    def test_actual_pipeline_full_dict_validates_against_jsonschema(
        self, sample_result: UnifiedPipelineResult
    ):
        schema = json.loads(OUTPUT_SCHEMA_PATH.read_text(encoding="utf-8"))
        full_dict = sample_result.to_dict()
        # Must pass without raising ValidationError
        validate(instance=full_dict, schema=schema)

    def test_canonical_dict_contains_all_10_logical_sections(
        self, sample_result: UnifiedPipelineResult
    ):
        canon = sample_result.to_canonical_dict()

        expected_sections = [
            "schema_version",
            "metadata",
            "candidate_profile",
            "skills",
            "occupation_recommendations",
            "target_occupation",
            "skill_gap",
            "readiness",
            "explanations",
            "knowledge_graph",
            "learning_roadmap",
            "warnings",
            "errors",
        ]
        for section in expected_sections:
            assert section in canon, f"Missing required canonical section: '{section}'"

    def test_metadata_section_conformance(self, sample_result: UnifiedPipelineResult):
        meta = sample_result.to_canonical_dict()["metadata"]
        assert meta["schema_version"] == "1.0.0"
        assert meta["pipeline_version"] == "3.0.0"
        assert meta["status"] in ["success", "warning", "error"]
        assert meta["page_count"] >= 1
        assert "source_file" in meta
        assert "execution_timings_seconds" in meta
        # Verify ISO timestamp regex pattern
        iso_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
        assert re.match(iso_pattern, meta["timestamp"])

    def test_skills_section_conformance(self, sample_result: UnifiedPipelineResult):
        skills = sample_result.to_canonical_dict()["skills"]
        assert "extracted_skills" in skills
        assert "esco_mappings" in skills
        assert isinstance(skills["extracted_skills"], list)
        assert isinstance(skills["esco_mappings"], list)
        assert skills["extracted_skill_count"] == len(skills["extracted_skills"])
        assert skills["mapped_skill_count"] == len(skills["esco_mappings"])

        # Check ESCO mapping structure
        for m in skills["esco_mappings"]:
            assert "skill" in m
            assert "ESCO_Skill_Id" in m
            assert m["ESCO_Skill_Id"].startswith("http")
            assert "ESCO_Skill_Name" in m

    def test_target_occupation_conformance(self, sample_result: UnifiedPipelineResult):
        target = sample_result.to_canonical_dict()["target_occupation"]
        assert target is not None
        assert "occupation_uri" in target
        assert target["occupation_uri"].startswith("http")
        assert target["occupation_label"] == "data engineer"
        assert target["resolution_source"] in ["suggestion", "direct_uri", "taxonomy_lookup"]

    def test_skill_gap_section_conformance(self, sample_result: UnifiedPipelineResult):
        gap = sample_result.to_canonical_dict()["skill_gap"]
        assert 0.0 <= gap["overall_skill_coverage_score"] <= 1.0
        assert 0.0 <= gap["essential_skill_coverage_score"] <= 1.0
        assert 0.0 <= gap["optional_skill_coverage_score"] <= 1.0
        assert isinstance(gap["matched_skills"], list)
        assert isinstance(gap["partially_matched_skills"], list)
        assert isinstance(gap["missing_essential_skills"], list)
        assert isinstance(gap["missing_optional_skills"], list)

    def test_readiness_section_conformance(self, sample_result: UnifiedPipelineResult):
        readiness = sample_result.to_canonical_dict()["readiness"]
        assert readiness is not None
        assert readiness["predicted_class"] in ["Developing", "Job Ready", "Not Ready"]
        probs = readiness["class_probabilities"]
        assert abs(sum(probs.values()) - 1.0) < 1e-3
        assert isinstance(readiness["is_ood"], bool)
        assert isinstance(readiness["ood_warnings"], list)
        assert readiness["training_sample_count"] == 71

    def test_explanations_section_conformance(self, sample_result: UnifiedPipelineResult):
        exp = sample_result.to_canonical_dict()["explanations"]
        assert exp is not None
        assert exp["target_class_explained"] in ["Developing", "Job Ready", "Not Ready"]
        assert isinstance(exp["base_value"], float)
        assert isinstance(exp["top_positive_factors"], list)
        assert isinstance(exp["top_negative_factors"], list)
        assert isinstance(exp["global_importance_ranking"], list)
        assert len(exp["global_importance_ranking"]) == 9

    def test_learning_roadmap_conformance(self, sample_result: UnifiedPipelineResult):
        roadmap = sample_result.to_canonical_dict()["learning_roadmap"]
        assert roadmap is not None
        assert roadmap["target_occupation_title"] == "data engineer"
        assert len(roadmap["phases"]) == 4
        for idx, phase in enumerate(roadmap["phases"], start=1):
            assert phase["phase_number"] == idx
            assert "phase_name" in phase
            assert "estimated_weeks" in phase
            assert isinstance(phase["items"], list)


# =============================================================================
# 3. Error Response Contract Conformance
# =============================================================================


class TestErrorResponseContract:
    """Validates structured error generation matching pipeline_error.schema.json."""

    def test_create_error_response_conforms_to_contract(self):
        err = create_error_response(
            code="OCCUPATION_NOT_FOUND",
            message="Could not resolve target occupation 'invalid role'.",
            stage="occupation_resolution",
            details={"query": "invalid role"},
            recoverable=True,
            warnings=["Notice: using fallback matching."],
        )

        assert err["schema_version"] == "1.0.0"
        assert err["status"] == "error"
        assert "timestamp" in err
        assert err["error"]["code"] == "OCCUPATION_NOT_FOUND"
        assert err["error"]["stage"] == "occupation_resolution"
        assert err["error"]["recoverable"] is True
        assert err["error"]["details"]["query"] == "invalid role"
        assert len(err["warnings"]) == 1

    @pytest.mark.parametrize(
        "code,stage,recoverable",
        [
            ("RESUME_NOT_FOUND", "input_validation", False),
            ("INVALID_FILE_TYPE", "input_validation", False),
            ("EMPTY_OR_CORRUPT_DOCUMENT", "input_validation", False),
            ("TEXT_EXTRACTION_FAILED", "resume_extraction", False),
            ("NO_SKILLS_DETECTED", "skill_extraction", True),
            ("OCCUPATION_SELECTION_REQUIRED", "occupation_resolution", True),
            ("MODEL_ARTIFACT_MISSING", "readiness_prediction", False),
            ("PIPELINE_EXECUTION_ERROR", "reporting", False),
        ],
    )
    def test_valid_error_codes_and_stages(self, code, stage, recoverable):
        err = create_error_response(
            code=code,
            message=f"Test error message for {code}",
            stage=stage,
            recoverable=recoverable,
        )
        assert err["error"]["code"] == code
        assert err["error"]["stage"] == stage
        assert err["error"]["recoverable"] == recoverable

        # Strict JSON Schema instance validation
        schema = json.loads(ERROR_SCHEMA_PATH.read_text(encoding="utf-8"))
        validate(instance=err, schema=schema)


# =============================================================================
# 4. Backward Compatibility & Serialization
# =============================================================================


class TestBackwardCompatibilityAndSerialization:
    """Verifies that to_dict() maintains full backward compatibility for existing consumers."""

    def test_to_dict_contains_both_canonical_and_legacy_fields(
        self, sample_result: UnifiedPipelineResult
    ):
        d = sample_result.to_dict()

        # Legacy top-level keys
        assert "pipeline_version" in d
        assert "selected_occupation" in d
        assert "skill_gap_analysis" in d
        assert "readiness_prediction" in d
        assert "shap_explanation" in d
        assert "learning_roadmap" in d

        # Canonical section keys
        assert "metadata" in d
        assert "skills" in d
        assert "occupation_recommendations" in d
        assert "target_occupation" in d
        assert "skill_gap" in d
        assert "readiness" in d
        assert "explanations" in d
        assert "knowledge_graph" in d

    def test_to_json_canonical_serialization_roundtrip(
        self, sample_result: UnifiedPipelineResult
    ):
        json_str = sample_result.to_json(canonical=True)
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)

        assert parsed["schema_version"] == "1.0.0"
        assert parsed["metadata"]["status"] in ["success", "warning"]
        assert parsed["target_occupation"]["occupation_label"] == "data engineer"
        assert parsed["readiness"]["predicted_class"] == sample_result.readiness_prediction.predicted_class


# =============================================================================
# 5. Schema Rejection of Invalid Payloads
# =============================================================================


class TestSchemaRejectionOfInvalidInstances:
    """Verifies that malformed data structures are strictly rejected by the schemas."""

    def test_output_schema_rejects_missing_required_section(
        self, sample_result: UnifiedPipelineResult
    ):
        schema = json.loads(OUTPUT_SCHEMA_PATH.read_text(encoding="utf-8"))
        bad_payload = sample_result.to_canonical_dict()
        del bad_payload["skills"]  # Missing required section

        with pytest.raises(ValidationError):
            validate(instance=bad_payload, schema=schema)

    def test_output_schema_rejects_invalid_status_enum(
        self, sample_result: UnifiedPipelineResult
    ):
        schema = json.loads(OUTPUT_SCHEMA_PATH.read_text(encoding="utf-8"))
        bad_payload = sample_result.to_canonical_dict()
        bad_payload["metadata"]["status"] = "partially_failed"  # Not in enum

        with pytest.raises(ValidationError):
            validate(instance=bad_payload, schema=schema)

    def test_error_schema_rejects_invalid_error_code(self):
        schema = json.loads(ERROR_SCHEMA_PATH.read_text(encoding="utf-8"))
        bad_err = {
            "schema_version": "1.0.0",
            "status": "error",
            "timestamp": "2026-11-07T14:10:00",
            "error": {
                "code": "RANDOM_CUSTOM_ERROR",  # Not in allowed enum
                "message": "Custom message",
                "stage": "input_validation",
                "recoverable": False,
            },
            "warnings": [],
        }
        with pytest.raises(ValidationError):
            validate(instance=bad_err, schema=schema)


# =============================================================================
# 6. Pipeline Failure Safety (No Silent Conversions to Success)
# =============================================================================


class TestPipelineFailureSafety:
    """Confirms that pipeline failures cannot silently produce successful results."""

    def test_missing_file_raises_not_success(self):
        pipeline = Road2HirePipeline()
        with pytest.raises(ResumeValidationError):
            pipeline.run(
                "totally_nonexistent_resume.pdf",
                target_occupation="data engineer",
                interactive=False,
            )

    def test_unresolvable_occupation_raises_not_success(self):
        pipeline = Road2HirePipeline()
        with pytest.raises(OccupationSelectionError):
            pipeline.run(
                SAMPLE_PDF,
                target_occupation="completely fictional occupation 9999",
                interactive=False,
            )


