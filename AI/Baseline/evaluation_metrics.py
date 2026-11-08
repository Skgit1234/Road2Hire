"""
Evaluation metrics for Road2Hire skill matching baselines.

Provides Precision, Recall, F1-score, macro-aggregate, and NDCG@k.
All functions are implemented from first principles with no external
dependencies (no scikit-learn, no scipy).

Metric frame of reference
--------------------------
All P/R/F1 metrics are computed from the perspective of required-skill
gap detection:

  TP -- required skill correctly identified as present in the candidate.
  FN -- required skill the candidate genuinely lacks (absent from candidate set).
  FP -- required skill incorrectly called "present" when candidate lacks it.
       For the exact-match keyword and canonical taxonomy matchers, FP = 0
       by construction.

Documented Precision limitation
---------------------------------
Because FP = 0 for these matchers, Precision = 1.0 whenever TP > 0.
This confirms the matcher does not falsely claim a skill is present, but it
does NOT evaluate whether the candidate holds irrelevant skills. That
concern is captured separately in the candidate_skills_not_required
output field of each matcher; it does not affect Precision.

Undefined-value convention
---------------------------
  Precision = None  when TP + FP == 0  (no positive predictions: 0/0).
  Recall    = None  when TP + FN == 0  (no required skills: 0/0).
  F1        = None  when Precision or Recall is None, or their sum == 0.

Aggregate (macro) None-handling convention
-------------------------------------------
  Recall is 0.0 in typical use (candidate has none of the required skills)
  and is included in every sample's macro average.
  Precision and F1 may be None for some samples (when TP == 0).
  None values are EXCLUDED from macro averages; only defined values
  contribute. The counts of excluded samples are reported so the caller
  can assess how representative the averages are.
  If ALL samples have Precision == None, macro_precision is None.
"""

from __future__ import annotations

import math
from typing import Any


def precision_recall_f1(
    tp: int,
    fp: int,
    fn: int,
) -> dict[str, float | None]:
    """Return Precision, Recall, and F1 from raw confusion-matrix counts.

    Parameters
    ----------
    tp : int
        True positives -- required skills correctly identified as present.
    fp : int
        False positives -- skills incorrectly called present.
        For the keyword and taxonomy exact-match baselines this is always 0.
    fn : int
        False negatives -- required skills the candidate genuinely lacks.

    Returns
    -------
    dict with keys "precision", "recall", "f1".
    Any value may be None according to the undefined-value convention.

    Raises
    ------
    ValueError if any count is negative.
    """
    if tp < 0 or fp < 0 or fn < 0:
        raise ValueError("tp, fp, fn must all be non-negative integers.")

    precision: float | None
    recall: float | None
    f1: float | None

    if tp + fp == 0:
        precision = None  # 0 / 0 -- undefined
    else:
        precision = tp / (tp + fp)

    if tp + fn == 0:
        recall = None  # 0 / 0 -- no required skills
    else:
        recall = tp / (tp + fn)

    if precision is None or recall is None:
        f1 = None
    elif precision + recall == 0.0:
        f1 = None  # both zero -- harmonic mean undefined
    else:
        f1 = 2.0 * precision * recall / (precision + recall)

    return {"precision": precision, "recall": recall, "f1": f1}


