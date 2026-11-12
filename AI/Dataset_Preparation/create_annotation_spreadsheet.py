"""Generate Excel Annotation Spreadsheet for Road2Hire M4.3.

Reads the 100 candidate-occupation records from:
Datasets/Processed/readiness_annotation_pilot.jsonl

Generates a fully-formatted, styled Excel workbook:
Datasets/Processed/readiness_annotation.xlsx

Features:
- Exactly 18 standardized columns (metadata, candidate evidence, blank annotation fields).
- Openpyxl data validation dropdowns for columns 9, 10, 11, 12, 13, 14, 17.
- Header row frozen (A2) with auto-filters enabled.
- Text wrapping, generous row heights, and styled headers.
- Visual highlighting on blank readiness labels (Column M) to clearly flag pending annotations.
- Full programmatic verification on the saved disk file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_JSONL_PATH = (
    PROJECT_ROOT / "Datasets" / "Processed" / "readiness_annotation_pilot.jsonl"
)
OUTPUT_XLSX_PATH = (
    PROJECT_ROOT / "Datasets" / "Processed" / "readiness_annotation.xlsx"
)

# Standardized column headers in exact order
COLUMNS = [
    ("annotation_id", 28, "center"),
    ("candidate_id", 15, "center"),
    ("target_occupation_title", 26, "left"),
    ("target_occupation_uri", 32, "left"),
    ("skills", 45, "left"),
    ("experience_summary", 55, "left"),
    ("projects_summary", 55, "left"),
    ("education_summary", 42, "left"),
    ("essential_skill_proficiency", 25, "center"),
    ("work_experience_relevance", 28, "center"),
    ("practical_application_evidence", 30, "center"),
    ("education_relevance", 24, "center"),
    ("readiness_label", 20, "center"),
    ("confidence", 16, "center"),
    ("key_evidence_summary", 48, "left"),
    ("annotator_id", 18, "center"),
    ("reviewer_status", 22, "center"),
    ("annotation_notes", 45, "left"),
]

# Dropdown options for data validation
DROPDOWNS = {
    # col_idx, col_letter, formula_string
    "essential_skill_proficiency": ("I", '"Insufficient,Foundational,Proficient"'),
    "work_experience_relevance": ("J", '"Irrelevant_or_None,Partial_or_Junior,Substantial_and_Direct"'),
    "practical_application_evidence": ("K", '"None_Observed,Academic_or_Demo_Projects,Production_or_EndToEnd_Systems"'),
    "education_relevance": ("L", '"Non_Technical,Related_Degree,Directly_Aligned_Degree,Not_Provided"'),
    "readiness_label": ("M", '"Not Ready,Developing,Job Ready"'),
    "confidence": ("N", '"High,Medium,Low"'),
    "reviewer_status": ("Q", '"Draft,Reviewed,Verified,Disputed,Flagged_Insufficient_Evidence"'),
}


def build_annotation_spreadsheet() -> Path:
    """Create and save readiness_annotation.xlsx from readiness_annotation_pilot.jsonl."""
    if not INPUT_JSONL_PATH.exists():
        raise FileNotFoundError(f"Source JSONL not found at {INPUT_JSONL_PATH}")

    # Load 100 JSONL records
    records: list[dict[str, Any]] = []
    with INPUT_JSONL_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if line_str:
                records.append(json.loads(line_str))

    if len(records) != 100:
        raise ValueError(f"Expected exactly 100 records, got {len(records)}")

    # Initialize Workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Readiness_Annotation"

    # Styling definitions
    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_data = Font(name="Calibri", size=10, color="000000")
    font_target_label = Font(name="Calibri", size=10, bold=True, color="1F497D")

    # Header section fills
    fill_meta_header = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")       # Dark Navy
    fill_evidence_header = PatternFill(start_color="2E4053", end_color="2E4053", fill_type="solid")   # Slate Steel
    fill_eval_header = PatternFill(start_color="1A5276", end_color="1A5276", fill_type="solid")       # Deep Blue
    fill_target_header = PatternFill(start_color="B9770E", end_color="B9770E", fill_type="solid")     # Amber Gold
    fill_admin_header = PatternFill(start_color="34495E", end_color="34495E", fill_type="solid")      # Charcoal

    # Data row fills
    fill_evidence_col = PatternFill(start_color="F8F9F9", end_color="F8F9F9", fill_type="solid")      # Very soft gray
    fill_pending_label = PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid")     # Soft amber highlight

    thin_border_side = Side(border_style="thin", color="D5D8DC")
    thin_border = Border(
        left=thin_border_side,
        right=thin_border_side,
        top=thin_border_side,
        bottom=thin_border_side,
    )
    header_border = Border(
        left=thin_border_side,
        right=thin_border_side,
        top=thin_border_side,
        bottom=Side(border_style="medium", color="1B2631"),
    )

    # 1. Write Header Row
    ws.row_dimensions[1].height = 34
    for col_idx, (col_name, col_width, _) in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.font = font_header
        cell.border = header_border
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        # Apply category fill to header
        if col_idx in (1, 2, 3, 4):
            cell.fill = fill_meta_header
        elif col_idx in (5, 6, 7, 8):
            cell.fill = fill_evidence_header
        elif col_idx in (9, 10, 11, 12, 14, 15):
            cell.fill = fill_eval_header
        elif col_idx == 13:
            cell.fill = fill_target_header  # Highlight readiness_label column header
        else:
            cell.fill = fill_admin_header

        # Set column width
        col_letter = openpyxl.utils.get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = col_width

    # 2. Populate 100 Data Rows
    for row_idx, rec in enumerate(records, start=2):
        ws.row_dimensions[row_idx].height = 68  # Generous multi-line height

        ev = rec.get("evidence", {})
        cps = ev.get("candidate_profile_summary", {})

        # Format skills
        raw_skills = cps.get("skills", [])
        skills_str = ", ".join(raw_skills) if raw_skills else ""

        # Format experience
        raw_exps = cps.get("experience_summary", [])
        exp_str = "\n".join(f"• {e}" for e in raw_exps) if raw_exps else ""

        # Format projects
        raw_projs = cps.get("projects_summary", [])
        proj_str = "\n".join(f"• {p}" for p in raw_projs) if raw_projs else ""

        # Format education
        raw_edus = cps.get("education_summary", [])
        edu_str = "\n".join(f"• {ed}" for ed in raw_edus) if raw_edus else ""

        row_values = [
            rec.get("annotation_id", ""),
            rec.get("candidate_id", ""),
            rec.get("target_occupation_title", ""),
            rec.get("target_occupation_uri", ""),
            skills_str,
            exp_str,
            proj_str,
            edu_str,
            None,  # 9. essential_skill_proficiency (BLANK)
            None,  # 10. work_experience_relevance (BLANK)
            None,  # 11. practical_application_evidence (BLANK)
            None,  # 12. education_relevance (BLANK)
            None,  # 13. readiness_label (BLANK)
            None,  # 14. confidence (BLANK)
            None,  # 15. key_evidence_summary (BLANK)
            None,  # 16. annotator_id (BLANK)
            None,  # 17. reviewer_status (BLANK)
            None,  # 18. annotation_notes (BLANK)
        ]

        for col_idx, val in enumerate(row_values, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.font = font_data
            cell.border = thin_border
            _, _, align_h = COLUMNS[col_idx - 1]
            cell.alignment = Alignment(horizontal=align_h, vertical="top", wrap_text=True)

            # Soft background for evidence columns to enhance readability
            if col_idx in (5, 6, 7, 8):
                cell.fill = fill_evidence_col

            # Highlight blank readiness label cells so pending work is instantly visible
            if col_idx == 13:
                cell.fill = fill_pending_label
                cell.font = font_target_label

    # 3. Configure Excel Data Validation Dropdowns
    for field_name, (col_letter, formula_str) in DROPDOWNS.items():
        dv = DataValidation(
            type="list",
            formula1=formula_str,
            allow_blank=True,
            showDropDown=True,
            showErrorMessage=True,
            errorTitle="Invalid Selection",
            error=f"Please choose an approved option from the {field_name} dropdown.",
        )
        ws.add_data_validation(dv)
        cell_range = f"{col_letter}2:{col_letter}101"
        dv.add(cell_range)

    # 4. Conditional Formatting for Blank Readiness Label (Column M)
    # Applies soft amber fill when empty to flag pending manual annotation
    ws.conditional_formatting.add(
        "M2:M101",
        CellIsRule(
            operator="equal",
            formula=['""'],
            stopIfTrue=True,
            fill=fill_pending_label,
        ),
    )

    # 5. Enable Frozen Pane and Auto-Filters
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = "A1:R101"

    # Save to disk
    OUTPUT_XLSX_PATH.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUTPUT_XLSX_PATH)
    return OUTPUT_XLSX_PATH


def verify_saved_spreadsheet(xlsx_path: Path | None = None) -> dict[str, Any]:
    """Reopen the saved workbook from disk and perform exhaustive quality checks."""
    target_path = xlsx_path or OUTPUT_XLSX_PATH
    if not target_path.exists():
        raise FileNotFoundError(f"Spreadsheet not found at {target_path}")

    # Load source JSONL for ground-truth comparison
    source_records: list[dict[str, Any]] = []
    with INPUT_JSONL_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                source_records.append(json.loads(line))

    wb = openpyxl.load_workbook(target_path)
    ws = wb.active

    results: dict[str, Any] = {
        "file_exists": True,
        "sheet_name": ws.title,
        "max_row": ws.max_row,
        "max_column": ws.max_column,
        "data_row_count": ws.max_row - 1,
        "header_row_matches": True,
        "annotation_ids_matched": 0,
        "candidate_ids_matched": 0,
        "occupation_titles_matched": 0,
        "occupation_uris_matched": 0,
        "evidence_preserved_count": 0,
        "blank_annotation_fields_verified": 0,
        "data_validations_count": len(ws.data_validations.dataValidation),
        "data_validations_details": [],
        "errors": [],
    }

    # 1. Header validation
    expected_headers = [col[0] for col in COLUMNS]
    actual_headers = [ws.cell(row=1, column=c).value for c in range(1, 19)]
    if actual_headers != expected_headers:
        results["header_row_matches"] = False
        results["errors"].append(f"Header mismatch. Expected {expected_headers}, got {actual_headers}")

    # 2. Data row count
    if ws.max_row != 101:
        results["errors"].append(f"Expected 101 total rows (1 header + 100 data), got {ws.max_row}")

    # 3. Row-by-row verification against JSONL
    for idx, rec in enumerate(source_records, start=2):
        row_ann_id = ws.cell(row=idx, column=1).value
        row_cand_id = ws.cell(row=idx, column=2).value
        row_occ_title = ws.cell(row=idx, column=3).value
        row_occ_uri = ws.cell(row=idx, column=4).value
        row_skills = ws.cell(row=idx, column=5).value
        row_exp = ws.cell(row=idx, column=6).value
        row_proj = ws.cell(row=idx, column=7).value
        row_edu = ws.cell(row=idx, column=8).value

        # Check metadata
        if row_ann_id == rec["annotation_id"]:
            results["annotation_ids_matched"] += 1
        else:
            results["errors"].append(f"Row {idx} annotation_id mismatch: {row_ann_id} vs {rec['annotation_id']}")

        if row_cand_id == rec["candidate_id"]:
            results["candidate_ids_matched"] += 1
        else:
            results["errors"].append(f"Row {idx} candidate_id mismatch: {row_cand_id} vs {rec['candidate_id']}")

        if row_occ_title == rec["target_occupation_title"]:
            results["occupation_titles_matched"] += 1
        else:
            results["errors"].append(f"Row {idx} title mismatch: {row_occ_title} vs {rec['target_occupation_title']}")

        if row_occ_uri == rec["target_occupation_uri"]:
            results["occupation_uris_matched"] += 1
        else:
            results["errors"].append(f"Row {idx} URI mismatch: {row_occ_uri} vs {rec['target_occupation_uri']}")

        # Check evidence preservation
        cps = rec["evidence"]["candidate_profile_summary"]
        skills_ok = (not cps.get("skills")) or bool(row_skills)
        exp_ok = (not cps.get("experience_summary")) or bool(row_exp)
        proj_ok = (not cps.get("projects_summary")) or bool(row_proj)
        edu_ok = (not cps.get("education_summary")) or bool(row_edu)
        if skills_ok and exp_ok and proj_ok and edu_ok:
            results["evidence_preserved_count"] += 1
        else:
            results["errors"].append(f"Row {idx} evidence fields incomplete")

        # Check that columns 9 to 18 are completely blank
        all_blank = True
        for col_idx in range(9, 19):
            val = ws.cell(row=idx, column=col_idx).value
            if val is not None and val != "":
                all_blank = False
                results["errors"].append(
                    f"Row {idx} column {col_idx} ({COLUMNS[col_idx-1][0]}) is not blank: {val}"
                )
        if all_blank:
            results["blank_annotation_fields_verified"] += 1

    # 4. Data validation inspection
    for dv in ws.data_validations.dataValidation:
        results["data_validations_details"].append({
            "type": dv.type,
            "formula1": dv.formula1,
            "sqref": str(dv.sqref),
        })

    if len(ws.data_validations.dataValidation) != len(DROPDOWNS):
        results["errors"].append(
            f"Expected {len(DROPDOWNS)} data validations, found {len(ws.data_validations.dataValidation)}"
        )

    # 5. Check freeze panes and auto filter
    if ws.freeze_panes != "A2":
        results["errors"].append(f"Expected freeze_panes 'A2', got {ws.freeze_panes}")
    if not ws.auto_filter.ref:
        results["errors"].append("Auto filter is not enabled")

    return results


if __name__ == "__main__":
    saved_path = build_annotation_spreadsheet()
    print(f"[DONE] Created spreadsheet: {saved_path}")
    audit = verify_saved_spreadsheet(saved_path)
    print(f"[DONE] Audit completed: {audit['data_row_count']} rows, {len(audit['errors'])} errors")
    if audit["errors"]:
        for e in audit["errors"][:5]:
            print("  ERROR:", e)
    else:
        print("[SUCCESS] All quality checks passed cleanly!")

