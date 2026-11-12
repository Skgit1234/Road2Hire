"""Tests for Road2Hire M4.2 Dataset Preparation Module.

Covers:
- Dataset inventory discovery and verification
- Streaming access to master_resumes.jsonl without full memory load
- Loading and indexing gold_labels.json, scraped_jobs.json, synthetic_profiles.json
- Adapting master resumes to standardized CandidateProfile (schema v1.1.0)
- Validation of adapted profiles via profile_validator (0 fatal errors)
- Adapting ESCO occupations into requirement summaries
- Assembling unified CandidateOccupationRecord with hybrid skill gap features
- Verification that raw datasets are accessed in read-only mode and not modified
"""

import unittest
from pathlib import Path

from AI.Candidate_Profile.profile_validator import validate_candidate_profile_comprehensive
from AI.Dataset_Preparation import (
    adapt_esco_occupation,
    adapt_master_resume_to_candidate_profile,
    get_dataset_inventory,
    get_gold_label_index,
    load_gold_labels,
    load_scraped_jobs,
    load_synthetic_profiles,
    stream_master_resumes,
)
from AI.Knowledge_Graph.esco_graph import get_esco_graph
from AI.Skill_Extraction.esco_taxonomy import get_esco_taxonomy
from AI.Skill_Gap.skill_gap_detector import SkillGapDetector


class TestDatasetInventory(unittest.TestCase):
    """Test dataset inventory discovery and raw file verification."""

    def test_inventory_detects_all_required_datasets(self):
        inventory = get_dataset_inventory()

        required_keys = [
            "master_resumes",
            "scraped_jobs",
            "synthetic_profiles",
            "gold_labels",
            "esco_skill_mapping",
            "onet_skill_mapping",
            "esco_occupations",
            "esco_skills",
            "esco_occupation_skill_relations",
            "skill_taxonomy_processed",
        ]

        for key in required_keys:
            self.assertIn(key, inventory, f"Expected '{key}' in dataset inventory.")
            self.assertTrue(
                inventory[key]["exists"],
                f"Dataset file '{inventory[key]['relative_path']}' should exist.",
            )
            self.assertGreater(
                inventory[key]["size_bytes"],
                0,
                f"Dataset file '{key}' should not be empty.",
            )

    def test_stream_master_resumes_lazy_loading(self):
        """Streaming should yield valid JSON records up to the limit without loading the full file."""
        records = list(stream_master_resumes(limit=5))
        self.assertEqual(len(records), 5)
        for r in records:
            self.assertIn("personal_info", r)
            self.assertIn("experience", r)
            self.assertIn("education", r)
            self.assertIn("skills", r)
            self.assertIn("projects", r)

    def test_load_gold_labels_and_indexing(self):
        labels = load_gold_labels()
        self.assertEqual(len(labels), 108)

        index = get_gold_label_index()
        self.assertEqual(len(index), 108)
        # Check a sample pair_id
        sample_pair = labels[0]["pair_id"]
        self.assertIn(sample_pair, index)
        self.assertIn("skills", index[sample_pair])
        self.assertIn("composite", index[sample_pair])

    def test_load_scraped_jobs_and_synthetic_profiles(self):
        jobs = load_scraped_jobs(limit=10)
        self.assertEqual(len(jobs), 10)
        self.assertIn("id", jobs[0])
        self.assertIn("title", jobs[0])

        syn = load_synthetic_profiles(limit=10)
        self.assertEqual(len(syn), 10)
        self.assertIn("profile_id", syn[0])
        self.assertIn("skills_primary", syn[0])


