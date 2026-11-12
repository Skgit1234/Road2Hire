"""Configurable, explainable scoring formulas for Road2Hire M3 Hybrid Skill Gap Detection.

Provides mathematical formulations for essential, optional, and overall skill coverage
without interpreting similarity scores as probabilities or job-readiness guarantees.
"""

from __future__ import annotations

from typing import Any

# Default configuration constants
DEFAULT_ESSENTIAL_WEIGHT = 0.75
DEFAULT_OPTIONAL_WEIGHT = 0.25

EXACT_MATCH_CREDIT = 1.0
SEMANTIC_CONFIRMED_CREDIT = 1.0
GRAPH_NARROWER_CREDIT = 0.75
GRAPH_RELATED_CREDIT = 0.70
GRAPH_BROADER_CREDIT = 0.60
SEMANTIC_PARTIAL_SCALE = 0.50

DISCLAIMER_TEXT = (
    "Skill coverage scores represent a heuristic alignment between candidate skills and "
    "ESCO occupation requirements. They are NOT probabilities, hiring guarantees, or "
    "statistically validated predictors of job performance."
)


def compute_gap_scores(
    essential_credits: list[float],
    total_essential_count: int,
    optional_credits: list[float],
    total_optional_count: int,
    essential_weight: float = DEFAULT_ESSENTIAL_WEIGHT,
    optional_weight: float = DEFAULT_OPTIONAL_WEIGHT,
) -> dict[str, Any]:
    """Compute essential, optional, and overall skill coverage scores.

    Handles zero candidate skills, occupations with zero optional skills,
    and missing values gracefully without division-by-zero errors.

    Parameters
    ----------
    essential_credits:
        List of credit scores [0.0 to 1.0] awarded to essential skills.
    total_essential_count:
        Total number of essential skills required by the occupation.
    optional_credits:
        List of credit scores [0.0 to 1.0] awarded to optional skills.
    total_optional_count:
        Total number of optional skills recommended by the occupation.
    essential_weight:
        Weight assigned to essential skills in overall score (default 0.75).
    optional_weight:
        Weight assigned to optional skills in overall score (default 0.25).

    Returns
    -------
    dict with:
        essential_score: float (0.0 to 1.0)
        optional_score: float | None (None if total_optional_count == 0)
        overall_score: float (0.0 to 1.0)
        weights_used: dict
    """
    # Validate weights are non-negative
    if essential_weight < 0 or optional_weight < 0:
        raise ValueError("Scoring weights must be non-negative.")

    # 1. Essential score
    if total_essential_count <= 0:
        essential_score = 1.0 if not essential_credits else 0.0
    else:
        essential_sum = sum(essential_credits)
        essential_score = min(1.0, max(0.0, essential_sum / total_essential_count))

    # 2. Optional score (handle zero optional skills without division-by-zero)
    if total_optional_count <= 0:
        optional_score = None
    else:
        optional_sum = sum(optional_credits)
        optional_score = min(1.0, max(0.0, optional_sum / total_optional_count))

    # 3. Overall score
    if optional_score is None:
        # If there are no optional skills, overall score is 100% driven by essential skills
        overall_score = essential_score
        effective_weights = {"essential": 1.0, "optional": 0.0}
    elif total_essential_count <= 0:
        # Fallback if an occupation hypothetically has no essential skills
        overall_score = optional_score
        effective_weights = {"essential": 0.0, "optional": 1.0}
    else:
        # Normalize weights to sum to 1.0
        weight_sum = essential_weight + optional_weight
        if weight_sum <= 0:
            norm_e_weight = DEFAULT_ESSENTIAL_WEIGHT
            norm_o_weight = DEFAULT_OPTIONAL_WEIGHT
        else:
            norm_e_weight = essential_weight / weight_sum
            norm_o_weight = optional_weight / weight_sum

        overall_score = (norm_e_weight * essential_score) + (norm_o_weight * optional_score)
        overall_score = min(1.0, max(0.0, overall_score))
        effective_weights = {"essential": norm_e_weight, "optional": norm_o_weight}

    return {
        "essential_skill_coverage_score": round(essential_score, 4),
        "optional_skill_coverage_score": round(optional_score, 4) if optional_score is not None else None,
        "overall_skill_coverage_score": round(overall_score, 4),
        "scoring_weights": effective_weights,
    }
