"""Dataset Loader for Career Readiness Model Training (M4.4).

Loads and sanitizes candidate evidence from:
Datasets/Processed/readiness_annotation.xlsx

Enforces strict leakage prevention:
- Excludes all unlabeled / withheld records (N=29).
- Excludes candidate IDs, annotation IDs, and pair IDs.
- Excludes human annotation sub-ratings (Cols 9-12).
- Excludes key_evidence_summary (Col 15) and annotation_notes (Col 18).
- Excludes M3 skill coverage scores and gold compatibility labels.
- Validates that labeled instances have zero duplicate evidence profiles.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import openpyxl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_XLSX_PATH = PROJECT_ROOT / "Datasets" / "Processed" / "readiness_annotation.xlsx"

VALID_CLASSES = {"Not Ready", "Developing", "Job Ready"}
VALID_REVIEWER_STATUSES = {
    "Draft",
    "Reviewed",
    "Verified",
    "Disputed",
    "Flagged_Insufficient_Evidence",
}
SHAP_BACKGROUND_STATUSES = {"Reviewed", "Verified"}
ANNOTATION_HEADERS = [
    "annotation_id",
    "candidate_id",
    "target_occupation_title",
    "target_occupation_uri",
    "skills",
    "experience_summary",
    "projects_summary",
    "education_summary",
    "essential_skill_proficiency",
    "work_experience_relevance",
    "practical_application_evidence",
    "education_relevance",
    "readiness_label",
    "confidence",
    "key_evidence_summary",
    "annotator_id",
    "reviewer_status",
    "annotation_notes",
]


@dataclass(frozen=True)
class ReadinessRawRecord:
    """Sanitized raw evidence representation for a single candidate."""

    row_index: int
    target_occupation_title: str
    skills_text: str
    experience_text: str
    projects_text: str
    education_text: str
    readiness_label: str


@dataclass(frozen=True)
class ReadinessDataset:
    """Sanitized dataset split ready for feature extraction and training."""

    records: list[ReadinessRawRecord]
    raw_evidence: list[dict[str, str]]
    y: np.ndarray
    classes: list[str]
    unlabeled_count: int
    total_rows_inspected: int


def load_readiness_dataset(
    xlsx_path: Path | str = DEFAULT_XLSX_PATH,
) -> ReadinessDataset:
    """Load and validate the labeled career readiness dataset from Excel."""
    path = Path(xlsx_path)
    if not path.exists():
        raise FileNotFoundError(f"Annotation spreadsheet not found at {path}")

    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active

    records: list[ReadinessRawRecord] = []
    raw_evidence: list[dict[str, str]] = []
    y_labels: list[str] = []
    unlabeled_count = 0
    total_inspected = 0
    seen_evidence_hashes: set[tuple[str, str, str, str]] = set()

    for r in range(2, ws.max_row + 1):
        total_inspected += 1
        label = ws.cell(row=r, column=13).value

        # Phase 1 requirement: Exclude unlabeled / withheld records
        if label is None or str(label).strip() == "" or str(label).strip().lower() == "none":
            unlabeled_count += 1
            continue

        label_str = str(label).strip()
        if label_str not in VALID_CLASSES:
            raise ValueError(f"Invalid readiness label at row {r}: '{label_str}'")

        # Extract only permitted raw evidence fields
        target_occ = str(ws.cell(row=r, column=3).value or "").strip()
        skills = str(ws.cell(row=r, column=5).value or "").strip()
        experience = str(ws.cell(row=r, column=6).value or "").strip()
        projects = str(ws.cell(row=r, column=7).value or "").strip()
        education = str(ws.cell(row=r, column=8).value or "").strip()

        # Phase 1 requirement: Ensure no identical duplicate evidence profiles exist in labeled pool
        evidence_key = (skills, experience, projects, education)
        if evidence_key in seen_evidence_hashes:
            raise ValueError(
                f"Duplicate evidence profile detected at row {r} in labeled pool. "
                "All duplicate profiles must be withheld."
            )
        seen_evidence_hashes.add(evidence_key)

        record = ReadinessRawRecord(
            row_index=r,
            target_occupation_title=target_occ,
            skills_text=skills,
            experience_text=experience,
            projects_text=projects,
            education_text=education,
            readiness_label=label_str,
        )
        records.append(record)
        raw_evidence.append({
            "target_occupation_title": target_occ,
            "skills_text": skills,
            "experience_text": experience,
            "projects_text": projects,
            "education_text": education,
        })
        y_labels.append(label_str)

    wb.close()

    # Integrity assertions
    if len(records) != 71:
        raise ValueError(f"Expected exactly 71 labeled records, got {len(records)}")
    if unlabeled_count != 29:
        raise ValueError(f"Expected exactly 29 unlabeled records, got {unlabeled_count}")

    y_array = np.array(y_labels, dtype=object)
    classes = sorted(list(VALID_CLASSES))

    return ReadinessDataset(
        records=records,
        raw_evidence=raw_evidence,
        y=y_array,
        classes=classes,
        unlabeled_count=unlabeled_count,
        total_rows_inspected=total_inspected,
    )


def load_readiness_shap_background(
    xlsx_path: Path | str = DEFAULT_XLSX_PATH,
) -> list[dict[str, str]]:
    """Load only reviewed/verified, labeled evidence for SHAP references.

    This is deliberately separate from ``load_readiness_dataset`` so adding
    reviewer filtering for explainability cannot silently alter the persisted
    model's training data or prediction behavior.
    """
    path = Path(xlsx_path)
    if not path.exists():
        raise FileNotFoundError(f"Annotation spreadsheet not found at {path}")

    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    try:
        if "Readiness_Annotation" not in wb.sheetnames:
            raise ValueError("Workbook is missing the Readiness_Annotation worksheet")
        ws = wb["Readiness_Annotation"]
        headers = [ws.cell(row=1, column=col).value for col in range(1, 19)]
        if ws.max_row < 2 or ws.max_column != 18 or headers != ANNOTATION_HEADERS:
            raise ValueError("Readiness annotation workbook schema is invalid")

        background: list[dict[str, str]] = []
        for row in range(2, ws.max_row + 1):
            status = ws.cell(row=row, column=17).value
            status = status.strip() if isinstance(status, str) else ""
            if status not in VALID_REVIEWER_STATUSES:
                raise ValueError(f"Invalid reviewer status at row {row}")
            if status not in SHAP_BACKGROUND_STATUSES:
                continue

            label = ws.cell(row=row, column=13).value
            if not isinstance(label, str) or label.strip() not in VALID_CLASSES:
                raise ValueError(
                    f"Reviewed/verified row {row} must have a valid readiness label"
                )

            background.append(
                {
                    "target_occupation_title": str(
                        ws.cell(row=row, column=3).value or ""
                    ).strip(),
                    "skills_text": str(ws.cell(row=row, column=5).value or "").strip(),
                    "experience_text": str(
                        ws.cell(row=row, column=6).value or ""
                    ).strip(),
                    "projects_text": str(
                        ws.cell(row=row, column=7).value or ""
                    ).strip(),
                    "education_text": str(
                        ws.cell(row=row, column=8).value or ""
                    ).strip(),
                }
            )
    finally:
        wb.close()

    if not background:
        raise ValueError("No reviewed/verified labeled records are available for SHAP")
    return background
