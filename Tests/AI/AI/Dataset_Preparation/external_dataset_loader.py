"""External Dataset Loader for Job-Resume Matching Benchmark.

Provides streaming and batch ingestion utilities for:
- cv.csv (candidate resumes, 9,544 rows)
- job.csv (job postings, 1,167 rows)
- matches.csv (candidate-job pairs, 122,560 rows)

Designed for memory efficiency with chunked reading and streaming iterators.
"""

from __future__ import annotations

import csv
import json
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def safe_parse_json_list(val: Any) -> list[str]:
    """Safely parse a JSON list string, list object, or comma-separated string.

    Returns a clean list of non-empty strings.
    """
    if val is None:
        return []
    if isinstance(val, (list, tuple, set)):
        return [str(item).strip() for item in val if str(item).strip()]
    if isinstance(val, (int, float)):
        if pd.isna(val):
            return []
        return [str(val).strip()]
    if isinstance(val, str):
        val_str = val.strip()
        if not val_str:
            return []
        if val_str.startswith("[") and val_str.endswith("]"):
            try:
                parsed = json.loads(val_str)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except (json.JSONDecodeError, ValueError):
                pass
        # Fallback to comma/newline split
        items = [s.strip() for s in val_str.replace("\n", ",").split(",") if s.strip()]
        return items
    return [str(val).strip()]


def stream_external_cvs(
    file_path: Path | str,
    chunk_size: int = 1000,
    limit: int | None = None,
) -> Iterator[dict[str, Any]]:
    """Stream candidate CV records chunk by chunk from cv.csv.

    Yields individual candidate row dictionaries.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Candidate file not found: {path}")

    yielded = 0
    # Use pandas read_csv with chunksize to handle multiline quoted text cleanly
    for chunk in pd.read_csv(path, chunksize=chunk_size, dtype={"candidate_id": str}):
        for record in chunk.to_dict(orient="records"):
            # Clean skills list
            record["skills_list"] = safe_parse_json_list(
                record.get("clean_skills_json") or record.get("clean_skills")
            )
            yield record
            yielded += 1
            if limit is not None and yielded >= limit:
                return


def stream_external_jobs(
    file_path: Path | str,
    chunk_size: int = 1000,
    limit: int | None = None,
) -> Iterator[dict[str, Any]]:
    """Stream job posting records chunk by chunk from job.csv.

    Yields individual job row dictionaries.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Job file not found: {path}")

    yielded = 0
    for chunk in pd.read_csv(path, chunksize=chunk_size, dtype={"job_id": int}):
        for record in chunk.to_dict(orient="records"):
            record["job_id"] = str(record["job_id"])
            record["skills_list"] = safe_parse_json_list(
                record.get("clean_skills_json") or record.get("clean_skills")
            )
            yield record
            yielded += 1
            if limit is not None and yielded >= limit:
                return


def stream_external_matches(
    file_path: Path | str,
    chunk_size: int = 5000,
    limit: int | None = None,
) -> Iterator[dict[str, Any]]:
    """Stream candidate-job matching records from matches.csv.

    Yields individual match row dictionaries.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Matches file not found: {path}")

    yielded = 0
    for chunk in pd.read_csv(
        path,
        chunksize=chunk_size,
        dtype={"candidate_id": str, "job_id": int},
    ):
        for record in chunk.to_dict(orient="records"):
            record["job_id"] = str(record["job_id"])
            yield record
            yielded += 1
            if limit is not None and yielded >= limit:
                return


def load_external_cvs_records(
    file_path: Path | str,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Load external CV records into memory as a list of dicts."""
    return list(stream_external_cvs(file_path, limit=limit))


def load_external_jobs_records(
    file_path: Path | str,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Load external job records into memory as a list of dicts."""
    return list(stream_external_jobs(file_path, limit=limit))


def load_external_matches_records(
    file_path: Path | str,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Load external match records into memory as a list of dicts."""
    return list(stream_external_matches(file_path, limit=limit))
