"""Career Readiness Model Package (M4.4 & M4.5).

Supervised machine learning pipeline and SHAP explainability for candidate career readiness prediction.
Classes: ['Developing', 'Job Ready', 'Not Ready']
"""

from __future__ import annotations

from .dataset_loader import load_readiness_dataset
from .feature_extractor import ReadinessFeatureExtractor, get_feature_names
from .model_trainer import build_readiness_pipeline, train_and_persist_model
from .model_evaluator import evaluate_all_models
from .ood_detector import (
    OODDetectionResult,
    ReadinessOODDetector,
    get_default_ood_detector,
)
from .shap_explainer import ReadinessModelExplainer

__all__ = [
    "load_readiness_dataset",
    "ReadinessFeatureExtractor",
    "get_feature_names",
    "build_readiness_pipeline",
    "train_and_persist_model",
    "evaluate_all_models",
    "ReadinessOODDetector",
    "OODDetectionResult",
    "get_default_ood_detector",
    "ReadinessModelExplainer",
]
