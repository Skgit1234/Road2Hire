"""Unit and Integration Tests for Career Readiness Model Training & Evaluation (M4.4).

Validates:
- Workbook loading and label filtering (71 labeled, 29 unlabeled excluded)
- Exclusion of candidate IDs, annotation IDs, pair IDs, and personal information
- Prevention of human rubric sub-rating leakage (Cols 9-12 excluded)
- Deterministic feature extraction and handling of missing evidence
- Pipeline construction for Dummy, LogisticRegression, and RandomForest
- Repeated Stratified 3-Fold Cross-Validation evaluation and metric calculations
- Model serialization, metadata integrity, and clean loading
- Explainability preparation interface for M4.5 SHAP integration
"""

from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pytest
from sklearn.pipeline import Pipeline

from AI.Readiness_Model.dataset_loader import (
    DEFAULT_XLSX_PATH,
    ReadinessDataset,
    load_readiness_dataset,
)
from AI.Readiness_Model.feature_extractor import (
    ReadinessFeatureExtractor,
    get_feature_names,
)
from AI.Readiness_Model.model_evaluator import (
    ModelEvaluationResult,
    evaluate_all_models,
    evaluate_single_model,
)
from AI.Readiness_Model.model_trainer import (
    build_readiness_pipeline,
    get_model_for_explainability,
    load_persisted_model,
    train_and_persist_model,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class TestReadinessModelTrainingSuite:
    """Comprehensive test suite for M4.4 career readiness ML pipeline."""

    @pytest.fixture(scope="module")
    def dataset(self) -> ReadinessDataset:
        assert DEFAULT_XLSX_PATH.exists(), f"Spreadsheet not found at {DEFAULT_XLSX_PATH}"
        return load_readiness_dataset()

    def test_workbook_loading_and_filtering(self, dataset: ReadinessDataset):
        assert dataset.total_rows_inspected == 100
        assert len(dataset.records) == 71
        assert dataset.unlabeled_count == 29
        assert len(dataset.raw_evidence) == 71
        assert len(dataset.y) == 71

        # Check unique labels
        unique_labels = set(dataset.y)
        assert unique_labels == {"Developing", "Job Ready", "Not Ready"}

    def test_unlabeled_records_strictly_excluded(self, dataset: ReadinessDataset):
        for rec in dataset.records:
            assert rec.readiness_label is not None
            assert rec.readiness_label in {"Developing", "Job Ready", "Not Ready"}
            assert rec.readiness_label != ""

    def test_pii_and_identifier_exclusion(self, dataset: ReadinessDataset):
        for raw in dataset.raw_evidence:
            # Must only contain the permitted raw evidence keys
            assert set(raw.keys()) == {
                "target_occupation_title",
                "skills_text",
                "experience_text",
                "projects_text",
                "education_text",
            }
            # No identifier keys
            assert "candidate_id" not in raw
            assert "annotation_id" not in raw
            assert "pair_id" not in raw
            assert "email" not in raw
            assert "phone" not in raw

    def test_annotation_subrating_leakage_prevention(self, dataset: ReadinessDataset):
        for raw in dataset.raw_evidence:
            assert "essential_skill_proficiency" not in raw
            assert "work_experience_relevance" not in raw
            assert "practical_application_evidence" not in raw
            assert "education_relevance" not in raw
            assert "key_evidence_summary" not in raw
            assert "annotation_notes" not in raw

    def test_feature_extraction_shape_and_names(self, dataset: ReadinessDataset):
        extractor = ReadinessFeatureExtractor()
        X = extractor.fit_transform(dataset.raw_evidence)

        assert isinstance(X, np.ndarray)
        assert X.shape == (71, 9)
        assert not np.isnan(X).any(), "Feature matrix contains NaN values"

        expected_names = [
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
        assert get_feature_names() == expected_names
        assert extractor.get_feature_names_out() == expected_names

    def test_missing_values_handling(self):
        extractor = ReadinessFeatureExtractor()
        empty_record = [{
            "target_occupation_title": "software developer",
            "skills_text": "",
            "experience_text": "",
            "projects_text": "",
            "education_text": "",
        }]
        X_empty = extractor.transform(empty_record)
        assert X_empty.shape == (1, 9)
        assert not np.isnan(X_empty).any()
        # All extracted features should be zero for completely empty input
        assert np.all(X_empty == 0.0)

    def test_feature_extraction_reproducibility(self, dataset: ReadinessDataset):
        extractor1 = ReadinessFeatureExtractor()
        extractor2 = ReadinessFeatureExtractor()

        X1 = extractor1.fit_transform(dataset.raw_evidence)
        X2 = extractor2.fit_transform(dataset.raw_evidence)

        np.testing.assert_array_equal(X1, X2)

    def test_pipeline_construction(self):
        for m_type in ["dummy", "dummy_most_frequent", "logistic_regression", "random_forest"]:
            pipeline = build_readiness_pipeline(model_type=m_type)
            assert isinstance(pipeline, Pipeline)
            assert "extractor" in pipeline.named_steps
            assert "scaler" in pipeline.named_steps
            assert "classifier" in pipeline.named_steps

    def test_cross_validation_evaluation(self, dataset: ReadinessDataset):
        res = evaluate_single_model(
            model_type="logistic_regression",
            X_raw=dataset.raw_evidence,
            y=dataset.y,
            random_state=42,
            n_splits=3,
            n_repeats=2,  # Quick test run: 6 iterations
        )

        assert isinstance(res, ModelEvaluationResult)
        assert res.model_name == "logistic_regression"
        assert res.total_evaluations == 6
        assert 0.0 <= res.macro_f1_mean <= 1.0
        assert 0.0 <= res.balanced_accuracy_mean <= 1.0
        assert set(res.per_class_metrics.keys()) == {"Developing", "Job Ready", "Not Ready"}
        assert len(res.cumulative_confusion_matrix) == 3

    def test_model_serialization_and_loading(self, dataset: ReadinessDataset, tmp_path: Path):
        model_path, meta_path = train_and_persist_model(
            X_raw=dataset.raw_evidence,
            y=dataset.y,
            model_type="logistic_regression",
            evaluation_metrics={"test_metric": 0.85},
            output_dir=tmp_path,
            random_state=42,
        )

        assert model_path.exists()
        assert meta_path.exists()

        # Reload
        pipeline, metadata = load_persisted_model(model_path=model_path)
        assert isinstance(pipeline, Pipeline)
        assert metadata["model_type"] == "logistic_regression"
        assert metadata["training_sample_count"] == 71
        assert metadata["target_classes"] == ["Developing", "Job Ready", "Not Ready"]

        # Ensure prediction matches
        preds = pipeline.predict(dataset.raw_evidence[:5])
        assert len(preds) == 5
        assert all(p in {"Developing", "Job Ready", "Not Ready"} for p in preds)

    def test_metadata_excludes_personal_information(self, tmp_path: Path, dataset: ReadinessDataset):
        _, meta_path = train_and_persist_model(
            X_raw=dataset.raw_evidence,
            y=dataset.y,
            model_type="logistic_regression",
            output_dir=tmp_path,
        )
        meta_text = meta_path.read_text(encoding="utf-8")

        # Must not contain candidate references or individual profile texts
        assert "mr_1" not in meta_text
        assert "candidate_id" not in meta_text
        assert "annotation_id" not in meta_text
        assert "Honeywell" not in meta_text
        assert "Savitribai" not in meta_text

    def test_explainability_interface_ready_for_m4_5(self):
        pipeline = build_readiness_pipeline("logistic_regression")
        pipeline.fit([
            {
                "target_occupation_title": "dev",
                "skills_text": "Python",
                "experience_text": "Dev",
                "projects_text": "Proj",
                "education_text": "BE",
            },
            {
                "target_occupation_title": "dev",
                "skills_text": "Java",
                "experience_text": "Dev",
                "projects_text": "Proj",
                "education_text": "BE",
            },
            {
                "target_occupation_title": "dev",
                "skills_text": "",
                "experience_text": "None",
                "projects_text": "",
                "education_text": "BA",
            },
        ], np.array(["Developing", "Job Ready", "Not Ready"]))

        exp_dict = get_model_for_explainability(pipeline)
        assert "classifier" in exp_dict
        assert "scaler" in exp_dict
        assert "feature_names" in exp_dict
        assert len(exp_dict["feature_names"]) == 9

