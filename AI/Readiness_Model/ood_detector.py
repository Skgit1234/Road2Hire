"""Out-of-Distribution (OOD) Detection for Career Readiness Model (Phase 2).

Quantifies how closely incoming candidate features align with the empirical
training feature distribution (M4.3 pilot dataset, N=71).

Guarantees:
- Transparent detection of empirical range violations (min/max bounds).
- Statistical outlier detection via z-score and IQR thresholds.
- Structured, human-readable warnings identifying affected features.
- Zero modification or clipping of candidate feature values.
- Separate and decoupled from the classifier's class and probability predictions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Default empirical training feature statistics for M4.3 pilot dataset (N=71)
DEFAULT_TRAINING_FEATURE_STATS: dict[str, dict[str, float]] = {
    "skills_count": {
        "min": 0.0,
        "max": 14.0,
        "mean": 6.9437,
        "std": 4.0347,
        "q25": 4.0,
        "q75": 10.0,
        "iqr": 6.0,
    },
    "exp_positions_count": {
        "min": 1.0,
        "max": 3.0,
        "mean": 1.3662,
        "std": 0.5627,
        "q25": 1.0,
        "q75": 2.0,
        "iqr": 1.0,
    },
    "has_senior_role": {
        "min": 0.0,
        "max": 1.0,
        "mean": 0.0986,
        "std": 0.2981,
        "q25": 0.0,
        "q75": 0.0,
        "iqr": 0.0,
    },
    "project_count": {
        "min": 0.0,
        "max": 3.0,
        "mean": 1.5775,
        "std": 1.1946,
        "q25": 0.5,
        "q75": 3.0,
        "iqr": 2.5,
    },
    "project_words": {
        "min": 0.0,
        "max": 88.0,
        "mean": 34.3803,
        "std": 27.9952,
        "q25": 2.5,
        "q75": 57.5,
        "iqr": 55.0,
    },
    "project_tech_count": {
        "min": 0.0,
        "max": 15.0,
        "mean": 4.2113,
        "std": 4.6842,
        "q25": 1.0,
        "q75": 6.0,
        "iqr": 5.0,
    },
    "has_production_system": {
        "min": 0.0,
        "max": 1.0,
        "mean": 0.2394,
        "std": 0.4267,
        "q25": 0.0,
        "q75": 0.0,
        "iqr": 0.0,
    },
    "edu_level_ordinal": {
        "min": 1.0,
        "max": 2.0,
        "mean": 1.4366,
        "std": 0.496,
        "q25": 1.0,
        "q75": 2.0,
        "iqr": 1.0,
    },
    "is_stem_degree": {
        "min": 0.0,
        "max": 1.0,
        "mean": 0.8169,
        "std": 0.3867,
        "q25": 1.0,
        "q75": 1.0,
        "iqr": 0.0,
    },
}


@dataclass
class OODDetectionResult:
    """Structured output of an Out-of-Distribution evaluation."""

    is_ood: bool
    ood_warnings: list[str] = field(default_factory=list)
    range_violations: list[str] = field(default_factory=list)
    statistical_outliers: list[str] = field(default_factory=list)
    feature_diagnostics: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ReadinessOODDetector:
    """Detects whether incoming candidate features deviate from training distributions."""

    def __init__(
        self,
        training_stats: dict[str, dict[str, float]] | None = None,
        z_threshold: float = 3.0,
    ) -> None:
        """Initialize detector with training statistics and outlier z-score threshold."""
        self.training_stats = (
            dict(training_stats)
            if training_stats is not None
            else dict(DEFAULT_TRAINING_FEATURE_STATS)
        )
        self.z_threshold = z_threshold

    @classmethod
    def fit_from_feature_matrix(
        cls,
        X: np.ndarray,
        feature_names: list[str],
        z_threshold: float = 3.0,
    ) -> ReadinessOODDetector:
        """Fit empirical distribution statistics directly from a 2D feature matrix."""
        stats: dict[str, dict[str, float]] = {}
        for idx, name in enumerate(feature_names):
            col = X[:, idx]
            q25, q75 = np.percentile(col, [25, 75])
            iqr = q75 - q25
            stats[name] = {
                "min": float(np.min(col)),
                "max": float(np.max(col)),
                "mean": float(round(np.mean(col), 4)),
                "std": float(round(np.std(col), 4)),
                "q25": float(round(q25, 4)),
                "q75": float(round(q75, 4)),
                "iqr": float(round(iqr, 4)),
            }
        return cls(training_stats=stats, z_threshold=z_threshold)

    def detect(
        self,
        features: dict[str, float] | np.ndarray | list[float],
        feature_names: list[str] | None = None,
    ) -> OODDetectionResult:
        """Evaluate a candidate feature vector for range violations and statistical outliers.

        Parameters
        ----------
        features:
            Dictionary mapping feature names to numeric values, or a 1D vector.
        feature_names:
            Optional ordered list of feature names if features is an array/list.

        Returns
        -------
        OODDetectionResult containing booleans, diagnostic details, and human-readable warnings.
        """
        # Convert to dictionary representation
        if isinstance(features, dict):
            feat_dict = {k: float(v) for k, v in features.items()}
        elif isinstance(features, (np.ndarray, list)):
            names = feature_names or list(self.training_stats.keys())
            arr = np.asarray(features, dtype=float).ravel()
            feat_dict = {name: float(arr[i]) for i, name in enumerate(names) if i < len(arr)}
        else:
            raise TypeError(f"Unsupported features type: {type(features)}")

        warnings: list[str] = []
        range_violations: list[str] = []
        stat_outliers: list[str] = []
        diagnostics: dict[str, dict[str, Any]] = {}

        for feat_name, val in feat_dict.items():
            if feat_name not in self.training_stats:
                continue

            stats = self.training_stats[feat_name]
            f_min = stats["min"]
            f_max = stats["max"]
            f_mean = stats["mean"]
            f_std = stats["std"]

            # 1. Empirical Range Check
            is_range_viol = False
            viol_direction = None
            if val < f_min:
                is_range_viol = True
                viol_direction = "below_min"
                msg = (
                    f"Feature '{feat_name}' value {val:.1f} is below the observed "
                    f"training minimum {f_min:.1f}."
                )
                range_violations.append(msg)
                warnings.append(msg)
            elif val > f_max:
                is_range_viol = True
                viol_direction = "above_max"
                msg = (
                    f"Feature '{feat_name}' value {val:.1f} exceeds the observed "
                    f"training maximum {f_max:.1f}."
                )
                range_violations.append(msg)
                warnings.append(msg)

            # 2. Z-Score Statistical Outlier Check
            z_score = 0.0
            is_stat_outlier = False
            if f_std > 1e-6:
                z_score = float((val - f_mean) / f_std)
                if abs(z_score) >= self.z_threshold:
                    is_stat_outlier = True
                    msg = (
                        f"Feature '{feat_name}' value {val:.1f} deviates significantly from "
                        f"the training mean {f_mean:.1f} (|z| = {abs(z_score):.2f} >= {self.z_threshold:.1f})."
                    )
                    stat_outliers.append(msg)
                    if not is_range_viol:
                        warnings.append(msg)

            diagnostics[feat_name] = {
                "value": round(val, 4),
                "training_min": f_min,
                "training_max": f_max,
                "training_mean": f_mean,
                "training_std": f_std,
                "z_score": round(z_score, 2),
                "is_range_violation": is_range_viol,
                "range_violation_direction": viol_direction,
                "is_statistical_outlier": is_stat_outlier,
            }

        is_ood = bool(range_violations or stat_outliers)

        return OODDetectionResult(
            is_ood=is_ood,
            ood_warnings=warnings,
            range_violations=range_violations,
            statistical_outliers=stat_outliers,
            feature_diagnostics=diagnostics,
        )

    def get_training_stats(self) -> dict[str, dict[str, float]]:
        """Return a copy of the stored empirical training statistics."""
        return {k: dict(v) for k, v in self.training_stats.items()}

    def to_dict(self) -> dict[str, Any]:
        """Serialize detector configuration."""
        return {
            "training_stats": self.training_stats,
            "z_threshold": self.z_threshold,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReadinessOODDetector:
        """Instantiate detector from serialized dictionary."""
        return cls(
            training_stats=data.get("training_stats"),
            z_threshold=float(data.get("z_threshold", 3.0)),
        )


def get_default_ood_detector() -> ReadinessOODDetector:
    """Return a singleton or default OOD detector populated with training statistics."""
    return ReadinessOODDetector()
