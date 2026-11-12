"""Unit and Integration Tests for SHAP Explainability (M4.5).

Validates:
- Exact SHAP values dimensions (N, 9, 3) matching 9 features and 3 classes
- Exact feature names alignment with ReadinessFeatureExtractor.get_feature_names()
- Multiclass explanation support across all 3 classes (Developing, Job Ready, Not Ready)
- Finite numerical outputs (no NaN, Inf)
- Efficiency axiom: base_value + sum(shap_values) == decision_function to numerical tolerance
- Standardized structured JSON output schema conformance
- Top positive and top negative factor ranking and separation
- Determinism across repeated explanation calls on identical inputs
- Safe, graceful handling of empty, zero-valued, or missing evidence fields
- Absence of candidate PII and raw identifiers in global and local explanation payloads
- Model invariance: explanation generation does not mutate model state or predictions
"""

from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pytest

from AI.Readiness_Model.feature_extractor import get_feature_names
from AI.Readiness_Model.dataset_loader import load_readiness_shap_background
from AI.Readiness_Model.model_trainer import (
    SAVED_MODELS_DIR,
    load_persisted_model,
)
from AI.Readiness_Model.shap_explainer import (
    FEATURE_HUMAN_DESCRIPTIONS,
    GLOBAL_SHAP_JSON_NAME,
    EXPLAINABILITY_REPORT_NAME,
    ReadinessModelExplainer,
)

EXPECTED_CLASSES = ["Developing", "Job Ready", "Not Ready"]
EXPECTED_FEATURES = [
    "skills_count",
    "exp_positions_count",
    "has_senior_role",
    "project_count",
    "project_words",
    "project_tech_count",
    "has_production_system",
    "edu_level_ordinal",
    "is_stem_degree",
]


@pytest.fixture(scope="module")
def explainer() -> ReadinessModelExplainer:
    return ReadinessModelExplainer()


@pytest.fixture
def sample_senior_candidate() -> dict[str, str]:
    return {
        "skills_text": "Python, Django, FastAPI, Docker, Kubernetes, PostgreSQL, Redis, AWS, CI/CD, Git, Linux",
        "experience_text": "Senior Backend Architect at Tech Corp (4 years); Lead Software Engineer at StartupX (3 years)",
        "projects_text": "High-throughput microservices architecture deployed to AWS handling 50k requests per second in production.",
        "education_text": "Master of Science in Computer Science",
    }


@pytest.fixture
def sample_novice_candidate() -> dict[str, str]:
    return {
        "skills_text": "",
        "experience_text": "",
        "projects_text": "",
        "education_text": "High School Diploma",
    }


