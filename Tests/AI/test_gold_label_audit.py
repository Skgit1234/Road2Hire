"""Focused unit and integration tests for Road2Hire M4.2 Gold-Label Quality Audit.

Covers:
- Status classification (verified, pending, missing_status, invalid)
- Referential integrity validation (candidate IDs in synthetic profiles, job IDs in scraped jobs)
- Score bounds validation and composite score formula verification
- Duplicate candidate-job pair detection
- Reasoning text presence and sufficiency
- Task alignment distinction (compatibility vs. career readiness)
"""

from pathlib import Path
import unittest

from AI.Dataset_Preparation.gold_label_audit import (
    audit_gold_labels,
    classify_record_status,
    parse_pair_id,
)


class TestGoldLabelAuditLogic(unittest.TestCase):
    """Unit tests for the gold-label audit functions."""

    def test_parse_pair_id(self):
        cand_id, job_id = parse_pair_id("13_linkedin_4392811970")
        self.assertEqual(cand_id, "13")
        self.assertEqual(job_id, "linkedin_4392811970")

        cand_id2, job_id2 = parse_pair_id("21_job_20")
        self.assertEqual(cand_id2, "21")
        self.assertEqual(job_id2, "job_20")

    def test_status_classification_invalid_records(self):
        # Broken job reference
        rec = {
            "pair_id": "21_job_20",
            "skills": 80,
            "seniority": 80,
            "domain": 80,
            "location": 80,
            "composite": 80,
        }
        self.assertEqual(
            classify_record_status(rec, valid_job=False, valid_cand=True),
            "invalid",
        )

        # Broken candidate reference
        self.assertEqual(
            classify_record_status(rec, valid_job=True, valid_cand=False),
            "invalid",
        )

        # Out-of-bounds score
        rec_out_of_bounds = dict(rec)
        rec_out_of_bounds["skills"] = 150
        self.assertEqual(
            classify_record_status(rec_out_of_bounds, valid_job=True, valid_cand=True),
            "invalid",
        )

    def test_status_classification_pending_records(self):
        # Explicit review_status: pending
        rec = {
            "pair_id": "34_linkedin_4407156829",
            "skills": 85,
            "seniority": 95,
            "domain": 72,
            "location": 68,
            "composite": 81,
            "review_status": "pending",
        }
        self.assertEqual(
            classify_record_status(rec, valid_job=True, valid_cand=True),
            "pending",
        )

        # Missing reasoning and no status field
        rec_no_reason = {
            "pair_id": "34_linkedin_4407156829",
            "skills": 85,
            "seniority": 95,
            "domain": 72,
            "location": 68,
            "composite": 81,
            "reasoning": "",
        }
        self.assertEqual(
            classify_record_status(rec_no_reason, valid_job=True, valid_cand=True),
            "pending",
        )

    def test_status_classification_missing_status_records(self):
        # Valid references, valid scores, human reasoning, but no status field
        rec = {
            "pair_id": "13_linkedin_4392811970",
            "skills": 98,
            "seniority": 95,
            "domain": 90,
            "location": 97,
            "composite": 96,
            "reasoning": "Sr Backend (TS/Node/PG/GraphQL) × Fullstack @PwC. All skills match.",
        }
        self.assertEqual(
            classify_record_status(rec, valid_job=True, valid_cand=True),
            "missing_status",
        )

    def test_status_classification_verified_records(self):
        # Explicit status verified with complete reasoning
        rec = {
            "pair_id": "13_linkedin_4392811970",
            "skills": 98,
            "seniority": 95,
            "domain": 90,
            "location": 97,
            "composite": 96,
            "status": "verified",
            "reasoning": "Sr Backend (TS/Node/PG/GraphQL) × Fullstack @PwC. All skills match.",
        }
        self.assertEqual(
            classify_record_status(rec, valid_job=True, valid_cand=True),
            "verified",
        )


class TestGoldLabelAuditExecution(unittest.TestCase):
    """Integration audit test directly against Datasets/gold_labels.json."""

    @classmethod
    def setUpClass(cls):
        cls.audit_result = audit_gold_labels()

    def test_total_record_count_and_status_counts(self):
        res = self.audit_result
        self.assertEqual(res["total_records"], 108)

        # Status breakdown
        counts = res["status_counts"]
        self.assertEqual(counts["verified"], 0, "No records should be classified as verified without explicit sign-off.")
        self.assertEqual(counts["invalid"], 2, "Exactly 2 records have broken foreign keys.")
        self.assertEqual(counts["pending"], 58, "Cohort B contains 58 valid pending records.")
        self.assertEqual(counts["missing_status"], 48, "Cohort A contains 48 records with reasoning but no status field.")

        # Sum of categories must equal total
        self.assertEqual(
            counts["verified"] + counts["pending"] + counts["missing_status"] + counts["invalid"],
            108,
        )

    def test_invalid_records_details(self):
        invalid = self.audit_result["invalid_records"]
        self.assertEqual(len(invalid), 2)

        invalid_pairs = {item["pair_id"] for item in invalid}
        self.assertEqual(invalid_pairs, {"21_job_20", "111_job_14"})

    def test_candidate_referential_integrity(self):
        cand_stats = self.audit_result["candidate_reference_stats"]
        self.assertEqual(cand_stats["valid_references"], 108)
        self.assertEqual(cand_stats["missing_references"], [])

    def test_score_ranges_and_composite_formula(self):
        score_val = self.audit_result["score_validation"]
        for f in ("skills", "seniority", "domain", "location", "composite"):
            self.assertEqual(score_val[f]["null_count"], 0)
            self.assertEqual(score_val[f]["out_of_bounds_count"], 0)
            self.assertGreaterEqual(score_val[f]["min_value"], 0)
            self.assertLessEqual(score_val[f]["max_value"], 100)

        # Composite formula: composite == round(0.50*skills + 0.15*seniority + 0.10*domain + 0.25*location)
        mismatches = self.audit_result["composite_formula_mismatches"]
        self.assertEqual(len(mismatches), 0, f"Unexpected formula mismatches: {mismatches}")

    def test_zero_duplicate_pair_ids(self):
        duplicates = self.audit_result["duplicate_pair_ids"]
        self.assertEqual(duplicates, [], f"Found duplicate pair IDs: {duplicates}")

    def test_task_classification_compatibility_not_career_readiness(self):
        """Audit must designate gold_labels as candidate-job compatibility, not career readiness."""
        res = self.audit_result
        self.assertEqual(res["dataset_type_classification"], "candidate_job_compatibility")
        self.assertEqual(res["suitable_for_career_readiness_eval_count"], 0)
        self.assertEqual(res["suitable_for_compatibility_eval_count"], 48)


if __name__ == "__main__":
    unittest.main()

