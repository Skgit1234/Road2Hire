"""Keyword-based skill matching baseline for Road2Hire.

Provides exact case-insensitive skill matching between candidate skills
and job required skills.

Metric frame of reference:
--------------------------
All Precision, Recall, and F1 metrics are evaluated from the perspective of
required-skill gap detection:
  TP -- required skill correctly identified as present in candidate skills.
  FN -- required skill candidate lacks (reported in missing_skills).
  FP -- required skill incorrectly identified as present. For exact
        keyword matching, FP = 0 by construction.

Documented Precision limitation:
---------------------------------
Because FP = 0 by construction, Precision is 1.0 whenever TP > 0.
This confirms the matcher does not falsely claim a skill is present, but it
does NOT evaluate whether the candidate holds irrelevant skills. Evaluating
whether candidate skills are irrelevant to the role is a separate concern,
captured in candidate_skills_not_required; it does not affect Precision.

Undefined-value convention:
---------------------------
  Precision = None  when TP + FP == 0 (no positive predictions: 0/0).
  Recall    = None  when TP + FN == 0 (no required skills: 0/0).
  F1        = None  when Precision or Recall is None, or sum == 0.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from AI.Baseline.evaluation_metrics import precision_recall_f1


def keyword_match(
    candidate_skills: list[str],
    required_skills: list[str],
) -> dict[str, Any]:
    """Perform exact case-insensitive keyword matching.

    Preserved for backward compatibility.
    """
    candidate = {skill.lower() for skill in candidate_skills}

    present = []
    missing = []

    for skill in required_skills:
        if skill.lower() in candidate:
            present.append(skill)
        else:
            missing.append(skill)

    total_required = len(required_skills)
    matched = len(present)

    score = matched / total_required if total_required else 0

    return {
        "present_skills": present,
        "missing_skills": missing,
        "match_score": round(score, 2),
    }


def keyword_match_with_metrics(
    candidate_skills: list[str],
    required_skills: list[str],
) -> dict[str, Any]:
    """Perform keyword matching with Precision, Recall, F1, and diagnostics.

    Computes skill gap metrics against required_skills. Irrelevant candidate
    skills are reported separately in candidate_skills_not_required.
    """
    base_result = keyword_match(candidate_skills, required_skills)
    present = base_result["present_skills"]
    missing = base_result["missing_skills"]
    match_score = base_result["match_score"]

    candidate_lower = {skill.lower() for skill in candidate_skills}
    required_lower = {skill.lower() for skill in required_skills}

    candidate_skills_not_required = [
        skill for skill in candidate_skills
        if skill.lower() not in required_lower
    ]

    tp = len(present)
    fp = 0
    fn = len(missing)

    prf = precision_recall_f1(tp, fp, fn)

    return {
        "present_skills": present,
        "missing_skills": missing,
        "match_score": match_score,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": prf["precision"],
        "recall": prf["recall"],
        "f1": prf["f1"],
        "candidate_skills_not_required": candidate_skills_not_required,
        "ndcg": None,
    }


def main():
    eval_file = PROJECT_ROOT / "AI" / "Baseline" / "sample_evaluation.json"
    with open(eval_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    results = []

    for sample in data["samples"]:
        result = keyword_match(
            sample["candidate_skills"],
            sample["required_skills"],
        )

        results.append({
            "id": sample["id"],
            **result,
        })

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()