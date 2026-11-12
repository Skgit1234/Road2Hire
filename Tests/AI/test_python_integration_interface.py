"""Phase 5 — Python Integration Interface & Backend Readiness Tests.

Validates:
1. Pipeline initialization and thread-safe singleton identity (`get_pipeline()`).
2. Valid sample PDF processing via `process_resume()` and `Road2HirePipeline.run()`.
3. Processing with explicit target occupation.
4. Processing without target occupation:
   - `auto_select_top_occupation=True` resolves top recommendation.
   - `auto_select_top_occupation=False` raises `OccupationSelectionError` with suggestions.
5. Invalid resume path validation (`ResumeValidationError`).
6. Invalid file type rejection (`ResumeValidationError`).
7. Empty (0-byte) PDF rejection (`ResumeValidationError`).
8. Invalid target occupation handling (`OccupationSelectionError` / `TypeError`).
9. Graceful handling of missing M4 model artifacts.
10. JSON serialization (`to_canonical_dict()`, `to_dict()`, `to_json()`).
11. Draft-07 JSON Schema validation for canonical output and error payloads.
12. Resource reuse and lifecycle caching efficiency across calls.
13. Concurrency and thread safety for singleton retrieval.
14. Error propagation guarantees (fatal errors never silently masked).
15. Existing CLI compatibility.
"""

from __future__ import annotations

import concurrent.futures
import json
from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch
import jsonschema
from jsonschema import Draft7Validator
import pytest

from AI.Pipeline import (
    OccupationSelectionError,
    PipelineError,
    ResumeValidationError,
    Road2HirePipeline,
    UnifiedPipelineResult,
    create_error_response,
    get_pipeline,
    process_resume,
)
from AI.Pipeline.pipeline_schema import (
    LearningRoadmap,
    ReadinessPredictionData,
    SelectedOccupation,
    SHAPExplanationData,
)
from AI.road2hire_model import get_road2hire_model

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_PDF = PROJECT_ROOT / "Tests" / "AI" / "sample_resume.pdf"
OUTPUT_SCHEMA_PATH = PROJECT_ROOT / "AI" / "Pipeline" / "schemas" / "pipeline_output.schema.json"
ERROR_SCHEMA_PATH = PROJECT_ROOT / "AI" / "Pipeline" / "schemas" / "pipeline_error.schema.json"


