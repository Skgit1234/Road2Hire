"""Tests for Career Readiness Model Reliability, OOD Detection & Metadata (Phase 2).

Validates:
1. Training and inference feature consistency and schema adherence.
2. Out-of-Distribution (OOD) detection for in-range and out-of-range candidates.
3. Non-destructive feature handling (zero clipping or prediction mutation).
4. Readiness prediction output structure (OOD warnings, class probabilities, metadata).
5. SHAP explainability consistency with the persisted model.
6. Model metadata completeness and JSON serializability.
7. Missing model artifact error handling.
8. Data leakage prevention and unlabeled record exclusion.
"""

from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pytest

from AI.Pipeline.pipeline import Road2HirePipeline
from AI.Pipeline.pipeline_schema import ReadinessPredictionData
from AI.Readiness_Model.dataset_loader import load_readiness_dataset
from AI.Readiness_Model.feature_extractor import ReadinessFeatureExtractor, get_feature_names
from AI.Readiness_Model.model_trainer import (
    SAVED_MODELS_DIR,
    load_persisted_model,
)
from AI.Readiness_Model.ood_detector import (
    ReadinessOODDetector,
    get_default_ood_detector,
)
from AI.Readiness_Model.shap_explainer import ReadinessModelExplainer


# ---------------------------------------------------------------------------
# 1. Feature Consistency: Training vs. Inference
# ---------------------------------------------------------------------------

def test_feature_consistency_training_vs_inference():
    extractor = ReadinessFeatureExtractor()
    feature_names = get_feature_names()
    assert len(feature_names) == 9

    # Training format
    sample_training_evidence = {
        "skills_text": "Python, SQL, Machine Learning",
        "experience_text": "Software Engineer at Tech Corp",
        "projects_text": "Built Recommendation Engine (Tech: Python, Pandas, Scikit-Learn)",
        "education_text": "Bachelor of Technology in Computer Science",
    }
    feat_train = extractor.transform([sample_training_evidence])[0]
    assert len(feat_train) == 9
    assert feat_train[0] == 3.0   # skills_count
    assert feat_train[1] == 1.0   # exp_positions_count
    assert feat_train[7] == 1.0   # edu_level_ordinal (Bachelor)
    assert feat_train[8] == 1.0   # is_stem_degree

    # Inference format via pipeline evidence extractor
    mock_resume_result = {
        "candidate_profile": {
            "skills": [
                {"skill": "Python"},
                {"skill": "SQL"},
                {"skill": "Machine Learning"},
            ],
            "experience": [
                {
                    "job_title": "Software Engineer",
                    "organization": "Tech Corp",
                    "skills_used": ["Python", "SQL"],
                }
            ],
            "projects": [
                {
                    "project_name": "Recommendation Engine",
                    "technologies": ["Python", "Pandas", "Scikit-Learn"],
                    "description": "Built recommendation engine",
                }
            ],
            "education": [
                {
                    "degree": "Bachelor of Technology",
                    "field_of_study": "Computer Science",
                    "institution": "University",
                }
            ],
        },
        "sections": {},
    }

    pipeline = Road2HirePipeline()
    extracted_ev = pipeline._extract_evidence_dict(mock_resume_result)
    feat_infer = extractor.transform([extracted_ev])[0]

    assert len(feat_infer) == 9
    assert feat_infer[0] == 3.0   # skills_count matches exactly
    assert feat_infer[1] == 1.0   # exp_positions_count matches
    assert feat_infer[7] == 1.0   # edu_level_ordinal matches
    assert feat_infer[8] == 1.0   # is_stem_degree matches


# ---------------------------------------------------------------------------
# 2. Out-of-Distribution (OOD) Detection
# ---------------------------------------------------------------------------

def test_ood_detector_in_range_candidate():
    detector = get_default_ood_detector()
    typical_features = {
        "skills_count": 6.0,
        "exp_positions_count": 1.0,
        "has_senior_role": 0.0,
        "project_count": 2.0,
        "project_words": 30.0,
        "project_tech_count": 4.0,
        "has_production_system": 0.0,
        "edu_level_ordinal": 1.0,
        "is_stem_degree": 1.0,
    }
    result = detector.detect(typical_features)
    assert result.is_ood is False
    assert len(result.ood_warnings) == 0
    assert len(result.range_violations) == 0
    assert len(result.statistical_outliers) == 0


def test_ood_detector_out_of_range_and_statistical_outlier():
    detector = get_default_ood_detector()
    # Extreme skills count (25 > training max 14) and exp positions (6 > max 3)
    extreme_features = {
        "skills_count": 25.0,
        "exp_positions_count": 6.0,
        "has_senior_role": 1.0,
        "project_count": 5.0,
        "project_words": 150.0,
        "project_tech_count": 20.0,
        "has_production_system": 1.0,
        "edu_level_ordinal": 2.0,
        "is_stem_degree": 1.0,
    }
    result = detector.detect(extreme_features)
    assert result.is_ood is True
    assert len(result.ood_warnings) > 0

    # Verify specific feature diagnosis
    diag = result.feature_diagnostics
    assert diag["skills_count"]["is_range_violation"] is True
    assert diag["skills_count"]["range_violation_direction"] == "above_max"
    assert diag["exp_positions_count"]["is_range_violation"] is True


