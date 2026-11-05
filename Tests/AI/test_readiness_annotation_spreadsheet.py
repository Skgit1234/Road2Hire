"""Unit and Integration Tests for Readiness Annotation Spreadsheet (M4.3).

Validates:
- Existence and structural integrity of Datasets/Processed/readiness_annotation.xlsx
- Exact row and column count (101 rows = 1 header + 100 data rows, 18 columns)
- Header names and order match specifications
- Candidate IDs, occupation titles, URIs, and annotation IDs match source JSONL
- Evidence fields preserved (skills, experience, projects, education)
- Dropdown data validations configured and mapped to cells
- Freeze panes and auto-filter active
- Quality validation of completed human readiness annotations
- Verification of the pristine pre-annotation backup workbook
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
import openpyxl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
XLSX_PATH = PROJECT_ROOT / "Datasets" / "Processed" / "readiness_annotation.xlsx"
BACKUP_PATH = PROJECT_ROOT / "Datasets" / "Processed" / "readiness_annotation_backup.xlsx"
JSONL_PATH = PROJECT_ROOT / "Datasets" / "Processed" / "readiness_annotation_pilot.jsonl"

EXPECTED_HEADERS = [
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

VALID_PROFICIENCY = {None, "Insufficient", "Foundational", "Proficient"}
VALID_EXP_RELEVANCE = {None, "Irrelevant_or_None", "Partial_or_Junior", "Substantial_and_Direct"}
VALID_PRACTICAL = {None, "None_Observed", "Academic_or_Demo_Projects", "Production_or_EndToEnd_Systems"}
VALID_EDU_RELEVANCE = {None, "Non_Technical", "Related_Degree", "Directly_Aligned_Degree", "Not_Provided"}
VALID_READINESS = {None, "Not Ready", "Developing", "Job Ready"}
VALID_CONFIDENCE = {None, "High", "Medium", "Low"}
VALID_REVIEWER_STATUS = {"Draft", "Reviewed", "Verified", "Disputed", "Flagged_Insufficient_Evidence"}


class TestReadinessAnnotationSpreadsheet:
    """Tests for the generated readiness_annotation.xlsx workbook."""

    @pytest.fixture(scope="module")
    def workbook(self):
        assert XLSX_PATH.exists(), f"Spreadsheet not found at {XLSX_PATH}"
        wb = openpyxl.load_workbook(XLSX_PATH)
        yield wb
        wb.close()

    @pytest.fixture(scope="module")
    def backup_workbook(self):
        assert BACKUP_PATH.exists(), f"Backup workbook not found at {BACKUP_PATH}"
        wb = openpyxl.load_workbook(BACKUP_PATH)
        yield wb
        wb.close()

    @pytest.fixture(scope="module")
    def jsonl_records(self):
        assert JSONL_PATH.exists(), f"JSONL source not found at {JSONL_PATH}"
        records = []
        with JSONL_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
        return records

    def test_dimensions_and_headers(self, workbook):
        ws = workbook.active
        assert ws.title == "Readiness_Annotation"
        assert ws.max_row == 101, f"Expected 101 rows (1 header + 100 data), got {ws.max_row}"
        assert ws.max_column == 18, f"Expected 18 columns, got {ws.max_column}"

        actual_headers = [ws.cell(row=1, column=c).value for c in range(1, 19)]
        assert actual_headers == EXPECTED_HEADERS

    def test_frozen_panes_and_autofilter(self, workbook):
        ws = workbook.active
        assert ws.freeze_panes == "A2"
        assert ws.auto_filter.ref is not None
        assert "A1:R101" in ws.auto_filter.ref

    def test_data_alignment_with_jsonl_source(self, workbook, jsonl_records):
        ws = workbook.active
        assert len(jsonl_records) == 100

        for idx, rec in enumerate(jsonl_records, start=2):
            # Check Column 1: annotation_id
            assert ws.cell(row=idx, column=1).value == rec["annotation_id"]
            # Check Column 2: candidate_id
            assert ws.cell(row=idx, column=2).value == rec["candidate_id"]
            # Check Column 3: target_occupation_title
            assert ws.cell(row=idx, column=3).value == rec["target_occupation_title"]
            # Check Column 4: target_occupation_uri
            assert ws.cell(row=idx, column=4).value == rec["target_occupation_uri"]

            # Check evidence fields preserved
            assert ws.cell(row=idx, column=5).value is not None  # skills
            assert ws.cell(row=idx, column=6).value is not None  # experience
            assert ws.cell(row=idx, column=7).value is not None  # projects
            assert ws.cell(row=idx, column=8).value is not None  # education

    def test_backup_workbook_strictly_blank(self, backup_workbook):
        """Verifies that the original pre-annotation backup remains completely blank in annotation columns."""
        ws = backup_workbook.active
        assert ws.max_row == 101
        for row in range(2, 102):
            for col in range(9, 19):
                val = ws.cell(row=row, column=col).value
                assert (
                    val is None or val == ""
                ), f"Backup cell at row {row}, col {col} ({EXPECTED_HEADERS[col-1]}) must be blank, but got: {val}"

    def test_dropdown_data_validations(self, workbook):
        ws = workbook.active
        dvs = ws.data_validations.dataValidation
        assert len(dvs) == 7, f"Expected 7 dropdown data validations, got {len(dvs)}"

        ranges = {str(dv.sqref): dv for dv in dvs}

        # Check Column 9: essential_skill_proficiency (I2:I101)
        assert any("I2:I101" in r for r in ranges)
        # Check Column 10: work_experience_relevance (J2:J101)
        assert any("J2:J101" in r for r in ranges)
        # Check Column 11: practical_application_evidence (K2:K101)
        assert any("K2:K101" in r for r in ranges)
        # Check Column 12: education_relevance (L2:L101)
        assert any("L2:L101" in r for r in ranges)
        # Check Column 13: readiness_label (M2:M101)
        assert any("M2:M101" in r for r in ranges)
        # Check Column 14: confidence (N2:N101)
        assert any("N2:N101" in r for r in ranges)
        # Check Column 17: reviewer_status (Q2:Q101)
        assert any("Q2:Q101" in r for r in ranges)

        # Check formula values
        m_dv = [dv for dv in dvs if "M2:M101" in str(dv.sqref)][0]
        assert "Not Ready" in m_dv.formula1
        assert "Developing" in m_dv.formula1
        assert "Job Ready" in m_dv.formula1

    def test_annotation_validity_and_constraints(self, workbook):
        """Phase 5 Quality Audit: checks values, consistency, summaries, and flags."""
        ws = workbook.active
        label_counts = {"Not Ready": 0, "Developing": 0, "Job Ready": 0, "Unlabeled": 0}

        for r in range(2, 102):
            cid = ws.cell(row=r, column=2).value
            prof = ws.cell(row=r, column=9).value
            exp = ws.cell(row=r, column=10).value
            prac = ws.cell(row=r, column=11).value
            edu = ws.cell(row=r, column=12).value
            label = ws.cell(row=r, column=13).value
            conf = ws.cell(row=r, column=14).value
            summary = ws.cell(row=r, column=15).value
            annotator = ws.cell(row=r, column=16).value
            status = ws.cell(row=r, column=17).value
            notes = ws.cell(row=r, column=18).value

            # Verify dropdown values conform to schema
            assert prof in VALID_PROFICIENCY, f"Row {r} ({cid}) invalid proficiency: {prof}"
            assert exp in VALID_EXP_RELEVANCE, f"Row {r} ({cid}) invalid exp relevance: {exp}"
            assert prac in VALID_PRACTICAL, f"Row {r} ({cid}) invalid practical: {prac}"
            assert edu in VALID_EDU_RELEVANCE, f"Row {r} ({cid}) invalid edu relevance: {edu}"
            assert label in VALID_READINESS, f"Row {r} ({cid}) invalid readiness: {label}"
            assert conf in VALID_CONFIDENCE, f"Row {r} ({cid}) invalid confidence: {conf}"
            assert status in VALID_REVIEWER_STATUS, f"Row {r} ({cid}) invalid status: {status}"

            # Annotator ID must be present
            assert annotator and annotator.strip(), f"Row {r} ({cid}) missing annotator_id"

            if label is None:
                label_counts["Unlabeled"] += 1
                assert status == "Flagged_Insufficient_Evidence", (
                    f"Row {r} ({cid}) is unlabeled but status is {status}"
                )
                assert notes and len(notes.strip()) > 5, f"Row {r} ({cid}) unlabeled without notes"
            else:
                label_counts[label] += 1
                assert summary and len(summary.strip()) > 10, (
                    f"Row {r} ({cid}) labeled '{label}' but missing evidence summary"
                )

        # Confirm all 3 readiness classes represented
        assert label_counts["Job Ready"] > 0
        assert label_counts["Developing"] > 0
        assert label_counts["Not Ready"] > 0
        assert label_counts["Unlabeled"] > 0
        assert sum(label_counts.values()) == 100

    def test_first_five_reviewed_recommendations(self, workbook):
        """Verifies Phase 2 prompt specifications for mr_1, mr_2, mr_3, mr_4, mr_7."""
        ws = workbook.active

        # Row 2: mr_1
        assert ws.cell(row=2, column=2).value == "mr_1"
        assert ws.cell(row=2, column=9).value == "Foundational"
        assert ws.cell(row=2, column=10).value == "Partial_or_Junior"
        assert ws.cell(row=2, column=11).value == "None_Observed"
        assert ws.cell(row=2, column=12).value == "Directly_Aligned_Degree"
        assert ws.cell(row=2, column=13).value == "Developing"
        assert ws.cell(row=2, column=14).value == "Low"
        assert ws.cell(row=2, column=17).value == "Flagged_Insufficient_Evidence"

        # Row 3: mr_2
        assert ws.cell(row=3, column=2).value == "mr_2"
        assert ws.cell(row=3, column=9).value == "Proficient"
        assert ws.cell(row=3, column=10).value is None
        assert ws.cell(row=3, column=11).value == "Production_or_EndToEnd_Systems"
        assert ws.cell(row=3, column=12).value == "Related_Degree"
        assert ws.cell(row=3, column=13).value == "Developing"
        assert ws.cell(row=3, column=14).value == "Low"
        assert ws.cell(row=3, column=17).value == "Flagged_Insufficient_Evidence"

        # Row 4: mr_3
        assert ws.cell(row=4, column=2).value == "mr_3"
        assert ws.cell(row=4, column=9).value == "Foundational"
        assert ws.cell(row=4, column=10).value is None
        assert ws.cell(row=4, column=11).value == "Academic_or_Demo_Projects"
        assert ws.cell(row=4, column=12).value == "Not_Provided"
        assert ws.cell(row=4, column=13).value == "Developing"
        assert ws.cell(row=4, column=14).value == "Low"
        assert ws.cell(row=4, column=17).value == "Flagged_Insufficient_Evidence"

        # Row 5: mr_4
        assert ws.cell(row=5, column=2).value == "mr_4"
        assert ws.cell(row=5, column=13).value is None  # blank per prompt
        assert ws.cell(row=5, column=17).value == "Flagged_Insufficient_Evidence"
        assert "duplicate" in ws.cell(row=5, column=18).value.lower()

        # Row 6: mr_7
        assert ws.cell(row=6, column=2).value == "mr_7"
        assert ws.cell(row=6, column=9).value == "Foundational"
        assert ws.cell(row=6, column=10).value == "Partial_or_Junior"
        assert ws.cell(row=6, column=11).value == "Academic_or_Demo_Projects"
        assert ws.cell(row=6, column=12).value == "Directly_Aligned_Degree"
        assert ws.cell(row=6, column=13).value == "Developing"
        assert ws.cell(row=6, column=14).value == "Medium"
        assert ws.cell(row=6, column=17).value == "Draft"