def aggregate_metrics(
    per_sample_metrics: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute macro-averaged metrics over a list of per-sample metric dicts.

    None-handling convention (documented):
      - Recall is typically always defined (0.0 when all required skills are
        missing) and is included in every sample's macro average. The rare
        case where Recall is None (no required skills at all) is excluded
        from the macro, consistent with the treatment of Precision.
      - Precision and F1 may be None for some samples (when TP == 0).
        None values are EXCLUDED from the macro averages for Precision and F1.
        Only samples with a defined (non-None) value contribute.
      - If ALL samples have Precision == None, macro_precision is None.
      - The counts of excluded samples are reported as
        precision_undefined_count and f1_undefined_count so the caller can
        assess how representative the macro averages are.

    Parameters
    ----------
    per_sample_metrics : list of dicts, each containing at minimum:
        "precision" (float | None), "recall" (float | None),
        "f1" (float | None).

    Returns
    -------
    dict with keys:
        macro_precision (float | None),
        macro_recall (float | None),
        macro_f1 (float | None),
        precision_undefined_count (int),
        f1_undefined_count (int),
        sample_count (int).

    Raises
    ------
    TypeError if per_sample_metrics is not a list.
    """
    if not isinstance(per_sample_metrics, list):
        raise TypeError("per_sample_metrics must be a list.")

    n = len(per_sample_metrics)

    if n == 0:
        return {
            "macro_precision": None,
            "macro_recall": None,
            "macro_f1": None,
            "precision_undefined_count": 0,
            "f1_undefined_count": 0,
            "sample_count": 0,
        }

    defined_precisions: list[float] = []
    defined_recalls: list[float] = []
    defined_f1s: list[float] = []
    precision_undefined_count = 0
    f1_undefined_count = 0

    for sample in per_sample_metrics:
        p = sample.get("precision")
        r = sample.get("recall")
        f = sample.get("f1")

        if p is None:
            precision_undefined_count += 1
        else:
            defined_precisions.append(float(p))

        if r is None:
            pass  # exclude None recall from macro (same principle as precision)
        else:
            defined_recalls.append(float(r))

        if f is None:
            f1_undefined_count += 1
        else:
            defined_f1s.append(float(f))

    macro_precision: float | None = (
        sum(defined_precisions) / len(defined_precisions)
        if defined_precisions else None
    )
    macro_recall: float | None = (
        sum(defined_recalls) / len(defined_recalls)
        if defined_recalls else None
    )
    macro_f1: float | None = (
        sum(defined_f1s) / len(defined_f1s)
        if defined_f1s else None
    )

    return {
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1": macro_f1,
        "precision_undefined_count": precision_undefined_count,
        "f1_undefined_count": f1_undefined_count,
        "sample_count": n,
    }


def ndcg_at_k(
    ranked_list: list[str],
    relevant_set: set[str],
    k: int,
) -> float | None:
    """Compute Normalized Discounted Cumulative Gain at rank k.

    Implemented from first principles; no external dependencies.

    For the keyword and taxonomy matchers, which produce unranked binary
    sets, this function returns None because there is no ranked list to
    score. It is provided as a metric utility for Issue #16 completeness
    and for future ranked matchers.

    Parameters
    ----------
    ranked_list : ordered list of skill name strings (best-ranked first).
    relevant_set : set of relevant (correct) skill names.
    k : number of top positions to evaluate.

    Returns
    -------
    float in [0.0, 1.0], or None when scoring is not possible:
      - ranked_list is empty
      - k == 0
    Returns 0.0 when relevant_set is empty (nothing to gain).

    Notes
    -----
    Gain formula: rel(i) in {0, 1} (binary relevance).
    DCG@k  = sum_{i=1}^{k} rel(i) / log2(i + 1)
    IDCG@k = DCG of the ideal ranked list (all relevant items at top)
    NDCG@k = DCG@k / IDCG@k
    """
    if not ranked_list or k == 0:
        return None

    if not relevant_set:
        return 0.0

    def _dcg(items: list[str], cutoff: int) -> float:
        score = 0.0
        for rank, item in enumerate(items[:cutoff], start=1):
            if item in relevant_set:
                score += 1.0 / math.log2(rank + 1)
        return score

    actual_dcg = _dcg(ranked_list, k)

    # Ideal DCG: place as many relevant items as possible at the top k.
    ideal_count = min(len(relevant_set), k)
    ideal_dcg = sum(
        1.0 / math.log2(rank + 1)
        for rank in range(1, ideal_count + 1)
    )

    if ideal_dcg == 0.0:
        return None  # should not occur when relevant_set is non-empty

    return actual_dcg / ideal_dcg
