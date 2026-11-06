"""Unit and integration tests for Road2Hire External Resume-Job Dataset Integration.

Validates:
1. External dataset loaders and JSON parsers.
2. Candidate CV adapter (schema v1.1.0, privacy enforcement, ESCO normalization).
3. Job posting adapter (ESCO grounding, unresolvable title handling, skill normalization).
4. Referential integrity and score validator.
5. External compatibility benchmark metrics (Pearson r, Spearman rho, MAE, RMSE).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from AI.Candidate_Profile.profile_schema import SCHEMA_VERSION
from AI.Dataset_Preparation.external_candidate_adapter import (
    adapt_external_cv_to_candidate_profile,
)
from AI.Dataset_Preparation.external_compatibility_benchmark import (
    BenchmarkMetrics,
    ExternalCompatibilityBenchmark,
    compute_correlation_metrics,
)
from AI.Dataset_Preparation.external_dataset_loader import (
    load_external_cvs_records,
    load_external_jobs_records,
    load_external_matches_records,
    safe_parse_json_list,
    stream_external_cvs,
    stream_external_jobs,
    stream_external_matches,
)
from AI.Dataset_Preparation.external_dataset_validator import (
    ExternalDatasetValidator,
    ValidationReport,
)
from AI.Dataset_Preparation.external_occupation_adapter import (
    adapt_external_job_to_occupation,
)
from AI.Skill_Extraction.esco_taxonomy import ESCOTaxonomy


# ---------------------------------------------------------------------------
# 1. Loader & JSON Parser Tests
# ---------------------------------------------------------------------------

def test_safe_parse_json_list() -> None:
    # Valid JSON string
    assert safe_parse_json_list('["Python", "Pandas", "SQL"]') == ["Python", "Pandas", "SQL"]
    # List object
    assert safe_parse_json_list(["Java", "Kotlin"]) == ["Java", "Kotlin"]
    # Comma-separated string fallback
    assert safe_parse_json_list("Docker, Kubernetes, AWS") == ["Docker", "Kubernetes", "AWS"]
    # Empty / None / Whitespace
    assert safe_parse_json_list(None) == []
    assert safe_parse_json_list("") == []
    assert safe_parse_json_list("   ") == []


def test_stream_loaders_with_temp_files(tmp_path: Path) -> None:
    # Create small mock CSVs using pandas to ensure standard CSV formatting
    import pandas as pd

    cv_df = pd.DataFrame([{
        "candidate_id": "cand_001",
        "source_row": 0,
        "target_position": "Python Developer",
        "resume_text": "Experienced developer",
        "clean_skills": '["Python"]',
        "clean_skills_json": '["Python", "SQL"]',
        "education_text": "B.Tech CS 2020",
        "experience_text": "Software Eng 2020-2023",
        "years_experience": 3.0,
        "inferred_category": "INFORMATION-TECHNOLOGY",
        "embedding": "[0.1]",
    }])
    cv_csv = tmp_path / "cv.csv"
    cv_df.to_csv(cv_csv, index=False)

    job_df = pd.DataFrame([{
        "job_id": 101,
        "job_title": "Software Engineer",
        "category": "IT",
        "job_description": "Job overview",
        "job_text": "text",
        "clean_skills": '["Python"]',
        "clean_skills_json": '["Python", "Git"]',
        "education_text": "Bachelors required",
        "years_required": 2.0,
        "embedding": "[0.1]",
    }])
    job_csv = tmp_path / "job.csv"
    job_df.to_csv(job_csv, index=False)

    match_df = pd.DataFrame([{
        "candidate_id": "cand_001",
        "job_id": 101,
        "final_score": 0.72,
        "raw_score": 0.61,
        "label_strength": "strong_positive",
        "semantic_score": 0.85,
        "skill_score": 0.60,
        "position_score": 0.80,
        "category_score": 1.0,
        "experience_score": 0.75,
        "education_score": 0.90,
        "candidate_rank": 1,
        "candidate_rank_pct": 0.01,
    }])
    match_csv = tmp_path / "matches.csv"
    match_df.to_csv(match_csv, index=False)

    cv_records = list(stream_external_cvs(cv_csv))
    assert len(cv_records) == 1
    assert cv_records[0]["candidate_id"] == "cand_001"
    assert cv_records[0]["skills_list"] == ["Python", "SQL"]

    job_records = list(stream_external_jobs(job_csv))
    assert len(job_records) == 1
    assert job_records[0]["job_id"] == "101"
    assert job_records[0]["skills_list"] == ["Python", "Git"]

    match_records = list(stream_external_matches(match_csv))
    assert len(match_records) == 1
    assert match_records[0]["candidate_id"] == "cand_001"
    assert match_records[0]["job_id"] == "101"
    assert float(match_records[0]["final_score"]) == 0.72


# ---------------------------------------------------------------------------
# 2. Candidate Adapter Tests
# ---------------------------------------------------------------------------

def test_adapt_external_cv_to_candidate_profile() -> None:
    mock_row = {
        "candidate_id": "cand_99999",
        "target_position": "Data Scientist",
        "resume_text": "Experienced Data Scientist with machine learning expertise.\nWorked at Tech Corp.",
        "clean_skills_json": '["Python", "Machine Learning", "UnmappedSkillXYZ"]',
        "education_text": "Master of Science in Computer Science | Stanford University | 2018 - 2020",
        "experience_text": "Data Scientist at Tech Corp | 2020 - Present | Built recommendation models",
        "years_experience": 4.5,
        "inferred_category": "INFORMATION-TECHNOLOGY",
    }

    profile = adapt_external_cv_to_candidate_profile(mock_row, taxonomy=None)

    # Conforms to schema
    assert profile["schema_version"] == SCHEMA_VERSION
    assert profile["source_file"] == "Datasets/External/Job_Resume_Matching/cv.csv#cand_99999"

    # Candidate privacy: name is strictly 'Not provided'
    assert profile["candidate"]["name"] == "Not provided"
    assert profile["candidate"]["email"] is None

    # Metadata preserves provenance
    assert profile["metadata"]["original_candidate_id"] == "cand_99999"
    assert profile["metadata"]["target_position"] == "Data Scientist"
    assert profile["metadata"]["years_experience"] == 4.5
    assert profile["metadata"]["inferred_category"] == "INFORMATION-TECHNOLOGY"

    # Skills check
    assert len(profile["skills"]) == 3
    skill_names = [s["skill"] for s in profile["skills"]]
    assert "Python" in skill_names
    assert "Machine Learning" in skill_names

    # Education parsed
    assert len(profile["education"]) >= 1
    assert profile["education"][0]["academic_level"] == "Master" or profile["education"][0]["raw_text"] != ""

    # Experience parsed
    assert len(profile["experience"]) >= 1
    assert profile["experience"][0]["raw_text"] != ""


# ---------------------------------------------------------------------------
# 3. Occupation Adapter Tests
# ---------------------------------------------------------------------------

def test_adapt_external_job_to_occupation() -> None:
    mock_job = {
        "job_id": 402,
        "job_title": "Software Developer",
        "category": "IT",
        "job_description": "We are seeking a Software Developer to develop scalable backend systems.",
        "clean_skills_json": '["Python", "Docker"]',
        "education_text": "Bachelor's degree in Computer Science",
        "years_required": 3.0,
    }

    class MockResolver:
        def resolve(self, title: str) -> tuple[str, str] | None:
            if "developer" in title.lower():
                return ("http://data.europa.eu/esco/occupation/mock_dev_uri", "software developer")
            return None

    # With resolver
    occ = adapt_external_job_to_occupation(mock_job, taxonomy=None, resolver=MockResolver())
    assert occ["job_id"] == "402"
    assert occ["is_esco_grounded"] is True
    assert occ["esco_uri"] == "http://data.europa.eu/esco/occupation/mock_dev_uri"
    assert occ["esco_preferred_label"] == "software developer"
    assert occ["years_required"] == 3.0
    assert occ["total_required_skills"] == 2

    # Without resolver or unresolvable title
    unresolvable_job = dict(mock_job)
    unresolvable_job["job_title"] = "Chief Happiness Coordinator"
    occ_unresolved = adapt_external_job_to_occupation(unresolvable_job, taxonomy=None, resolver=MockResolver())
    assert occ_unresolved["is_esco_grounded"] is False
    assert occ_unresolved["esco_uri"] is None
    assert occ_unresolved["esco_preferred_label"] is None


# ---------------------------------------------------------------------------
# 4. Validator Tests
# ---------------------------------------------------------------------------

def test_validator_raw_and_output_checks(tmp_path: Path) -> None:
    validator = ExternalDatasetValidator(
        expected_cv_count=1,
        expected_job_count=1,
        expected_match_count=1,
    )

    cv_p = tmp_path / "cv.csv"
    job_p = tmp_path / "job.csv"
    match_p = tmp_path / "matches.csv"

    cv_p.write_text("candidate_id,years_experience\ncand_1,3.0\n", encoding="utf-8")
    job_p.write_text("job_id,job_title,category\n10,Dev,IT\n", encoding="utf-8")
    match_p.write_text(
        "candidate_id,job_id,final_score,label_strength,semantic_score,skill_score\n"
        "cand_1,10,0.65,medium_positive,0.8,0.5\n",
        encoding="utf-8",
    )

    # Raw validation passes
    report = validator.validate_raw_csv_files(cv_p, job_p, match_p)
    assert report.is_valid is True
    assert len(report.errors) == 0
    assert report.metrics["total_candidates"] == 1
    assert report.metrics["total_jobs"] == 1
    assert report.metrics["total_matches"] == 1

    # Referential integrity failure test
    bad_match_p = tmp_path / "bad_matches.csv"
    bad_match_p.write_text(
        "candidate_id,job_id,final_score,label_strength,semantic_score,skill_score\n"
        "cand_999,10,0.65,medium_positive,0.8,0.5\n",
        encoding="utf-8",
    )
    bad_report = validator.validate_raw_csv_files(cv_p, job_p, bad_match_p)
    assert bad_report.is_valid is False
    assert any("Referential integrity violation" in err for err in bad_report.errors)

    # Processed JSONL output validation
    c_jsonl = tmp_path / "candidates.jsonl"
    j_jsonl = tmp_path / "jobs.jsonl"
    p_jsonl = tmp_path / "pairs.jsonl"

    c_jsonl.write_text(json.dumps({"metadata": {"original_candidate_id": "cand_1"}}) + "\n", encoding="utf-8")
    j_jsonl.write_text(json.dumps({"job_id": "10", "job_title": "Dev"}) + "\n", encoding="utf-8")
    p_jsonl.write_text(json.dumps({"candidate_id": "cand_1", "job_id": "10", "final_score": 0.65}) + "\n", encoding="utf-8")

    out_report = validator.validate_processed_outputs(c_jsonl, j_jsonl, p_jsonl)
    assert out_report.is_valid is True
    assert out_report.metrics["processed_candidates_count"] == 1


# ---------------------------------------------------------------------------
# 5. Benchmark Metrics Tests
# ---------------------------------------------------------------------------

def test_compute_correlation_metrics() -> None:
    # Perfect linear correlation
    y_true = [0.1, 0.2, 0.3, 0.4, 0.5]
    y_pred = [0.1, 0.2, 0.3, 0.4, 0.5]
    res = compute_correlation_metrics(y_true, y_pred)
    assert res.pearson_r == 1.0
    assert res.spearman_rho == 1.0
    assert res.mae == 0.0
    assert res.rmse == 0.0

    # Inverse correlation
    y_inv = [0.5, 0.4, 0.3, 0.2, 0.1]
    res_inv = compute_correlation_metrics(y_true, y_inv)
    assert res_inv.pearson_r == -1.0
    assert res_inv.spearman_rho == -1.0

    # Small sample edge case
    res_small = compute_correlation_metrics([0.5], [0.5])
    assert res_small.sample_size == 1


def test_external_compatibility_benchmark_evaluation() -> None:
    bench = ExternalCompatibilityBenchmark()
    mock_records = [
        {"candidate_id": "c1", "job_id": "j1", "category": "IT", "label_strength": "strong_positive", "final_score": 0.75, "predicted_score": 0.70},
        {"candidate_id": "c2", "job_id": "j2", "category": "IT", "label_strength": "strong_positive", "final_score": 0.60, "predicted_score": 0.58},
        {"candidate_id": "c3", "job_id": "j3", "category": "IT", "label_strength": "medium_positive", "final_score": 0.50, "predicted_score": 0.52},
        {"candidate_id": "c4", "job_id": "j4", "category": "IT", "label_strength": "medium_positive", "final_score": 0.45, "predicted_score": 0.40},
        {"candidate_id": "c5", "job_id": "j5", "category": "IT", "label_strength": "weak_positive", "final_score": 0.40, "predicted_score": 0.38},
    ]

    eval_result = bench.evaluate_predictions(mock_records)
    assert "overall" in eval_result
    assert eval_result["overall"]["sample_size"] == 5
    assert eval_result["overall"]["pearson_r"] > 0.95
    assert "by_category" in eval_result
    assert "IT" in eval_result["by_category"]
    assert "evaluation_note" in eval_result
