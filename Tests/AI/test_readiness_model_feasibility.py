"""Unit and Integration Tests for Career Readiness Model Training Feasibility Audit (M4.4).

Validates:
- Existence and structural completeness of AI/Readiness_Model/training_feasibility_report.md
- Independent verification of annotated dataset label counts (71 labeled, 29 unlabeled)
- Exact class distribution (52 Developing, 16 Job Ready, 3 Not Ready)
- Effective independent evidence groups in labeled pool (71 unique groups, 0 duplicates)
- Mathematical proof that 5-fold stratification fails on minority class while 3-fold succeeds
- Model feasibility assessments (Logistic Regression, Random Forest, XGBoost)
- Final recommendation and limitations
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import warnings
import pytest
import openpyxl
import numpy as np
from sklearn.model_selection import StratifiedKFold

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = PROJECT_ROOT / "AI" / "Readiness_Model" / "training_feasibility_report.md"
XLSX_PATH = PROJECT_ROOT / "Datasets" / "Processed" / "readiness_annotation.xlsx"


class TestReadinessModelFeasibilityReport:
    """Tests for the M4.4 Career Readiness Training Feasibility Audit."""

    @pytest.fixture(scope="module")
    def workbook_records(self):
        assert XLSX_PATH.exists(), f"Spreadsheet not found at {XLSX_PATH}"
        wb = openpyxl.load_workbook(XLSX_PATH)
        ws = wb.active
        records = []
        for r in range(2, 102):
            records.append({
                "row": r,
                "candidate_id": ws.cell(row=r, column=2).value,
                "occupation": ws.cell(row=r, column=3).value,
                "skills": ws.cell(row=r, column=5).value,
                "experience": ws.cell(row=r, column=6).value,
                "projects": ws.cell(row=r, column=7).value,
                "education": ws.cell(row=r, column=8).value,
                "readiness_label": ws.cell(row=r, column=13).value,
                "reviewer_status": ws.cell(row=r, column=17).value,
            })
        wb.close()
        return records

    def test_report_exists_and_contains_required_sections(self):
        assert REPORT_PATH.exists(), f"Report not found at {REPORT_PATH}"
        content = REPORT_PATH.read_text(encoding="utf-8")
        assert len(content) > 1000

        # Required keywords and sections
        assert "Verified Dataset Statistics" in content or "DATASET VERIFICATION" in content
        assert "Independent Evidence Groups" in content or "EVIDENCE CLUSTERING" in content
        assert "Class Distribution" in content
        assert "Data Leakage" in content
        assert "Feature Representation" in content or "Recommended Feature Set" in content
        assert "Five-Fold Stratification is Invalid" in content or "5-Fold Stratification" in content
        assert "Logistic Regression" in content
        assert "Random Forest" in content
        assert "XGBoost" in content
        assert "PROCEED WITH RESTRICTIONS" in content or "Proceed with Restrictions" in content

    def test_verified_dataset_counts(self, workbook_records):
        assert len(workbook_records) == 100

        labeled = [r for r in workbook_records if r["readiness_label"] is not None]
        unlabeled = [r for r in workbook_records if r["readiness_label"] is None]

        assert len(labeled) == 71
        assert len(unlabeled) == 29

        # Unlabeled records must have Flagged_Insufficient_Evidence
        for r in unlabeled:
            assert r["reviewer_status"] == "Flagged_Insufficient_Evidence"

    def test_exact_class_distribution(self, workbook_records):
        labeled = [r for r in workbook_records if r["readiness_label"] is not None]
        counts = Counter(r["readiness_label"] for r in labeled)

        assert counts["Developing"] == 52
        assert counts["Job Ready"] == 16
        assert counts["Not Ready"] == 3
        assert sum(counts.values()) == 71

    def test_zero_duplicate_evidence_in_labeled_pool(self, workbook_records):
        labeled = [r for r in workbook_records if r["readiness_label"] is not None]

        # Check unique evidence tuples
        evidence_set = set()
        for r in labeled:
            key = (r["skills"], r["experience"], r["projects"], r["education"])
            assert key not in evidence_set, f"Duplicate evidence found in labeled record: {r['candidate_id']}"
            evidence_set.add(key)

        assert len(evidence_set) == 71

    def test_stratification_fold_constraints(self, workbook_records):
        """Demonstrates that 5-fold stratification generates a UserWarning while 3-fold succeeds."""
        labeled = [r for r in workbook_records if r["readiness_label"] is not None]
        y = np.array([r["readiness_label"] for r in labeled])

        # 5-fold must issue UserWarning regarding least populated class
        with pytest.warns(UserWarning, match="The least populated class in y has only 3 members"):
            skf_5 = StratifiedKFold(n_splits=5)
            splits_5 = list(skf_5.split(np.zeros(len(y)), y))
            assert len(splits_5) == 5

            # At least 2 folds must have zero instances of Not Ready in test set
            not_ready_test_counts = []
            for _, test_idx in splits_5:
                y_test = y[test_idx]
                not_ready_test_counts.append(np.sum(y_test == "Not Ready"))

            assert not_ready_test_counts.count(0) >= 2

        # 3-fold must succeed cleanly without warnings
        with warnings.catch_warnings():
            warnings.simplefilter("error", UserWarning)
            skf_3 = StratifiedKFold(n_splits=3)
            splits_3 = list(skf_3.split(np.zeros(len(y)), y))
            assert len(splits_3) == 3

            # Every fold must have exactly 1 Not Ready instance in test set
            for _, test_idx in splits_3:
                y_test = y[test_idx]
                assert np.sum(y_test == "Not Ready") == 1
                assert np.sum(y_test == "Job Ready") >= 5
                assert np.sum(y_test == "Developing") >= 17