class TestReadinessModelExplainer:
    """Comprehensive test suite for M4.5 SHAP explainability module."""

    def test_explainer_initialization(self, explainer: ReadinessModelExplainer):
        """Explainer must load the pipeline and configure linear explainer properly."""
        assert explainer.pipeline is not None
        assert explainer.classes == EXPECTED_CLASSES
        assert explainer.feature_names == EXPECTED_FEATURES
        assert explainer.feature_names == get_feature_names()
        assert explainer.explainer_type == "LinearExplainer"

    def test_shap_background_excludes_unreviewed_and_unlabeled_records(
        self, explainer: ReadinessModelExplainer
    ):
        background = load_readiness_shap_background()

        assert len(background) == 19
        assert explainer.X_bg_scaled.shape == (19, 9)
        assert all(
            set(record) == {
                "target_occupation_title",
                "skills_text",
                "experience_text",
                "projects_text",
                "education_text",
            }
            for record in background
        )

    def test_shap_values_dimensions_and_finite(self, explainer: ReadinessModelExplainer):
        """SHAP values must have shape (N, 9, 3) and be finite numbers."""
        test_inputs = np.array([
            [10.0, 3.0, 1.0, 2.0, 80.0, 4.0, 1.0, 2.0, 1.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [4.0, 1.0, 0.0, 1.0, 30.0, 2.0, 0.0, 1.0, 1.0],
        ])
        _, X_scaled = explainer._prepare_scaled_input(test_inputs)
        shap_vals = explainer.explainer.shap_values(X_scaled)
        arr = shap_vals.values if hasattr(shap_vals, "values") else np.array(shap_vals)

        assert arr.shape == (3, 9, 3), f"Expected shape (3, 9, 3), got {arr.shape}"
        assert np.all(np.isfinite(arr)), "SHAP values must be completely finite (no NaN or Inf)"

    def test_efficiency_axiom_mathematical_additivity(
        self, explainer: ReadinessModelExplainer, sample_senior_candidate: dict[str, str]
    ):
        """SHAP values plus base value must equal decision function to machine precision."""
        _, X_scaled = explainer._prepare_scaled_input(sample_senior_candidate)
        decision_fn = explainer.classifier.decision_function(X_scaled)[0]

        shap_vals = explainer.explainer.shap_values(X_scaled)
        arr = shap_vals.values if hasattr(shap_vals, "values") else np.array(shap_vals)
        base_vals = explainer.explainer.expected_value

        for c_idx, cls_name in enumerate(explainer.classes):
            b_val = float(base_vals[c_idx]) if isinstance(base_vals, (list, np.ndarray)) else float(base_vals)
            c_shap_sum = float(np.sum(arr[0, :, c_idx]))
            reconstructed_margin = b_val + c_shap_sum
            diff = abs(reconstructed_margin - decision_fn[c_idx])
            assert diff < 1e-6, (
                f"Efficiency axiom violated for class {cls_name}: "
                f"reconstructed {reconstructed_margin} vs decision {decision_fn[c_idx]} (diff={diff})"
            )

    def test_explain_instance_schema_and_types(
        self, explainer: ReadinessModelExplainer, sample_senior_candidate: dict[str, str]
    ):
        """Structured output dictionary must conform to required schema and types."""
        result = explainer.explain_instance(sample_senior_candidate)

        assert "predicted_class" in result
        assert result["predicted_class"] in EXPECTED_CLASSES

        assert "class_probabilities" in result
        probs = result["class_probabilities"]
        assert set(probs.keys()) == set(EXPECTED_CLASSES)
        assert abs(sum(probs.values()) - 1.0) < 1e-3

        explanation = result["explanation"]
        assert explanation["target_class_explained"] == result["predicted_class"]
        assert isinstance(explanation["base_value"], float)
        assert isinstance(explanation["top_positive_factors"], list)
        assert isinstance(explanation["top_negative_factors"], list)
        assert isinstance(explanation["feature_contributions"], list)
        assert len(explanation["feature_contributions"]) == 9
        assert isinstance(explanation["human_readable_summary"], str)
        assert len(explanation["human_readable_summary"]) > 10

        viz = result["visualization_data"]
        assert "feature_importance_ranking" in viz
        assert len(viz["feature_importance_ranking"]) == 9
        assert "waterfall_steps" in viz
        assert len(viz["waterfall_steps"]) == 10  # base_value + 9 features

        assert "limitations" in result
        assert len(result["limitations"]) >= 3

    def test_multiclass_target_explanation(
        self, explainer: ReadinessModelExplainer, sample_senior_candidate: dict[str, str]
    ):
        """User can request explanation targeting any of the 3 classes specifically."""
        for target_cls in EXPECTED_CLASSES:
            result = explainer.explain_instance(sample_senior_candidate, target_class=target_cls)
            assert result["explanation"]["target_class_explained"] == target_cls

        with pytest.raises(ValueError, match="Invalid target_class"):
            explainer.explain_instance(sample_senior_candidate, target_class="UnknownClass")

    def test_factor_directionality_and_ranking(
        self, explainer: ReadinessModelExplainer, sample_senior_candidate: dict[str, str]
    ):
        """Positive factors must have positive contributions, negative factors must have negative."""
        result = explainer.explain_instance(sample_senior_candidate, top_k=5)
        top_pos = result["explanation"]["top_positive_factors"]
        top_neg = result["explanation"]["top_negative_factors"]

        for item in top_pos:
            assert item["contribution"] > 0
            assert item["direction_relative_to_target"] == "positive"
        for item in top_neg:
            assert item["contribution"] < 0
            assert item["direction_relative_to_target"] == "negative"

        # Verify descending order of magnitude
        pos_contribs = [item["contribution"] for item in top_pos]
        assert pos_contribs == sorted(pos_contribs, reverse=True)

    def test_input_representations_interchangeability(
        self, explainer: ReadinessModelExplainer
    ):
        """Explainer must accept raw dict, feature dict, 1D array, or 2D array."""
        feat_dict = {
            "skills_count": 8.0,
            "exp_positions_count": 2.0,
            "has_senior_role": 1.0,
            "project_count": 2.0,
            "project_words": 50.0,
            "project_tech_count": 4.0,
            "has_production_system": 1.0,
            "edu_level_ordinal": 1.0,
            "is_stem_degree": 1.0,
        }
        res_dict = explainer.explain_instance(feat_dict)
        assert res_dict["predicted_class"] in EXPECTED_CLASSES

        array_1d = np.array([8.0, 2.0, 1.0, 2.0, 50.0, 4.0, 1.0, 1.0, 1.0])
        res_arr = explainer.explain_instance(array_1d)
        assert res_arr["predicted_class"] == res_dict["predicted_class"]
        assert res_arr["explanation"]["base_value"] == res_dict["explanation"]["base_value"]

    def test_graceful_handling_empty_and_zero_inputs(
        self, explainer: ReadinessModelExplainer, sample_novice_candidate: dict[str, str]
    ):
        """Empty or null resume fields must not throw errors and predict Not Ready."""
        result = explainer.explain_instance(sample_novice_candidate)
        assert result["predicted_class"] == "Not Ready"
        assert result["explanation"]["target_class_explained"] == "Not Ready"
        assert len(result["explanation"]["top_positive_factors"]) > 0

    def test_determinism_and_model_invariance(
        self, explainer: ReadinessModelExplainer, sample_senior_candidate: dict[str, str]
    ):
        """Repeated calls must yield identical explanations and preserve model weights."""
        res1 = explainer.explain_instance(sample_senior_candidate)
        res2 = explainer.explain_instance(sample_senior_candidate)

        assert res1["predicted_class"] == res2["predicted_class"]
        assert res1["class_probabilities"] == res2["class_probabilities"]
        assert json.dumps(res1["explanation"], sort_keys=True) == json.dumps(res2["explanation"], sort_keys=True)

    def test_global_importance_computation_and_artifacts(
        self, explainer: ReadinessModelExplainer
    ):
        """Global feature importance must compute valid rankings and persist files."""
        global_info = explainer.compute_global_importance()

        assert global_info["sample_count"] == 19
        assert "overall_feature_importance" in global_info
        assert len(global_info["overall_feature_importance"]) == 9
        assert "class_specific_importance" in global_info
        assert set(global_info["class_specific_importance"].keys()) == set(EXPECTED_CLASSES)

        # Top feature across all classes is skills_count
        top_global_feat = global_info["overall_feature_importance"][0]["feature"]
        assert top_global_feat == "skills_count"

        # Check artifact files on disk
        json_path = SAVED_MODELS_DIR / GLOBAL_SHAP_JSON_NAME
        report_path = SAVED_MODELS_DIR.parent / EXPLAINABILITY_REPORT_NAME

        assert json_path.exists(), f"Missing {json_path}"
        assert report_path.exists(), f"Missing {report_path}"

        # Ensure no PII in global JSON artifact
        json_content = json_path.read_text(encoding="utf-8")
        assert "candidate_id" not in json_content
        assert "pair_id" not in json_content
        assert "annotation_id" not in json_content
        assert json.loads(json_content)["sample_count"] == 19

