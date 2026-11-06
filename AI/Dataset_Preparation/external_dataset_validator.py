"""Dataset Validator for External Job-Resume Matching Benchmark.

Validates:
1. File existence and row counts.
2. Referential integrity between matches, candidates, and jobs (zero dangling foreign keys).
3. Primary key and composite pair uniqueness.
4. Numerical score bounds [0.0, 1.0] and categorical label distributions.
5. Schema conformity of adapted JSONL output files.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

VALID_LABEL_STRENGTHS = {"strong_positive", "medium_positive", "weak_positive"}


@dataclass
class ValidationReport:
    """Detailed dataset validation report."""

    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ExternalDatasetValidator:
    """Validator for external job-resume matching datasets."""

    def __init__(
        self,
        expected_cv_count: int | None = 9544,
        expected_job_count: int | None = 1167,
        expected_match_count: int | None = 122560,
    ) -> None:
        self.expected_cv_count = expected_cv_count
        self.expected_job_count = expected_job_count
        self.expected_match_count = expected_match_count

    def validate_raw_csv_files(
        self,
        cv_path: Path | str,
        job_path: Path | str,
        matches_path: Path | str,
    ) -> ValidationReport:
        """Validate raw input CSV files for counts, integrity, and score bounds."""
        report = ValidationReport()
        cv_p = Path(cv_path)
        job_p = Path(job_path)
        match_p = Path(matches_path)

        for p, label in [(cv_p, "cv.csv"), (job_p, "job.csv"), (match_p, "matches.csv")]:
            if not p.is_file():
                report.errors.append(f"Missing required input file: {label} at {p}")
                report.is_valid = False
                return report

        logger.info("Validating candidates in %s ...", cv_p.name)
        cv_df = pd.read_csv(cv_p, usecols=["candidate_id", "years_experience"], dtype={"candidate_id": str})
        cv_count = len(cv_df)
        cv_unique_ids = set(cv_df["candidate_id"].dropna())

        if self.expected_cv_count is not None and cv_count != self.expected_cv_count:
            report.warnings.append(
                f"CV row count ({cv_count}) differs from expected ({self.expected_cv_count})."
            )
        if len(cv_unique_ids) != cv_count:
            report.errors.append(
                f"Duplicate candidate_id found in {cv_p.name}: {cv_count - len(cv_unique_ids)} duplicates."
            )
            report.is_valid = False

        logger.info("Validating jobs in %s ...", job_p.name)
        job_df = pd.read_csv(job_p, usecols=["job_id", "job_title", "category"], dtype={"job_id": int})
        job_count = len(job_df)
        job_unique_ids = set(job_df["job_id"].astype(str).dropna())

        if self.expected_job_count is not None and job_count != self.expected_job_count:
            report.warnings.append(
                f"Job row count ({job_count}) differs from expected ({self.expected_job_count})."
            )
        if len(job_unique_ids) != job_count:
            report.errors.append(
                f"Duplicate job_id found in {job_p.name}: {job_count - len(job_unique_ids)} duplicates."
            )
            report.is_valid = False

        logger.info("Validating matches in %s ...", match_p.name)
        match_df = pd.read_csv(
            match_p,
            usecols=[
                "candidate_id",
                "job_id",
                "final_score",
                "label_strength",
                "semantic_score",
                "skill_score",
            ],
            dtype={"candidate_id": str, "job_id": int},
        )
        match_count = len(match_df)

        if self.expected_match_count is not None and match_count != self.expected_match_count:
            report.warnings.append(
                f"Matches row count ({match_count}) differs from expected ({self.expected_match_count})."
            )

        # Referential integrity check
        match_cand_ids = set(match_df["candidate_id"].dropna())
        dangling_cands = match_cand_ids - cv_unique_ids
        if dangling_cands:
            report.errors.append(
                f"Referential integrity violation: {len(dangling_cands)} candidate_ids in matches not in cv.csv."
            )
            report.is_valid = False

        match_job_ids = set(match_df["job_id"].astype(str).dropna())
        dangling_jobs = match_job_ids - job_unique_ids
        if dangling_jobs:
            report.errors.append(
                f"Referential integrity violation: {len(dangling_jobs)} job_ids in matches not in job.csv."
            )
            report.is_valid = False

        # Duplicate pair check
        pairs = match_df["candidate_id"] + "_" + match_df["job_id"].astype(str)
        if pairs.nunique() != match_count:
            report.errors.append(
                f"Duplicate (candidate_id, job_id) pairs found: {match_count - pairs.nunique()} duplicates."
            )
            report.is_valid = False

        # Score range and label checks
        min_final = float(match_df["final_score"].min())
        max_final = float(match_df["final_score"].max())
        if min_final < 0.0 or max_final > 1.0:
            report.errors.append(f"final_score out of [0, 1] bounds: min={min_final}, max={max_final}")
            report.is_valid = False

        labels_found = set(match_df["label_strength"].unique())
        invalid_labels = labels_found - VALID_LABEL_STRENGTHS
        if invalid_labels:
            report.errors.append(f"Invalid label_strength categories detected: {invalid_labels}")
            report.is_valid = False

        report.metrics = {
            "total_candidates": cv_count,
            "unique_candidate_ids": len(cv_unique_ids),
            "total_jobs": job_count,
            "unique_job_ids": len(job_unique_ids),
            "total_matches": match_count,
            "unique_matched_candidates": len(match_cand_ids),
            "unique_matched_jobs": len(match_job_ids),
            "unmatched_candidates": len(cv_unique_ids - match_cand_ids),
            "unmatched_jobs": len(job_unique_ids - match_job_ids),
            "final_score_min": min_final,
            "final_score_max": max_final,
            "final_score_mean": float(match_df["final_score"].mean()),
            "label_strength_counts": match_df["label_strength"].value_counts().to_dict(),
        }

        return report

    def validate_processed_outputs(
        self,
        candidates_jsonl: Path | str,
        jobs_jsonl: Path | str,
        pairs_jsonl: Path | str,
    ) -> ValidationReport:
        """Validate generated JSONL files for line formatting and schema validity."""
        report = ValidationReport()
        c_p = Path(candidates_jsonl)
        j_p = Path(jobs_jsonl)
        p_p = Path(pairs_jsonl)

        for p, label in [(c_p, "candidates"), (j_p, "jobs"), (p_p, "pairs")]:
            if not p.is_file():
                report.errors.append(f"Output file missing: {label} at {p}")
                report.is_valid = False
                return report

        # Candidate lines check
        cand_ids: set[str] = set()
        c_lines = 0
        with c_p.open("r", encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                c_lines += 1
                try:
                    data = json.loads(line)
                    cid = data.get("metadata", {}).get("original_candidate_id")
                    if not cid:
                        report.errors.append(f"Line {idx} in {c_p.name} missing original_candidate_id")
                        report.is_valid = False
                        break
                    cand_ids.add(cid)
                except Exception as e:
                    report.errors.append(f"Malformed JSON at line {idx} in {c_p.name}: {e}")
                    report.is_valid = False
                    break

        # Job lines check
        job_ids: set[str] = set()
        j_lines = 0
        with j_p.open("r", encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                j_lines += 1
                try:
                    data = json.loads(line)
                    jid = data.get("job_id")
                    if not jid:
                        report.errors.append(f"Line {idx} in {j_p.name} missing job_id")
                        report.is_valid = False
                        break
                    job_ids.add(str(jid))
                except Exception as e:
                    report.errors.append(f"Malformed JSON at line {idx} in {j_p.name}: {e}")
                    report.is_valid = False
                    break

        # Pair lines check
        pair_lines = 0
        with p_p.open("r", encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                pair_lines += 1
                try:
                    data = json.loads(line)
                    cid = data.get("candidate_id")
                    jid = str(data.get("job_id"))
                    if not cid or not jid:
                        report.errors.append(f"Line {idx} in {p_p.name} missing candidate_id or job_id")
                        report.is_valid = False
                        break
                    if cid not in cand_ids:
                        report.errors.append(f"Line {idx} pair references unknown candidate_id: {cid}")
                        report.is_valid = False
                        break
                    if jid not in job_ids:
                        report.errors.append(f"Line {idx} pair references unknown job_id: {jid}")
                        report.is_valid = False
                        break
                except Exception as e:
                    report.errors.append(f"Malformed JSON at line {idx} in {p_p.name}: {e}")
                    report.is_valid = False
                    break

        report.metrics = {
            "processed_candidates_count": c_lines,
            "processed_jobs_count": j_lines,
            "processed_pairs_count": pair_lines,
        }
        return report