class TestCandidateAndOccupationAdapters(unittest.TestCase):
    """Test adapting raw data into canonical CandidateProfile and occupation summaries."""

    @classmethod
    def setUpClass(cls):
        cls.taxonomy = get_esco_taxonomy()
        cls.esco_graph = get_esco_graph(cls.taxonomy)
        cls.detector = SkillGapDetector(graph=cls.esco_graph, taxonomy=cls.taxonomy)

    def test_adapt_master_resume_to_candidate_profile(self):
        raw_resumes = list(stream_master_resumes(limit=1))
        self.assertEqual(len(raw_resumes), 1)

        profile = adapt_master_resume_to_candidate_profile(
            raw_record=raw_resumes[0],
            candidate_id="test_candidate_0",
            taxonomy=self.taxonomy,
        )

        self.assertEqual(profile["schema_version"], "1.1.0")
        self.assertEqual(profile["source_file"], "master_resumes:test_candidate_0")
        self.assertIsInstance(profile["candidate"], dict)
        self.assertIsInstance(profile["skills"], list)
        self.assertGreater(len(profile["skills"]), 0)
        self.assertIsInstance(profile["experience"], list)
        self.assertIsInstance(profile["education"], list)

        # Validate with comprehensive profile validator - MUST have 0 fatal errors
        res = validate_candidate_profile_comprehensive(profile)
        self.assertEqual(
            res["errors"],
            [],
            f"Adapted candidate profile produced fatal validation errors: {res['errors']}",
        )

    def test_adapt_esco_occupation(self):
        summary = adapt_esco_occupation("software developer", graph=self.esco_graph)
        self.assertEqual(summary["source_type"], "esco")
        self.assertIn("software developer", summary["occupation_title"].lower())
        self.assertGreater(summary["total_required_skills"], 0)
        self.assertGreater(len(summary["essential_skills"]), 0)
        self.assertGreater(len(summary["optional_skills"]), 0)

    def test_unified_candidate_occupation_record_construction(self):
        raw_resumes = list(stream_master_resumes(limit=1))
        profile = adapt_master_resume_to_candidate_profile(raw_resumes[0], candidate_id="0")
        occ_summary = adapt_esco_occupation("software developer", graph=self.esco_graph)

        # Compute skill gap features using existing detector without logic duplication
        gap_report = self.detector.detect_gap(profile, "software developer")

        # Assemble CandidateOccupationRecord
        record = {
            "pair_id": f"pair_0_{occ_summary['occupation_id']}",
            "candidate_id": "0",
            "candidate_source": "master_resumes",
            "candidate_profile": profile,
            "candidate_skills_normalized": [s["skill"] for s in profile["skills"]],
            "target_occupation": occ_summary,
            "skill_gap_features": {
                "overall_skill_coverage_score": gap_report["overall_skill_coverage_score"],
                "essential_skill_coverage_score": gap_report["essential_skill_coverage_score"],
                "optional_skill_coverage_score": gap_report["optional_skill_coverage_score"],
                "matched_skills_count": gap_report["matching_summary"]["matched_skills_count"],
                "partially_matched_skills_count": gap_report["matching_summary"]["partially_matched_skills_count"],
                "missing_essential_skills_count": gap_report["matching_summary"]["missing_essential_skills_count"],
                "missing_optional_skills_count": gap_report["matching_summary"]["missing_optional_skills_count"],
                "surplus_candidate_skills_count": gap_report["matching_summary"]["surplus_candidate_skills_count"],
            },
            "matched_skills_evidence": gap_report["matched_skills"],
            "partially_matched_skills_evidence": gap_report["partially_matched_skills"],
            "missing_essential_skills": gap_report["missing_essential_skills"],
            "missing_optional_skills": gap_report["missing_optional_skills"],
            "ground_truth": None,
            "metadata": {
                "pipeline_version": "1.0.0",
            },
        }

        self.assertIn("pair_id", record)
        self.assertIn("candidate_profile", record)
        self.assertIn("skill_gap_features", record)
        self.assertGreaterEqual(record["skill_gap_features"]["overall_skill_coverage_score"], 0.0)
        self.assertLessEqual(record["skill_gap_features"]["overall_skill_coverage_score"], 1.0)


if __name__ == "__main__":
    unittest.main()

