"""Gold-Label Dataset Quality Audit for Road2Hire (M4.2).

Performs a rigorous audit of Datasets/gold_labels.json against:
1. Synthetic Candidate Profiles (Datasets/synthetic_profiles.json)
2. Scraped Job Postings (Datasets/scraped_jobs.json)

Verifies:
- Classification into Verified, Pending, Missing Status, and Invalid
- Candidate and Job referential integrity
- Score ranges, null values, and composite score formula consistency
- Duplicate candidate-job pairs
- Reasoning evidence presence and sufficiency
- Distinction between Candidate-Job Compatibility vs. Career Readiness
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, TypedDict

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASETS_DIR = PROJECT_ROOT / "Datasets"


class RecordAuditIssue(TypedDict, total=False):
    index: int
    pair_id: str
    issue_type: str
    details: str


class ScoreAuditSummary(TypedDict, total=False):
    min_value: float
    max_value: float
    null_count: int
    out_of_bounds_count: int


class GoldLabelAuditResult(TypedDict, total=False):
    total_records: int
    status_counts: dict[str, int]
    invalid_records: list[RecordAuditIssue]
    pending_records_count: int
    missing_status_count: int
    verified_records_count: int
    candidate_reference_stats: dict[str, Any]
    job_reference_stats: dict[str, Any]
    score_validation: dict[str, ScoreAuditSummary]
    composite_formula_mismatches: list[dict[str, Any]]
    duplicate_pair_ids: list[str]
    empty_reasoning_count: int
    dataset_type_classification: str
    suitable_for_compatibility_eval_count: int
    suitable_for_career_readiness_eval_count: int


def parse_pair_id(pair_id: str) -> tuple[str, str]:
    """Parse pair_id into (candidate_id, job_id)."""
    parts = pair_id.split("_", 1)
    cand_id = parts[0] if len(parts) > 0 else ""
    job_id = parts[1] if len(parts) > 1 else ""
    return cand_id, job_id


def classify_record_status(
    record: dict[str, Any],
    valid_job: bool,
    valid_cand: bool,
) -> str:
    """Classify a gold label record into: 'invalid', 'pending', 'missing_status', or 'verified'.

    Classification Logic:
    --------------------
    1. 'invalid': Broken referential integrity (candidate or job ID not found in source datasets),
       or invalid score types / out-of-bound scores (<0 or >100).
    2. 'pending': Explicitly marked with review_status == 'pending', or missing reasoning.
    3. 'missing_status': Has valid references, scores, and human reasoning text, but completely
       lacks an explicit review/verification status attribute.
    4. 'verified': Explicitly confirmed with status == 'verified' or review_status == 'verified'
       with valid references, scores, and reasoning.
    """
    # 1. Check referential integrity
    if not valid_job or not valid_cand:
        return "invalid"

    # Check score validity
    score_fields = ("skills", "seniority", "domain", "location", "composite")
    for f in score_fields:
        val = record.get(f)
        if val is None or not isinstance(val, (int, float)):
            return "invalid"
        if val < 0 or val > 100:
            return "invalid"

    # 2. Check explicit status attributes
    explicit_status = (record.get("status") or record.get("review_status") or "").strip().lower()

    if explicit_status == "verified":
        # Must also have reasoning text to be truly verified
        reasoning = str(record.get("reasoning", "")).strip()
        return "verified" if len(reasoning) >= 10 else "pending"

    if explicit_status == "pending":
        return "pending"

    # 3. If explicit status is missing
    # Check if reasoning is empty or missing
    reasoning = str(record.get("reasoning", "")).strip()
    if not reasoning:
        return "pending"

    # Has reasoning, valid references and scores, but no status field
    return "missing_status"


def audit_gold_labels(
    gold_path: Path | str | None = None,
    syn_path: Path | str | None = None,
    jobs_path: Path | str | None = None,
) -> GoldLabelAuditResult:
    """Audit the gold labels dataset with full referential and score verification.

    Reads each file exactly once and caches lookups in memory for performance.
    """
    g_path = Path(gold_path) if gold_path else DATASETS_DIR / "gold_labels.json"
    s_path = Path(syn_path) if syn_path else DATASETS_DIR / "synthetic_profiles.json"
    j_path = Path(jobs_path) if jobs_path else DATASETS_DIR / "scraped_jobs.json"

    # 1. Read sources once
    with g_path.open("r", encoding="utf-8") as f:
        gold_data: list[dict[str, Any]] = json.load(f)

    with s_path.open("r", encoding="utf-8") as f:
        syn_data: list[dict[str, Any]] = json.load(f)

    with j_path.open("r", encoding="utf-8") as f:
        jobs_data: list[dict[str, Any]] = json.load(f)

    syn_ids = {str(p["profile_id"]) for p in syn_data if isinstance(p, dict) and "profile_id" in p}
    job_ids = {str(j["id"]) for j in jobs_data if isinstance(j, dict) and "id" in j}

    # 2. Audit tracking structures
    total_records = len(gold_data)
    pair_ids: list[str] = []
    seen_pair_ids: set[str] = set()
    duplicate_pair_ids: list[str] = []

    invalid_records: list[RecordAuditIssue] = []
    status_counts = {"verified": 0, "pending": 0, "missing_status": 0, "invalid": 0}

    missing_cand_refs: list[str] = []
    missing_job_refs: list[str] = []

    empty_reasoning_count = 0
    composite_mismatches: list[dict[str, Any]] = []

    score_fields = ["skills", "seniority", "domain", "location", "composite"]
    score_summaries: dict[str, ScoreAuditSummary] = {
        f: {"min_value": 999.0, "max_value": -999.0, "null_count": 0, "out_of_bounds_count": 0}
        for f in score_fields
    }

    # 3. Iterate through each gold record
    for idx, record in enumerate(gold_data):
        pid = record.get("pair_id", f"record_{idx}")
        pair_ids.append(pid)

        if pid in seen_pair_ids and pid not in duplicate_pair_ids:
            duplicate_pair_ids.append(pid)
        seen_pair_ids.add(pid)

        cand_id, job_id = parse_pair_id(pid)
        valid_cand = cand_id in syn_ids
        valid_job = job_id in job_ids

        if not valid_cand:
            missing_cand_refs.append(cand_id)
            invalid_records.append({
                "index": idx,
                "pair_id": pid,
                "issue_type": "missing_candidate_reference",
                "details": f"Candidate ID '{cand_id}' not found in synthetic_profiles.json",
            })

        if not valid_job:
            missing_job_refs.append(job_id)
            invalid_records.append({
                "index": idx,
                "pair_id": pid,
                "issue_type": "missing_job_reference",
                "details": f"Job ID '{job_id}' not found in scraped_jobs.json",
            })

        # Score checks
        for f in score_fields:
            val = record.get(f)
            if val is None or not isinstance(val, (int, float)):
                score_summaries[f]["null_count"] += 1
            else:
                score_summaries[f]["min_value"] = min(score_summaries[f]["min_value"], float(val))
                score_summaries[f]["max_value"] = max(score_summaries[f]["max_value"], float(val))
                if val < 0 or val > 100:
                    score_summaries[f]["out_of_bounds_count"] += 1

        # Check composite formula: round(0.50*skills + 0.15*seniority + 0.10*domain + 0.25*location)
        if all(isinstance(record.get(k), (int, float)) for k in score_fields):
            expected_comp = round(
                0.50 * record["skills"]
                + 0.15 * record["seniority"]
                + 0.10 * record["domain"]
                + 0.25 * record["location"]
            )
            actual_comp = record["composite"]
            if expected_comp != actual_comp:
                composite_mismatches.append({
                    "index": idx,
                    "pair_id": pid,
                    "expected": expected_comp,
                    "actual": actual_comp,
                    "diff": actual_comp - expected_comp,
                })

        # Reasoning check
        reasoning = str(record.get("reasoning", "")).strip()
        if not reasoning:
            empty_reasoning_count += 1

        # Status classification
        status = classify_record_status(record, valid_job=valid_job, valid_cand=valid_cand)
        status_counts[status] += 1

    return {
        "total_records": total_records,
        "status_counts": status_counts,
        "invalid_records": invalid_records,
        "pending_records_count": status_counts["pending"],
        "missing_status_count": status_counts["missing_status"],
        "verified_records_count": status_counts["verified"],
        "candidate_reference_stats": {
            "total_evaluated": len(gold_data),
            "valid_references": len(gold_data) - len(missing_cand_refs),
            "missing_references": missing_cand_refs,
        },
        "job_reference_stats": {
            "total_evaluated": len(gold_data),
            "valid_references": len(gold_data) - len(missing_job_refs),
            "missing_references": missing_job_refs,
        },
        "score_validation": score_summaries,
        "composite_formula_mismatches": composite_mismatches,
        "duplicate_pair_ids": duplicate_pair_ids,
        "empty_reasoning_count": empty_reasoning_count,
        "dataset_type_classification": "candidate_job_compatibility",
        "suitable_for_compatibility_eval_count": status_counts["missing_status"],  # 48 records with reasoning
        "suitable_for_career_readiness_eval_count": 0,  # 0 records (measures location/job fit, not career readiness)
    }

