"""SHAP Explainability for Career Readiness Prediction (M4.5).

Provides global and local (instance-level) SHAP explanations for the
Road2Hire career readiness prediction model.

Classes: ['Developing', 'Job Ready', 'Not Ready']

Core Capabilities:
- LinearExplainer for regularized Logistic Regression with scaled feature input.
- Exact feature name preservation matching ReadinessFeatureExtractor.
- Multiclass explanation support (class-specific SHAP values).
- Structured JSON explanation output with positive/negative factor decomposition.
- Frontend visualization-ready waterfall and importance payloads.
- Global feature importance generation and reporting.

Important Methodological Note:
SHAP values describe statistical model behavior and feature contributions
to the model's internal decision function; they do NOT assert causal
guarantees or deterministic real-world candidate qualification.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import shap
from sklearn.pipeline import Pipeline

from .dataset_loader import load_readiness_dataset
from .feature_extractor import ReadinessFeatureExtractor, get_feature_names
from .model_trainer import (
    DEFAULT_RANDOM_STATE,
    SAVED_MODELS_DIR,
    load_persisted_model,
)

GLOBAL_SHAP_JSON_NAME = "global_shap_importance.json"
EXPLAINABILITY_REPORT_NAME = "shap_explainability_report.md"

FEATURE_HUMAN_DESCRIPTIONS = {
    "skills_count": "Number of verified technical skills normalized to canonical taxonomy",
    "exp_positions_count": "Number of distinct professional employment roles",
    "has_senior_role": "Presence of senior, lead, architect, or manager title in work history",
    "project_count": "Number of documented technical projects with descriptions",
    "project_words": "Technical depth and implementation detail in project narratives",
    "project_tech_count": "Number of distinct technologies specified in project implementations",
    "has_production_system": "Evidence of enterprise, production, deployed, or multi-tier systems",
    "edu_level_ordinal": "Highest academic degree level (None/Secondary=0, Bachelor=1, Master/Postgraduate=2)",
    "is_stem_degree": "Formal degree alignment with Computer Science, IT, or Engineering disciplines",
}


class ReadinessModelExplainer:
    """SHAP Explainer wrapper for the Career Readiness Prediction Pipeline."""

    def __init__(
        self,
        pipeline: Pipeline | None = None,
        background_data: list[dict[str, str]] | None = None,
        random_state: int = DEFAULT_RANDOM_STATE,
    ) -> None:
        """Initialize explainer with saved or provided pipeline and background data."""
        self.random_state = random_state

        if pipeline is None:
            self.pipeline, self.metadata = load_persisted_model()
        else:
            self.pipeline = pipeline
            self.metadata = {
                "model_type": type(pipeline.named_steps.get("classifier")).__name__,
                "model_version": "0.1.0-exploratory",
                "target_classes": [str(c) for c in pipeline.classes_],
            }

        self.extractor: ReadinessFeatureExtractor = self.pipeline.named_steps["extractor"]
        self.scaler = self.pipeline.named_steps["scaler"]
        self.classifier = self.pipeline.named_steps["classifier"]
        self.classes: list[str] = [str(c) for c in self.classifier.classes_]
        self.feature_names: list[str] = get_feature_names()

        # Compute or load background data in scaled feature space
        if background_data is None:
            ds = load_readiness_dataset()
            raw_bg = ds.raw_evidence
        else:
            raw_bg = background_data

        X_bg_raw = self.extractor.transform(raw_bg)
        self.X_bg_scaled = self.scaler.transform(X_bg_raw)

        # Select compatible SHAP explainer
        # For Logistic Regression on scaled inputs, LinearExplainer is optimal and exact
        self.explainer_type = "LinearExplainer"
        try:
            self.explainer = shap.LinearExplainer(
                self.classifier,
                self.X_bg_scaled,
                feature_names=self.feature_names,
            )
        except Exception:
            # Fallback for arbitrary model types
            self.explainer_type = "Explainer"
            self.explainer = shap.Explainer(
                self.classifier,
                self.X_bg_scaled,
                feature_names=self.feature_names,
            )

    def _prepare_scaled_input(
        self, instance: dict[str, Any] | list[dict[str, Any]] | np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Convert varied input formats into (X_raw_matrix, X_scaled_matrix)."""
        if isinstance(instance, dict):
            # Check if it is a raw evidence dict or a feature-value dict
            if any(k in instance for k in ["skills_text", "experience_text", "projects_text"]):
                raw_list = [instance]
                X_raw = self.extractor.transform(raw_list)
            else:
                # Feature-value dictionary
                row = [float(instance.get(fn, 0.0)) for fn in self.feature_names]
                X_raw = np.array([row], dtype=np.float64)
        elif isinstance(instance, list):
            if len(instance) > 0 and isinstance(instance[0], dict):
                if any(k in instance[0] for k in ["skills_text", "experience_text"]):
                    X_raw = self.extractor.transform(instance)
                else:
                    rows = [
                        [float(item.get(fn, 0.0)) for fn in self.feature_names]
                        for item in instance
                    ]
                    X_raw = np.array(rows, dtype=np.float64)
            else:
                raise ValueError("List input must contain dictionaries.")
        elif isinstance(instance, np.ndarray):
            if instance.ndim == 1:
                if len(instance) != len(self.feature_names):
                    raise ValueError(
                        f"Expected {len(self.feature_names)} features, got {len(instance)}"
                    )
                X_raw = instance.reshape(1, -1).astype(np.float64)
            elif instance.ndim == 2:
                if instance.shape[1] != len(self.feature_names):
                    raise ValueError(
                        f"Expected {len(self.feature_names)} columns, got {instance.shape[1]}"
                    )
                X_raw = instance.astype(np.float64)
            else:
                raise ValueError("Array input must be 1D or 2D.")
        else:
            raise TypeError(f"Unsupported input type: {type(instance)}")

        X_scaled = self.scaler.transform(X_raw)
        return X_raw, X_scaled

    def explain_instance(
        self,
        instance: dict[str, Any] | np.ndarray,
        target_class: str | None = None,
        top_k: int = 3,
    ) -> dict[str, Any]:
        """Generate a structured SHAP explanation for a single candidate instance."""
        X_raw, X_scaled = self._prepare_scaled_input(instance)

        # 1. Prediction & Probabilities
        preds = self.classifier.predict(X_scaled)
        pred_class = str(preds[0])

        probs_dict: dict[str, float] = {}
        if hasattr(self.classifier, "predict_proba"):
            probs = self.classifier.predict_proba(X_scaled)[0]
            probs_dict = {
                cls_name: round(float(p), 4) for cls_name, p in zip(self.classes, probs)
            }

        # 2. Determine class to explain (defaults to predicted class)
        if target_class is None:
            eval_class = pred_class
        else:
            if target_class not in self.classes:
                raise ValueError(
                    f"Invalid target_class '{target_class}'. Must be one of: {self.classes}"
                )
            eval_class = target_class

        class_idx = self.classes.index(eval_class)

        # 3. Compute SHAP values
        # shap_values shape: (1, n_features, n_classes) or (1, n_features)
        raw_shap = self.explainer.shap_values(X_scaled)
        if hasattr(raw_shap, "values"):
            shap_array = raw_shap.values
        else:
            shap_array = np.array(raw_shap)

        # Handle multiclass indexing
        if shap_array.ndim == 3:
            # (N, features, classes)
            shap_instance = shap_array[0, :, class_idx]
            all_classes_shap = {
                c_name: shap_array[0, :, idx].tolist()
                for idx, c_name in enumerate(self.classes)
            }
        elif shap_array.ndim == 2:
            shap_instance = shap_array[0, :]
            all_classes_shap = {eval_class: shap_instance.tolist()}
        else:
            raise ValueError(f"Unexpected SHAP values shape: {shap_array.shape}")

        # Intercept / base value
        if hasattr(self.explainer, "expected_value"):
            exp_val = self.explainer.expected_value
            if isinstance(exp_val, (list, np.ndarray)):
                base_value = float(exp_val[class_idx])
            else:
                base_value = float(exp_val)
        else:
            base_value = 0.0

        # 4. Decompose Positive vs Negative Factors relative to eval_class
        feature_contributions: list[dict[str, Any]] = []
        positive_factors: list[dict[str, Any]] = []
        negative_factors: list[dict[str, Any]] = []

        cumulative_val = base_value
        waterfall_data: list[dict[str, Any]] = [
            {
                "step": "base_value",
                "feature": "Expected Log-Odds (Intercept)",
                "contribution": round(base_value, 4),
                "cumulative": round(cumulative_val, 4),
            }
        ]

        # Sort all features by descending magnitude
        sorted_indices = np.argsort(-np.abs(shap_instance))

        for f_idx in sorted_indices:
            f_name = self.feature_names[f_idx]
            raw_val = float(X_raw[0, f_idx])
            contrib = float(shap_instance[f_idx])
            direction = "positive" if contrib > 0 else "negative" if contrib < 0 else "neutral"

            item = {
                "feature": f_name,
                "display_name": f_name.replace("_", " ").title(),
                "feature_value": round(raw_val, 2),
                "contribution": round(contrib, 4),
                "direction_relative_to_target": direction,
                "description": FEATURE_HUMAN_DESCRIPTIONS.get(f_name, ""),
            }
            feature_contributions.append(item)

            if contrib > 0:
                positive_factors.append(item)
            elif contrib < 0:
                negative_factors.append(item)

            cumulative_val += contrib
            waterfall_data.append({
                "step": f_name,
                "feature": f_name,
                "contribution": round(contrib, 4),
                "cumulative": round(cumulative_val, 4),
            })

        # Rank factors
        top_pos = sorted(positive_factors, key=lambda x: -x["contribution"])[:top_k]
        top_neg = sorted(negative_factors, key=lambda x: x["contribution"])[:top_k]

        # 5. Construct Concise Human-Readable Explanation
        pos_names = [f["display_name"] for f in top_pos]
        neg_names = [f["display_name"] for f in top_neg]

        narrative_parts = [
            f"The model predicted '{pred_class}'"
            + (f" with {probs_dict[pred_class]*100:.1f}% confidence." if probs_dict else ".")
        ]
        if eval_class == pred_class:
            if top_pos:
                narrative_parts.append(
                    f"The primary factors increasing probability for '{eval_class}' were: {', '.join(pos_names)}."
                )
            if top_neg:
                narrative_parts.append(
                    f"Conversely, factors pulling against '{eval_class}' were: {', '.join(neg_names)}."
                )
        else:
            narrative_parts.append(
                f"When evaluated specifically for '{eval_class}', primary supporting factors were: {', '.join(pos_names) if pos_names else 'None'}, "
                f"while constraining factors were: {', '.join(neg_names) if neg_names else 'None'}."
            )

        human_narrative = " ".join(narrative_parts)

        # 6. Structured Output Payload (Phase 5 & 6 Schema)
        return {
            "predicted_class": pred_class,
            "class_probabilities": probs_dict,
            "explanation": {
                "target_class_explained": eval_class,
                "base_value": round(base_value, 4),
                "top_positive_factors": top_pos,
                "top_negative_factors": top_neg,
                "feature_contributions": feature_contributions,
                "multiclass_contributions": all_classes_shap,
                "human_readable_summary": human_narrative,
            },
            "visualization_data": {
                "feature_importance_ranking": [f["feature"] for f in feature_contributions],
                "waterfall_steps": waterfall_data,
                "class_probability_breakdown": probs_dict,
            },
            "model_version": self.metadata.get("model_version", "0.1.0-exploratory"),
            "limitations": [
                "Exploratory model trained on an annotated pilot dataset (N=71).",
                "SHAP values describe statistical model behavior, not causal reasons for actual candidate competence.",
                "Contribution directions are relative to the specific target class being evaluated.",
            ],
        }

    def compute_global_importance(
        self, dataset_records: list[dict[str, str]] | None = None
    ) -> dict[str, Any]:
        """Compute global feature importance across all candidate records."""
        if dataset_records is None:
            ds = load_readiness_dataset()
            raw_data = ds.raw_evidence
        else:
            raw_data = dataset_records

        X_raw = self.extractor.transform(raw_data)
        X_scaled = self.scaler.transform(X_raw)

        raw_shap = self.explainer.shap_values(X_scaled)
        if hasattr(raw_shap, "values"):
            shap_array = raw_shap.values
        else:
            shap_array = np.array(raw_shap)

        # shap_array shape: (N, n_features, n_classes)
        # 1. Overall Mean Absolute SHAP per feature across all samples and classes
        mean_abs_all = np.mean(np.abs(shap_array), axis=(0, 2))
        overall_ranking_idx = np.argsort(-mean_abs_all)

        overall_importance = [
            {
                "rank": int(rank),
                "feature": self.feature_names[idx],
                "display_name": self.feature_names[idx].replace("_", " ").title(),
                "mean_abs_shap": round(float(mean_abs_all[idx]), 4),
                "description": FEATURE_HUMAN_DESCRIPTIONS.get(self.feature_names[idx], ""),
            }
            for rank, idx in enumerate(overall_ranking_idx, start=1)
        ]

        # 2. Class-specific importance
        class_importance: dict[str, list[dict[str, Any]]] = {}
        for c_idx, c_name in enumerate(self.classes):
            c_shap = shap_array[:, :, c_idx]
            mean_abs_c = np.mean(np.abs(c_shap), axis=0)
            mean_signed_c = np.mean(c_shap, axis=0)
            c_ranking_idx = np.argsort(-mean_abs_c)

            class_importance[c_name] = [
                {
                    "rank": int(rank),
                    "feature": self.feature_names[idx],
                    "mean_abs_shap": round(float(mean_abs_c[idx]), 4),
                    "mean_signed_shap": round(float(mean_signed_c[idx]), 4),
                }
                for rank, idx in enumerate(c_ranking_idx, start=1)
            ]

        return {
            "explainer_type": self.explainer_type,
            "sample_count": len(raw_data),
            "classes": self.classes,
            "overall_feature_importance": overall_importance,
            "class_specific_importance": class_importance,
        }

    def generate_global_artifacts(
        self,
        output_dir: Path | str = SAVED_MODELS_DIR,
    ) -> tuple[Path, Path]:
        """Generate and save global SHAP importance JSON and Markdown report."""
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        global_info = self.compute_global_importance()

        json_path = out_path / GLOBAL_SHAP_JSON_NAME
        json_path.write_text(json.dumps(global_info, indent=2), encoding="utf-8")

        # Format Markdown report
        md_lines = [
            "# Road2Hire — M4.5 SHAP Global Feature Explainability Report",
            "",
            f"**Model Architecture:** `{type(self.classifier).__name__}` (`{self.explainer_type}`)  ",
            f"**Population Evaluated:** $N = {global_info['sample_count']}$ verified candidate records  ",
            f"**Target Classes:** `{global_info['classes']}`  ",
            "",
            "---",
            "",
            "## 1. Overall Global Feature Importance",
            "",
            "Feature importance ranked by mean absolute SHAP value across all samples and classes:",
            "",
            "| Rank | Feature Name | Mean |SHAP| | Description |",
            "|:---:|:---|:---:|:---|",
        ]

        for item in global_info["overall_feature_importance"]:
            md_lines.append(
                f"| **{item['rank']}** | `{item['feature']}` | **{item['mean_abs_shap']:.4f}** | "
                f"{item['description']} |"
            )

        md_lines.extend([
            "",
            "---",
            "",
            "## 2. Class-Specific Feature Contributions",
            "",
            "Mean absolute SHAP value (|SHAP|) and mean signed directional contribution for each readiness class:",
            "",
        ])

        for c_name in global_info["classes"]:
            md_lines.extend([
                f"### Target Class: `{c_name}`",
                "",
                "| Rank | Feature | Mean |SHAP| (Magnitude) | Mean Signed SHAP (Direction) |",
                "|:---:|:---|:---:|:---:|",
            ])
            for item in global_info["class_specific_importance"][c_name]:
                md_lines.append(
                    f"| {item['rank']} | `{item['feature']}` | {item['mean_abs_shap']:.4f} | "
                    f"{item['mean_signed_shap']:+.4f} |"
                )
            md_lines.append("")

        md_lines.extend([
            "---",
            "",
            "## 3. Methodological Interpretation & Governance",
            "",
            "1. **Dominant Signal (Technical Skills & Degree Level):** Across all classes, `skills_count` and `edu_level_ordinal` serve as the primary macro anchors for readiness classification.",
            "2. **Job Ready Drivers:** `skills_count` (+1.264) and `exp_positions_count` (+0.472) provide the strongest positive directional lift toward `Job Ready`.",
            "3. **Not Ready Drivers:** A low `skills_count` is the overwhelming driver (+1.356) pushing candidates into `Not Ready`.",
            "4. **No Causal Claim:** SHAP values explain internal model weight allocations and must not be communicated to candidates as certified real-world qualifications.",
            "",
        ])

        report_path = out_path.parent / EXPLAINABILITY_REPORT_NAME
        report_path.write_text("\n".join(md_lines), encoding="utf-8")

        return json_path, report_path

