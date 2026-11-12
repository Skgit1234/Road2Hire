"""Taxonomy-based skill matching baseline for Road2Hire.

Provides alias expansion and canonical skill matching using Road2Hire's
skill graph vocabulary and curated ESCO taxonomy mappings.

Key distinctions from keyword matching:
---------------------------------------
1. Normalizes skill variants and aliases (e.g., 'ML' -> 'Machine Learning',
   'sklearn' -> 'Scikit-learn') before comparison.
2. Distinguishes skills not recognized by the current vocabulary/taxonomy
   matcher from genuine skill gaps without forcing incorrect mappings.
3. Annotates matched and missing skills with their ESCO mapping status
   ('exact_concept', 'unmapped', 'not_in_esco_csv'). Unmapped status
   does not prevent skills from matching at the canonical name level.

Metric frame of reference:
--------------------------
Evaluated over recognized required skills:
  TP -- recognized required skill present in candidate's canonical skills.
  FN -- recognized required skill absent from candidate's canonical skills.
  FP -- 0 by construction for canonical exact-match.

Documented Precision limitation:
---------------------------------
Because FP = 0 by construction, Precision is 1.0 whenever TP > 0.
This confirms the matcher does not falsely claim a skill is present, but it
does NOT evaluate whether the candidate holds irrelevant skills. Evaluating
whether candidate skills are irrelevant to the role is captured separately in
candidate_skills_not_required. Unrecognized candidate skills are captured in
unrecognized_candidate.

Undefined-value convention:
---------------------------
  Precision = None  when TP + FP == 0 (no positive predictions: 0/0).
  Recall    = None  when TP + FN == 0 (no recognized required skills: 0/0).
  F1        = None  when Precision or Recall is None, or sum == 0.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from AI.Baseline.evaluation_metrics import precision_recall_f1
from AI.Skill_Extraction.skill_extractor import (
    load_skill_vocabulary,
    normalize_skill_name,
)
from AI.Skill_Extraction.skill_taxonomy_mapper import (
    ESCO_MAPPING_PATH,
    load_esco_mapping,
)


def get_skill_esco_status(
    skill_name: str,
    esco_mapping: dict[str, dict[str, str]],
) -> str:
    """Determine the ESCO status of a skill from curated mappings.

    Returns
    -------
    'exact_concept' : present in ESCO CSV with a non-empty concept URI.
    'unmapped' : present in ESCO CSV explicitly recorded as unmapped.
    'not_in_esco_csv' : recognized in vocabulary but absent from ESCO CSV.
    """
    mapping = esco_mapping.get(skill_name.casefold())
    if mapping:
        mapping_type = mapping.get("Mapping_Type", "").strip()
        esco_id = mapping.get("ESCO_Skill_Id", "").strip()
        if mapping_type == "exact_concept" and esco_id:
            return "exact_concept"
        return "unmapped"
    return "not_in_esco_csv"


def taxonomy_match(
    candidate_skills: list[str],
    required_skills: list[str],
    vocabulary: list[str] | None = None,
    esco_mapping: dict[str, dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Perform taxonomy-based skill matching with alias expansion and ESCO diagnostics.

    Parameters
    ----------
    candidate_skills : list of skill names from candidate profile/resume.
    required_skills : list of skill names required for the role.
    vocabulary : optional curated vocabulary list. Loaded from graph if None.
    esco_mapping : optional ESCO mapping dict. Loaded from CSV if None.

    Returns
    -------
    dict with keys:
        present_skills : list of recognized required skills present in candidate.
        missing_skills : list of recognized required skills missing from candidate.
        unrecognized_candidate : candidate skills not recognized by current vocabulary/taxonomy matcher.
        unrecognized_required : required skills not recognized by current vocabulary/taxonomy matcher.
        candidate_skills_not_required : recognized candidate skills not in required set.
        esco_status : dict mapping each recognized required skill to its ESCO status.
        match_score : ratio of present recognized skills to total recognized required skills.
        tp, fp, fn : confusion matrix counts for recognized required skills.
        precision, recall, f1 : metrics according to defined conventions.
        ndcg : None (unranked match).
    """
    if vocabulary is None:
        vocabulary = load_skill_vocabulary()
    if esco_mapping is None:
        esco_mapping = load_esco_mapping(ESCO_MAPPING_PATH)

    # 1. Normalize candidate skills
    candidate_canonical_set: set[str] = set()
    recognized_candidate: list[str] = []
    unrecognized_candidate: list[str] = []

    for raw_skill in candidate_skills:
        canonical = normalize_skill_name(raw_skill, vocabulary=vocabulary)
        if canonical is not None:
            candidate_canonical_set.add(canonical)
            recognized_candidate.append(canonical)
        else:
            unrecognized_candidate.append(raw_skill)

    # 2. Normalize required skills and classify as present, missing, or unrecognized
    present_skills: list[str] = []
    missing_skills: list[str] = []
    unrecognized_required: list[str] = []
    recognized_required_canonicals: set[str] = set()

    for raw_skill in required_skills:
        canonical = normalize_skill_name(raw_skill, vocabulary=vocabulary)
        if canonical is not None:
            recognized_required_canonicals.add(canonical)
            if canonical in candidate_canonical_set:
                present_skills.append(canonical)
            else:
                missing_skills.append(canonical)
        else:
            unrecognized_required.append(raw_skill)

    # 3. Identify recognized candidate skills not required
    # Retain the original candidate skill name for those recognized skills not in required
    candidate_skills_not_required: list[str] = []
    for raw_skill in candidate_skills:
        canonical = normalize_skill_name(raw_skill, vocabulary=vocabulary)
        if canonical is not None and canonical not in recognized_required_canonicals:
            candidate_skills_not_required.append(raw_skill)

    # 4. Compute ESCO status for all recognized required skills
    esco_status: dict[str, str] = {}
    for skill in present_skills:
        esco_status[skill] = get_skill_esco_status(skill, esco_mapping)
    for skill in missing_skills:
        esco_status[skill] = get_skill_esco_status(skill, esco_mapping)

    # 5. Compute metrics over recognized required skills
    total_recognized = len(present_skills) + len(missing_skills)
    matched = len(present_skills)
    match_score = round(matched / total_recognized, 2) if total_recognized > 0 else 0.0

    tp = matched
    fp = 0
    fn = len(missing_skills)

    prf = precision_recall_f1(tp, fp, fn)

    return {
        "present_skills": present_skills,
        "missing_skills": missing_skills,
        "unrecognized_candidate": unrecognized_candidate,
        "unrecognized_required": unrecognized_required,
        "candidate_skills_not_required": candidate_skills_not_required,
        "esco_status": esco_status,
        "match_score": match_score,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": prf["precision"],
        "recall": prf["recall"],
        "f1": prf["f1"],
        "ndcg": None,
    }


def main():
    eval_file = PROJECT_ROOT / "AI" / "Baseline" / "evaluation_data.json"
    if not eval_file.exists():
        eval_file = PROJECT_ROOT / "AI" / "Baseline" / "sample_evaluation.json"

    with open(eval_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    results = []
    for sample in data["samples"]:
        result = taxonomy_match(
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