def test_ood_detector_below_minimum_education():
    detector = get_default_ood_detector()
    # Training set had no candidates with edu_level_ordinal == 0.0 (min was 1.0)
    low_edu_features = {
        "skills_count": 5.0,
        "exp_positions_count": 1.0,
        "has_senior_role": 0.0,
        "project_count": 1.0,
        "project_words": 20.0,
        "project_tech_count": 2.0,
        "has_production_system": 0.0,
        "edu_level_ordinal": 0.0,  # Below min
        "is_stem_degree": 0.0,
    }
    result = detector.detect(low_edu_features)
    assert result.is_ood is True
    assert any("edu_level_ordinal" in w for w in result.ood_warnings)
    assert result.feature_diagnostics["edu_level_ordinal"]["range_violation_direction"] == "below_min"


def test_ood_detector_non_destructive():
    detector = get_default_ood_detector()
    original_dict = {"skills_count": 20.0, "exp_positions_count": 5.0}
    copied_dict = dict(original_dict)
    detector.detect(original_dict)
    # Original dictionary must not be mutated or clipped
    assert original_dict == copied_dict


# ---------------------------------------------------------------------------
# 3. Model Metadata and Training Statistics
# ---------------------------------------------------------------------------

def test_model_metadata_contains_distribution_statistics():
    _, meta = load_persisted_model()
    assert "training_feature_statistics" in meta
    stats = meta["training_feature_statistics"]

    for feat in get_feature_names():
        assert feat in stats
        f_stat = stats[feat]
        assert "min" in f_stat
        assert "max" in f_stat
        assert "mean" in f_stat
        assert "std" in f_stat
        assert f_stat["min"] <= f_stat["max"]

    assert meta["training_sample_count"] == 71
    assert "known_limitations" in meta
    assert len(meta["known_limitations"]) >= 4


# ---------------------------------------------------------------------------
# 4. Readiness Prediction Output Structure & JSON Serialization
# ---------------------------------------------------------------------------

def test_readiness_prediction_data_schema():
    pred_data = ReadinessPredictionData(
        predicted_class="Developing",
        class_probabilities={"Developing": 0.75, "Job Ready": 0.20, "Not Ready": 0.05},
        model_version="0.1.0-exploratory",
        model_type="LogisticRegression",
        feature_values={"skills_count": 6.0},
        is_experimental=True,
        is_ood=True,
        ood_warnings=["Feature 'skills_count' exceeds training maximum."],
        training_sample_count=71,
        training_class_distribution={"Developing": 52, "Job Ready": 16, "Not Ready": 3},
        limitations=["Exploratory baseline only."],
    )
    d = pred_data.to_dict()
    assert d["is_ood"] is True
    assert len(d["ood_warnings"]) == 1
    assert d["training_sample_count"] == 71

    # Must be natively JSON serializable
    serialized = json.dumps(d)
    assert isinstance(serialized, str)
    deserialized = json.loads(serialized)
    assert deserialized["predicted_class"] == "Developing"


# ---------------------------------------------------------------------------
# 5. SHAP Consistency with Persisted Model
# ---------------------------------------------------------------------------

def test_shap_explainer_consistency():
    explainer = ReadinessModelExplainer()
    evidence = {
        "skills_text": "Python, SQL, Docker",
        "experience_text": "Data Engineer at Startup",
        "projects_text": "ETL Pipeline (Tech: Python, SQL)",
        "education_text": "B.Tech in Computer Science",
    }
    res = explainer.explain_instance(evidence, target_class="Developing", top_k=3)
    exp = res["explanation"]
    assert exp["target_class_explained"] == "Developing"
    assert "top_positive_factors" in exp
    assert "top_negative_factors" in exp
    assert "feature_contributions" in exp
    assert len(exp["feature_contributions"]) == 9

    # Verify all feature names exist in canonical list
    canonical_names = set(get_feature_names())
    for item in exp["feature_contributions"]:
        assert item["feature"] in canonical_names


# ---------------------------------------------------------------------------
# 6. Missing Artifacts Error Handling
# ---------------------------------------------------------------------------

def test_missing_persisted_model_raises_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_persisted_model(SAVED_MODELS_DIR / "nonexistent_model.joblib")


# ---------------------------------------------------------------------------
# 7. Dataset Leakage & Unlabeled Exclusion
# ---------------------------------------------------------------------------

def test_dataset_unlabeled_exclusion_and_unique_profiles():
    ds = load_readiness_dataset()
    assert len(ds.records) == 71
    assert ds.unlabeled_count == 29
    assert len(ds.raw_evidence) == 71

    # Verify zero identical evidence profiles in labeled set
    seen = set()
    for rec in ds.records:
        key = (rec.skills_text, rec.experience_text, rec.projects_text, rec.education_text)
        assert key not in seen, f"Duplicate evidence profile found at row {rec.row_index}"
        seen.add(key)