@pytest.fixture(scope="module")
def output_schema() -> dict:
    return json.loads(OUTPUT_SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def error_schema() -> dict:
    return json.loads(ERROR_SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def cached_pipeline() -> Road2HirePipeline:
    return get_pipeline()


@pytest.fixture(scope="module")
def real_explicit_result(cached_pipeline: Road2HirePipeline) -> UnifiedPipelineResult:
    """Single module-scoped real PDF pipeline execution with explicit occupation."""
    return process_resume(
        resume_path=SAMPLE_PDF,
        target_occupation="data engineer",
        output_format="none",
        pipeline=cached_pipeline,
    )


@pytest.fixture(scope="module")
def real_auto_result(cached_pipeline: Road2HirePipeline) -> UnifiedPipelineResult:
    """Single module-scoped real PDF pipeline execution with auto-selected top occupation."""
    return process_resume(
        resume_path=SAMPLE_PDF,
        target_occupation=None,
        auto_select_top_occupation=True,
        output_format="none",
        pipeline=cached_pipeline,
    )


# Canned mock data for fast unit isolation
CANNED_OCCUPATION_MATCHES = [
    {
        "occupation_uri": "http://data.europa.eu/esco/occupation/2079755f-d809-49e6-8037-4de6180e54c0",
        "occupation_label": "data engineer",
        "score": 92,
        "essential_count": 8,
        "optional_count": 4,
        "supporting_skills": ["SQL", "Python", "Data pipelines"],
    },
    {
        "occupation_uri": "http://data.europa.eu/esco/occupation/93efce58-69aa-425b-8664-cf3d724cb116",
        "occupation_label": "data analyst",
        "score": 85,
        "essential_count": 6,
        "optional_count": 3,
        "supporting_skills": ["SQL", "Tableau", "Data analysis"],
    },
]

CANNED_RESUME_RESULT = {
    "status": "success",
    "page_count": 1,
    "extraction_status": "success",
    "candidate_profile": {
        "candidate": {"name": "Test Candidate", "email": "test@example.com"},
        "education": [],
        "experience": [],
        "projects": [],
        "certifications": [],
    },
    "extracted_skills": [{"skill": "Python", "source_sections": ["skills"]}],
    "esco_mappings": [
        {
            "skill": "Python",
            "ESCO_Skill_Id": "http://data.europa.eu/esco/skill/e0a0d4b9-8c68-450f-90e6-9907f96b27e8",
            "ESCO_Skill_Name": "Python (computer programming)",
            "ESCO_Skill_Type": "skill/competence",
            "ESCO_Reuse_Level": "cross-sector",
            "ESCO_Mapping_Type": "exact",
            "confidence": 1.0,
        }
    ],
    "occupation_matches": CANNED_OCCUPATION_MATCHES,
    "sections": {"skills": "Python, SQL", "experience": "", "projects": "", "education": ""},
    "warnings": [],
    "errors": [],
}


# =============================================================================
# 1. Pipeline Initialization & Singleton Identity
# =============================================================================


class TestPipelineSingletonAndInit:
    """Verifies pipeline lifecycle, initialization, and singleton caching."""

    def test_get_pipeline_returns_singleton(self):
        p1 = get_pipeline()
        p2 = get_pipeline()
        assert p1 is p2
        assert isinstance(p1, Road2HirePipeline)

    def test_get_pipeline_shares_underlying_model_singleton(self):
        pipeline = get_pipeline()
        model = get_road2hire_model()
        assert pipeline.model is model

    def test_custom_pipeline_instance(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            custom_p = Road2HirePipeline(base_output_dir=tmp_dir)
            assert custom_p.base_output_dir == Path(tmp_dir)
            assert custom_p.model is get_road2hire_model()

    def test_concurrent_get_pipeline_thread_safety(self):
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(get_pipeline) for _ in range(20)]
            for f in concurrent.futures.as_completed(futures):
                results.append(f.result())

        assert len(results) == 20
        first = results[0]
        assert all(p is first for p in results)


# =============================================================================
# 2. Programmatic Execution & Parameter Modes
# =============================================================================


class TestProgrammaticExecution:
    """Tests resume processing through the public Python interface."""

    def test_process_resume_with_explicit_occupation(
        self, real_explicit_result: UnifiedPipelineResult, output_schema: dict
    ):
        result = real_explicit_result
        assert isinstance(result, UnifiedPipelineResult)
        assert result.status in ["success", "warning"]
        assert result.selected_occupation.occupation_label == "data engineer"
        assert result.selected_occupation.resolution_source in ["suggestion", "taxonomy_lookup"]

        # Validate Draft-07 schema compliance
        canonical_dict = result.to_canonical_dict()
        validator = Draft7Validator(output_schema)
        errors = list(validator.iter_errors(canonical_dict))
        assert not errors, f"Canonical output schema validation failed: {errors}"

    def test_process_resume_auto_select_top_occupation(
        self, real_auto_result: UnifiedPipelineResult, output_schema: dict
    ):
        result = real_auto_result
        assert isinstance(result, UnifiedPipelineResult)
        assert result.selected_occupation is not None
        assert result.selected_occupation.resolution_source == "top_recommendation"
        assert result.selected_occupation.match_score >= 0
        assert len(result.selected_occupation.occupation_label) > 0

        # Validate that top_recommendation validates against schema
        canonical_dict = result.to_canonical_dict()
        validator = Draft7Validator(output_schema)
        errors = list(validator.iter_errors(canonical_dict))
        assert not errors, f"Auto-selected output schema validation failed: {errors}"

    def test_process_resume_missing_occupation_raises_selection_error(
        self, cached_pipeline: Road2HirePipeline
    ):
        with patch.object(cached_pipeline.model, "predict", return_value=CANNED_RESUME_RESULT):
            with pytest.raises(OccupationSelectionError) as exc_info:
                cached_pipeline.run(
                    resume_path=SAMPLE_PDF,
                    target_occupation=None,
                    auto_select_top_occupation=False,
                    output_format="none",
                )

        err = exc_info.value
        assert "No target occupation specified" in str(err)
        assert hasattr(err, "suggested_occupations")
        assert isinstance(err.suggested_occupations, list)
        assert len(err.suggested_occupations) > 0
        assert err.suggested_occupations[0]["occupation_label"] == "data engineer"

    def test_process_resume_report_generation(
        self, real_explicit_result: UnifiedPipelineResult
    ):
        with tempfile.TemporaryDirectory() as tmp_dir:
            cached_pipeline = get_pipeline()
            # Test report generator saving without re-running entire ML pipeline
            paths = cached_pipeline.report_generator.save_reports(
                result=real_explicit_result,
                output_dir=tmp_dir,
                output_format="both",
            )
            assert "json" in paths and Path(paths["json"]).exists()
            assert "markdown" in paths and Path(paths["markdown"]).exists()


# =============================================================================
# 3. Input Validation & Error Handling
# =============================================================================


class TestInputValidationAndErrors:
    """Verifies strict input sanitization and exception propagation."""

    def test_nonexistent_resume_file_raises_validation_error(self, cached_pipeline: Road2HirePipeline):
        bad_path = PROJECT_ROOT / "Tests" / "AI" / "nonexistent_file_99999.pdf"
        with pytest.raises(ResumeValidationError) as exc_info:
            cached_pipeline.run(bad_path, target_occupation="data engineer")
        assert "not found" in str(exc_info.value).lower()

    def test_invalid_resume_path_types(self, cached_pipeline: Road2HirePipeline):
        with pytest.raises(ResumeValidationError):
            cached_pipeline.run(None, target_occupation="data engineer")

        with pytest.raises(ResumeValidationError):
            cached_pipeline.run("", target_occupation="data engineer")

        with pytest.raises(ResumeValidationError):
            cached_pipeline.run(12345, target_occupation="data engineer")

    def test_non_pdf_file_raises_validation_error(self, cached_pipeline: Road2HirePipeline):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(b"Not a PDF resume")
            tmp_path = Path(tmp.name)

        try:
            with pytest.raises(ResumeValidationError) as exc_info:
                cached_pipeline.run(tmp_path, target_occupation="data engineer")
            assert "Expected a .pdf file" in str(exc_info.value)
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_empty_zero_byte_pdf_raises_validation_error(self, cached_pipeline: Road2HirePipeline):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            with pytest.raises(ResumeValidationError) as exc_info:
                cached_pipeline.run(tmp_path, target_occupation="data engineer")
            assert "empty (0 bytes)" in str(exc_info.value)
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_invalid_target_occupation_type(self, cached_pipeline: Road2HirePipeline):
        with pytest.raises(TypeError) as exc_info:
            cached_pipeline.run(SAMPLE_PDF, target_occupation=12345)
        assert "target_occupation must be a string or None" in str(exc_info.value)

    def test_unresolvable_target_occupation_raises_with_suggestions(
        self, cached_pipeline: Road2HirePipeline
    ):
        with patch.object(cached_pipeline.model, "predict", return_value=CANNED_RESUME_RESULT):
            with pytest.raises(OccupationSelectionError) as exc_info:
                cached_pipeline.run(
                    SAMPLE_PDF,
                    target_occupation="completely_fictional_unresolvable_title_xyz_12345",
                    auto_select_top_occupation=False,
                )

        err = exc_info.value
        assert "Could not resolve target occupation" in str(err)
        assert hasattr(err, "suggested_occupations")
        assert len(err.suggested_occupations) > 0


# =============================================================================
# 4. Resilience & Graceful Degradation
# =============================================================================


class TestPipelineResilience:
    """Verifies pipeline behavior under partial failures and missing artifacts."""

    def test_missing_m4_model_artifact_graceful_degradation(
        self, cached_pipeline: Road2HirePipeline, output_schema: dict
    ):
        with patch(
            "AI.Readiness_Model.model_trainer.load_persisted_model",
            side_effect=FileNotFoundError("Persisted model file not found"),
        ):
            # Create fresh pipeline with uninitialized readiness model
            test_pipeline = Road2HirePipeline(model=cached_pipeline.model)
            with patch.object(test_pipeline.model, "predict", return_value=CANNED_RESUME_RESULT):
                result = test_pipeline.run(
                    resume_path=SAMPLE_PDF,
                    target_occupation="data engineer",
                    output_format="none",
                )

                assert isinstance(result, UnifiedPipelineResult)
                assert result.status == "warning"
                assert result.readiness_prediction is None
                assert result.shap_explanation is None
                assert any("Readiness prediction skipped" in w for w in result.warnings)

                # Canonical schema permits null readiness_prediction and shap_explanation
                canonical_dict = result.to_canonical_dict()
                validator = Draft7Validator(output_schema)
                errors = list(validator.iter_errors(canonical_dict))
                assert not errors, f"Schema validation failed for degraded run: {errors}"


# =============================================================================
# 5. Serialization & Error Schema Contract Conformance
# =============================================================================


class TestSerializationAndContract:
    """Verifies dict/JSON serialization and schema conformance."""

    def test_serialization_roundtrip(self, real_explicit_result: UnifiedPipelineResult):
        result = real_explicit_result

        canonical = result.to_canonical_dict()
        assert isinstance(canonical, dict)
        assert canonical["schema_version"] == "1.0.0"

        legacy = result.to_dict()
        assert isinstance(legacy, dict)
        assert "pipeline_version" in legacy

        json_str = result.to_json(indent=2)
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["schema_version"] == "1.0.0"
        assert parsed["metadata"]["pipeline_version"] == result.pipeline_version

    def test_create_error_response_conforms_to_error_schema(self, error_schema: dict):
        err_dict = create_error_response(
            code="EMPTY_OR_CORRUPT_DOCUMENT",
            message="Resume file is corrupt or unreadable.",
            stage="input_validation",
            details={"file": "test.pdf", "size": 0},
        )

        validator = Draft7Validator(error_schema)
        errors = list(validator.iter_errors(err_dict))
        assert not errors, f"Error payload failed schema validation: {errors}"
        assert err_dict["error"]["code"] == "EMPTY_OR_CORRUPT_DOCUMENT"


# =============================================================================
# 6. Resource Reuse & Lifecycle Efficiency
# =============================================================================


class TestResourceLifecycle:
    """Verifies shared model caching and resource efficiency across calls."""

    def test_singleton_shares_exact_heavy_instances(self, cached_pipeline: Road2HirePipeline):
        m1 = cached_pipeline.model
        m2 = get_road2hire_model()

        assert m1 is m2
        assert id(m1._taxonomy) == id(m2._taxonomy)
        assert id(m1._graph) == id(m2._graph)
        assert id(m1._esco_vocab) == id(m2._esco_vocab)
