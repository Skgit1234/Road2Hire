"""Dataset Inventory and Streaming Utilities for Road2Hire M4.2.

Provides inspection, validation, and streaming access to raw datasets in Datasets/:
- master_resumes.jsonl
- scraped_jobs.json
- synthetic_profiles.json
- gold_labels.json
- ESCO & O*NET mappings
- ESCO raw taxonomy CSVs

Operates strictly in read-only mode without mutating raw data.
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any, Generator

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASETS_DIR = PROJECT_ROOT / "Datasets"


def get_datasets_dir() -> Path:
    """Return the resolved path to the Datasets directory."""
    return DATASETS_DIR


def get_dataset_inventory() -> dict[str, dict[str, Any]]:
    """Scan and return an inventory of all available datasets with metadata."""
    base = get_datasets_dir()

    inventory: dict[str, dict[str, Any]] = {}

    targets = {
        "master_resumes": base / "master_resumes.jsonl",
        "scraped_jobs": base / "scraped_jobs.json",
        "synthetic_profiles": base / "synthetic_profiles.json",
        "gold_labels": base / "gold_labels.json",
        "esco_skill_mapping": base / "ESCO_ONET" / "Mappings" / "ESCO_Skill_Mapping.csv",
        "onet_skill_mapping": base / "ESCO_ONET" / "Mappings" / "ONET_Skill_Mapping.csv",
        "esco_occupations": base / "Skill_Taxonomy" / "Raw" / "ESCO" / "occupations_en.csv",
        "esco_skills": base / "Skill_Taxonomy" / "Raw" / "ESCO" / "skills_en.csv",
        "esco_occupation_skill_relations": (
            base / "Skill_Taxonomy" / "Raw" / "ESCO" / "occupationSkillRelations_en.csv"
        ),
        "skill_taxonomy_processed": base / "Skill_Taxonomy" / "Processed" / "Skill_Taxonomy.csv",
    }

    for key, path in targets.items():
        if path.exists():
            size_bytes = path.stat().st_size
            inventory[key] = {
                "name": key,
                "path": str(path),
                "relative_path": str(path.relative_to(PROJECT_ROOT)),
                "exists": True,
                "size_bytes": size_bytes,
                "size_mb": round(size_bytes / (1024 * 1024), 2),
                "format": path.suffix.lower(),
            }
        else:
            inventory[key] = {
                "name": key,
                "path": str(path),
                "relative_path": str(path.relative_to(PROJECT_ROOT)),
                "exists": False,
                "size_bytes": 0,
                "size_mb": 0.0,
                "format": path.suffix.lower(),
            }

    return inventory


# ---------------------------------------------------------------------------
# Lazy Streaming Iterators (Memory Safe)
# ---------------------------------------------------------------------------

def stream_master_resumes(
    limit: int | None = None,
) -> Generator[dict[str, Any], None, None]:
    """Stream raw JSON records from master_resumes.jsonl.

    Parameters
    ----------
    limit:
        Optional maximum number of records to yield.
    """
    path = get_datasets_dir() / "master_resumes.jsonl"
    if not path.exists():
        logger.warning("master_resumes.jsonl not found at %s", path)
        return

    count = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            try:
                record = json.loads(line_str)
                yield record
                count += 1
                if limit is not None and count >= limit:
                    break
            except json.JSONDecodeError as err:
                logger.warning("Failed to decode JSON line: %s", err)
                continue


def load_scraped_jobs(
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Load job records from scraped_jobs.json."""
    path = get_datasets_dir() / "scraped_jobs.json"
    if not path.exists():
        logger.warning("scraped_jobs.json not found at %s", path)
        return []

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
        if isinstance(data, list):
            return data[:limit] if limit else data
        return []


def load_synthetic_profiles(
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Load synthetic candidate profiles from synthetic_profiles.json."""
    path = get_datasets_dir() / "synthetic_profiles.json"
    if not path.exists():
        logger.warning("synthetic_profiles.json not found at %s", path)
        return []

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
        if isinstance(data, list):
            return data[:limit] if limit else data
        return []


def load_gold_labels() -> list[dict[str, Any]]:
    """Load ground-truth annotated pairs from gold_labels.json."""
    path = get_datasets_dir() / "gold_labels.json"
    if not path.exists():
        logger.warning("gold_labels.json not found at %s", path)
        return []

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
        return data if isinstance(data, list) else []


def get_gold_label_index() -> dict[str, dict[str, Any]]:
    """Index gold labels by pair_id for O(1) lookup."""
    labels = load_gold_labels()
    return {
        item["pair_id"]: item
        for item in labels
        if isinstance(item, dict) and "pair_id" in item
    }

