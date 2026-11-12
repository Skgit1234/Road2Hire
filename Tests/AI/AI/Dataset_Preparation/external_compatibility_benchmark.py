"""External Compatibility Benchmark for Road2Hire.

Evaluates Road2Hire's candidate-job compatibility scoring against external benchmark
scores (matches.csv final_score and candidate_rank).

Methodological Notes:
- matches.csv represents top-k retrieved positive pairs (no hard negatives).
- External final_score is a heuristic retrieval baseline, NOT ground-truth career readiness.
- Metrics evaluated: Pearson r, Spearman rho, MAE, RMSE, and rank percentile alignment.
"""

from __future__ import annotations

import logging
import math
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkMetrics:
    """Statistical alignment metrics between predicted and benchmark scores."""

    sample_size: int = 0
    pearson_r: float = 0.0
    spearman_rho: float = 0.0
    mae: float = 0.0
    rmse: float = 0.0
    r2_score: float = 0.0
    mean_true: float = 0.0
    mean_pred: float = 0.0
    std_true: float = 0.0
    std_pred: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_correlation_metrics(
    y_true: list[float] | np.ndarray,
    y_pred: list[float] | np.ndarray,
) -> BenchmarkMetrics:
    """Calculate Pearson r, Spearman rho, MAE, and RMSE between two continuous score sets."""
    arr_true = np.asarray(y_true, dtype=float)
    arr_pred = np.asarray(y_pred, dtype=float)

    if len(arr_true) != len(arr_pred):
        raise ValueError(f"Array lengths differ: {len(arr_true)} vs {len(arr_pred)}")

    n = len(arr_true)
    if n < 2:
        return BenchmarkMetrics(sample_size=n)

    # Filtering NaNs or Infs
    mask = np.isfinite(arr_true) & np.isfinite(arr_pred)
    arr_true = arr_true[mask]
    arr_pred = arr_pred[mask]
    n = len(arr_true)

    if n < 2:
        return BenchmarkMetrics(sample_size=n)

    mean_t = float(np.mean(arr_true))
    mean_p = float(np.mean(arr_pred))
    std_t = float(np.std(arr_true))
    std_p = float(np.std(arr_pred))

    # Pearson r
    if std_t > 1e-9 and std_p > 1e-9:
        cov = np.mean((arr_true - mean_t) * (arr_pred - mean_p))
        pearson_r = float(cov / (std_t * std_p))
        pearson_r = max(-1.0, min(1.0, pearson_r))
    else:
        pearson_r = 0.0

    # Spearman rho (rank correlation)
    rank_true = np.argsort(np.argsort(arr_true)).astype(float)
    rank_pred = np.argsort(np.argsort(arr_pred)).astype(float)
    std_rt = float(np.std(rank_true))
    std_rp = float(np.std(rank_pred))
    if std_rt > 1e-9 and std_rp > 1e-9:
        cov_rank = np.mean((rank_true - np.mean(rank_true)) * (rank_pred - np.mean(rank_pred)))
        spearman_rho = float(cov_rank / (std_rt * std_rp))
        spearman_rho = max(-1.0, min(1.0, spearman_rho))
    else:
        spearman_rho = 0.0

    # MAE and RMSE
    mae = float(np.mean(np.abs(arr_true - arr_pred)))
    rmse = float(np.sqrt(np.mean((arr_true - arr_pred) ** 2)))

    # R2
    ss_tot = float(np.sum((arr_true - mean_t) ** 2))
    ss_res = float(np.sum((arr_true - arr_pred) ** 2))
    r2 = float(1.0 - (ss_res / ss_tot)) if ss_tot > 1e-9 else 0.0

    return BenchmarkMetrics(
        sample_size=n,
        pearson_r=round(pearson_r, 4),
        spearman_rho=round(spearman_rho, 4),
        mae=round(mae, 4),
        rmse=round(rmse, 4),
        r2_score=round(r2, 4),
        mean_true=round(mean_t, 4),
        mean_pred=round(mean_p, 4),
        std_true=round(std_t, 4),
        std_pred=round(std_p, 4),
    )


class ExternalCompatibilityBenchmark:
    """Benchmark suite for evaluating compatibility models against the external dataset."""

    def __init__(self) -> None:
        pass

    def evaluate_predictions(
        self,
        records: list[dict[str, Any]],
        pred_score_key: str = "predicted_score",
        true_score_key: str = "final_score",
    ) -> dict[str, Any]:
        """Evaluate a collection of pair records containing both true and predicted scores."""
        y_true = [float(r[true_score_key]) for r in records if true_score_key in r and pred_score_key in r]
        y_pred = [float(r[pred_score_key]) for r in records if true_score_key in r and pred_score_key in r]

        overall = compute_correlation_metrics(y_true, y_pred)

        # Categorical slice if category is available
        by_category: dict[str, dict[str, Any]] = {}
        by_label_strength: dict[str, dict[str, Any]] = {}

        for r in records:
            cat = r.get("category") or r.get("inferred_category")
            if cat:
                by_category.setdefault(str(cat), []).append(r)
            strength = r.get("label_strength")
            if strength:
                by_label_strength.setdefault(str(strength), []).append(r)

        category_metrics: dict[str, dict[str, Any]] = {}
        for cat, cat_records in by_category.items():
            if len(cat_records) >= 5:
                yt = [float(x[true_score_key]) for x in cat_records if true_score_key in x and pred_score_key in x]
                yp = [float(x[pred_score_key]) for x in cat_records if true_score_key in x and pred_score_key in x]
                category_metrics[cat] = compute_correlation_metrics(yt, yp).to_dict()

        strength_metrics: dict[str, dict[str, Any]] = {}
        for strength, str_records in by_label_strength.items():
            if len(str_records) >= 5:
                yt = [float(x[true_score_key]) for x in str_records if true_score_key in x and pred_score_key in x]
                yp = [float(x[pred_score_key]) for x in str_records if true_score_key in x and pred_score_key in x]
                strength_metrics[strength] = compute_correlation_metrics(yt, yp).to_dict()

        return {
            "overall": overall.to_dict(),
            "by_category": category_metrics,
            "by_label_strength": strength_metrics,
            "evaluation_note": (
                "Evaluates pairwise retrieval compatibility against external heuristic score. "
                "This benchmark does NOT measure career readiness."
            ),
        }

