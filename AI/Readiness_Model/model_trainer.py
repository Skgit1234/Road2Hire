"""Model Training and Persistence for Career Readiness Prediction (M4.4).

Builds scikit-learn Pipelines containing:
1. Feature Extraction (ReadinessFeatureExtractor)
2. Feature Scaling (StandardScaler)
3. Classifier (Dummy, LogisticRegression, RandomForest, XGBoost if available)

Persists model artifact and comprehensive metadata without candidate PII.
Prepares explainability interface for M4.5 SHAP integration.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .feature_extractor import ReadinessFeatureExtractor, get_feature_names

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAVED_MODELS_DIR = PROJECT_ROOT / "AI" / "Readiness_Model" / "saved_models"
MODEL_FILE_NAME = "readiness_classifier_pipeline.joblib"
METADATA_FILE_NAME = "model_metadata.json"

DEFAULT_RANDOM_STATE = 42
MODEL_VERSION = "0.1.0-exploratory"
DATASET_VERSION = "M4.3-pilot-N71"


def is_xgboost_available() -> bool:
    """Check whether xgboost is installed."""
    try:
        import xgboost  # noqa: F401
        return True
    except ImportError:
        return False


def build_readiness_pipeline(
    model_type: str = "logistic_regression",
    random_state: int = DEFAULT_RANDOM_STATE,
) -> Pipeline:
    """Build a scikit-learn Pipeline encapsulating feature extraction, scaling, and classification."""
    model_lower = model_type.lower().strip()

    if model_lower == "dummy":
        clf = DummyClassifier(strategy="stratified", random_state=random_state)
    elif model_lower == "dummy_most_frequent":
        clf = DummyClassifier(strategy="most_frequent")
    elif model_lower == "logistic_regression":
        clf = LogisticRegression(
            class_weight="balanced",
            solver="lbfgs",
            C=0.5,
            max_iter=1000,
            random_state=random_state,
        )
    elif model_lower == "random_forest":
        clf = RandomForestClassifier(
            n_estimators=50,
            max_depth=3,
            min_samples_split=4,
            min_samples_leaf=2,
            class_weight="balanced_subsample",
            random_state=random_state,
        )
    elif model_lower == "xgboost":
        if not is_xgboost_available():
            raise ImportError(
                "XGBoost dependency is not installed. Use 'logistic_regression' "
                "or 'random_forest' instead."
            )
        import xgboost as xgb
        clf = xgb.XGBClassifier(
            max_depth=2,
            learning_rate=0.03,
            n_estimators=35,
            subsample=0.7,
            colsample_bytree=0.7,
            reg_lambda=3.0,
            random_state=random_state,
            eval_metric="mlogloss",
        )
    else:
        raise ValueError(
            f"Unsupported model_type: '{model_type}'. Expected one of: "
            "['dummy', 'dummy_most_frequent', 'logistic_regression', 'random_forest', 'xgboost']"
        )

    pipeline = Pipeline([
        ("extractor", ReadinessFeatureExtractor()),
        ("scaler", StandardScaler()),
        ("classifier", clf),
    ])

    return pipeline


def train_and_persist_model(
    X_raw: list[dict[str, str]],
    y: np.ndarray,
    model_type: str = "logistic_regression",
    evaluation_metrics: dict[str, Any] | None = None,
    output_dir: Path | str = SAVED_MODELS_DIR,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> tuple[Path, Path]:
    """Train pipeline on full labeled pool and serialize model artifact and metadata."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    pipeline = build_readiness_pipeline(model_type=model_type, random_state=random_state)
    pipeline.fit(X_raw, y)

    # File paths
    model_path = out_dir / MODEL_FILE_NAME
    metadata_path = out_dir / METADATA_FILE_NAME

    # Persist pipeline artifact
    joblib.dump(pipeline, model_path)

    # Build sanitized metadata without candidate PII
    classes_list = [str(c) for c in pipeline.classes_]
    metadata = {
        "model_name": f"Road2Hire Career Readiness Classifier ({model_type})",
        "model_type": model_type,
        "model_version": MODEL_VERSION,
        "dataset_version": DATASET_VERSION,
        "training_sample_count": len(y),
        "target_classes": classes_list,
        "class_distribution": {
            cls_name: int(np.sum(y == cls_name)) for cls_name in classes_list
        },
        "feature_names": get_feature_names(),
        "random_seed": random_state,
        "trained_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "cross_validation_metrics": evaluation_metrics or {},
        "known_limitations": [
            "Trained on M4.3 pilot dataset (N=71 labeled records).",
            "Severe minority class imbalance in Not Ready (N=3, 4.2%).",
            "Occupational concentration in Software Developer (60.6%).",
            "Exploratory baseline only; not certified for autonomous production decisions.",
        ],
    }

    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return model_path, metadata_path


def load_persisted_model(
    model_path: Path | str = SAVED_MODELS_DIR / MODEL_FILE_NAME,
) -> tuple[Pipeline, dict[str, Any]]:
    """Load the persisted model pipeline and associated metadata."""
    m_path = Path(model_path)
    meta_path = m_path.parent / METADATA_FILE_NAME

    if not m_path.exists():
        raise FileNotFoundError(f"Persisted model not found at {m_path}")
    if not meta_path.exists():
        raise FileNotFoundError(f"Model metadata not found at {meta_path}")

    pipeline = joblib.load(m_path)
    metadata = json.loads(meta_path.read_text(encoding="utf-8"))

    return pipeline, metadata


def get_model_for_explainability(pipeline: Pipeline) -> dict[str, Any]:
    """Expose clean explainability interface for upcoming M4.5 SHAP analysis.

    Returns:
        dict containing:
        - 'classifier': fitted underlying classifier step.
        - 'scaler': fitted standard scaler step.
        - 'feature_names': list of engineered feature names.
    """
    if "classifier" not in pipeline.named_steps:
        raise ValueError("Pipeline missing 'classifier' step.")
    if "scaler" not in pipeline.named_steps:
        raise ValueError("Pipeline missing 'scaler' step.")

    return {
        "classifier": pipeline.named_steps["classifier"],
        "scaler": pipeline.named_steps["scaler"],
        "feature_names": get_feature_names(),
    }
