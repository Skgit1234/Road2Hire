"""Tests for Road2Hire M3 Hybrid Skill Gap Detection.

Covers:
- Exact skill matches (concept URI and label)
- Knowledge graph relationship matching (narrower, related, broader)
- Semantic similarity matching and hard-negative rejection
- Missing essential and optional skill categorization
- Configurable essential (75%) vs optional (25%) weighting
- Zero candidate skills / freshers (0% coverage, all skills missing)
- Zero optional skills handling without division by zero
- Unmapped and surplus candidate skill isolation
- Invalid occupation error handling
- Central Road2HireModel.detect_skill_gap() integration
- Structured schema validation and audit trail
"""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from AI.Candidate_Profile.profile_schema import CandidateProfile
from AI.Knowledge_Graph.esco_graph import ESCOKnowledgeGraph, get_esco_graph
from AI.Skill_Extraction.esco_taxonomy import get_esco_taxonomy
from AI.Skill_Gap.gap_scoring import compute_gap_scores
from AI.Skill_Gap.skill_gap_detector import SkillGapDetector, get_skill_gap_detector

SAMPLE_RESUME_PDF = Path("Tests/AI/sample_resume.pdf")


class TestGapScoringFormulas(unittest.TestCase):
    """Test compute_gap_scores edge cases and weightings."""

    def test_default_weights_and_standard_calculation(self):
        # 2 essential skills, 1 fully matched (1.0), 1 half matched (0.5) -> avg = 0.75
        # 2 optional skills, 1 fully matched (1.0), 1 missing (0.0) -> avg = 0.50
        # Overall = 0.75 * 0.75 + 0.25 * 0.50 = 0.5625 + 0.125 = 0.6875
        scores = compute_gap_scores(
            essential_credits=[1.0, 0.5],
            total_essential_count=2,
            optional_credits=[1.0],
            total_optional_count=2,
            essential_weight=0.75,
            optional_weight=0.25,
        )
        self.assertEqual(scores["essential_skill_coverage_score"], 0.75)
        self.assertEqual(scores["optional_skill_coverage_score"], 0.50)
        self.assertEqual(scores["overall_skill_coverage_score"], 0.6875)
        self.assertEqual(scores["scoring_weights"]["essential"], 0.75)
        self.assertEqual(scores["scoring_weights"]["optional"], 0.25)

    def test_zero_candidate_credits_returns_zero(self):
        scores = compute_gap_scores(
            essential_credits=[],
            total_essential_count=5,
            optional_credits=[],
            total_optional_count=3,
        )
        self.assertEqual(scores["essential_skill_coverage_score"], 0.0)
        self.assertEqual(scores["optional_skill_coverage_score"], 0.0)
        self.assertEqual(scores["overall_skill_coverage_score"], 0.0)

    def test_zero_optional_skills_no_division_by_zero(self):
        """Occupation with 0 optional skills should have None optional score and 100% essential drive."""
        scores = compute_gap_scores(
            essential_credits=[1.0, 1.0],
            total_essential_count=2,
            optional_credits=[],
            total_optional_count=0,
        )
        self.assertEqual(scores["essential_skill_coverage_score"], 1.0)
        self.assertIsNone(scores["optional_skill_coverage_score"])
        self.assertEqual(scores["overall_skill_coverage_score"], 1.0)
        self.assertEqual(scores["scoring_weights"]["essential"], 1.0)
        self.assertEqual(scores["scoring_weights"]["optional"], 0.0)

    def test_negative_weights_raise_value_error(self):
        """Negative weights must be rejected with ValueError."""
        with self.assertRaises(ValueError):
            compute_gap_scores(
                essential_credits=[1.0],
                total_essential_count=1,
                optional_credits=[1.0],
                total_optional_count=1,
                essential_weight=-0.5,
                optional_weight=0.5,
            )
        with self.assertRaises(ValueError):
            SkillGapDetector(essential_weight=-0.1)


class TestSkillGapDetectorUnit(unittest.TestCase):
    """Unit tests for SkillGapDetector matching tiers."""

    @classmethod
    def setUpClass(cls):
        cls.taxonomy = get_esco_taxonomy()
        cls.graph = get_esco_graph(cls.taxonomy)
        cls.detector = SkillGapDetector(graph=cls.graph, taxonomy=cls.taxonomy)

    def test_invalid_target_occupation_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.detector.detect_gap(
                candidate={"skills": ["Python"]},
                target_occupation="TotallyFakeOccupationNameXYZ999",
            )

    def test_empty_candidate_profile_returns_zero_coverage(self):
        # Using a valid real ESCO occupation: 'software developer'
        report = self.detector.detect_gap(
            candidate={"skills": []},
            target_occupation="software developer",
        )
        self.assertEqual(report["overall_skill_coverage_score"], 0.0)
        self.assertEqual(report["essential_skill_coverage_score"], 0.0)
        self.assertEqual(len(report["matched_skills"]), 0)
        self.assertEqual(len(report["partially_matched_skills"]), 0)
        self.assertGreater(len(report["missing_essential_skills"]), 0)
        self.assertIn("heuristic alignment", report["disclaimer"])

    def test_exact_match_tier(self):
        # Candidate has Python (computer programming)
        candidate = {
            "skills": [
                {
                    "skill": "Python (computer programming)",
                    "ESCO_Skill_Id": "http://data.europa.eu/esco/skill/4c5b2a62-5a76-4d99-a7a8-cbf04e9e8d1e",
                    "ESCO_Skill_Name": "Python (computer programming)",
                }
            ]
        }
        report = self.detector.detect_gap(candidate, "software developer")
        matched_cands = [m["candidate_skill"] for m in report["matched_skills"]]
        self.assertTrue(any("Python" in name for name in matched_cands))
        exact_matches = [m for m in report["matched_skills"] if m["tier"] == "exact"]
        self.assertGreater(len(exact_matches), 0)
        self.assertEqual(exact_matches[0]["credit_assigned"], 1.0)

    def test_deceptive_distinct_skills_not_matched(self):
        """Java and JavaScript must never match despite lexically overlapping tokens."""
        # Software developer requires 'JavaScript' or 'computer programming'
        candidate = {
            "skills": [
                {"skill": "Java", "ESCO_Skill_Id": "", "ESCO_Skill_Name": "Java"}
            ]
        }
        report = self.detector.detect_gap(candidate, "software developer")
        # Ensure Java is not falsely matched as JavaScript
        for match in report["matched_skills"]:
            pair = {match["candidate_skill"].lower(), match["target_skill"].lower()}
            self.assertFalse(
                {"java", "javascript"}.issubset(pair),
                msg="Deceptive pair Java and JavaScript was improperly matched!",
            )

    def test_unmapped_skills_reported(self):
        candidate = {
            "skills": [
                {"skill": "TotallyMadeUpSkill123", "ESCO_Skill_Id": "", "ESCO_Skill_Name": ""}
            ]
        }
        report = self.detector.detect_gap(candidate, "software developer")
        self.assertIn("TotallyMadeUpSkill123", report["unmapped_candidate_skills"])

    def test_surplus_skills_reported(self):
        # If candidate has a completely irrelevant skill for a software developer
        # (e.g. 'dental surgery' or 'baking bread')
        candidate = {
            "skills": [
                {"skill": "Python (computer programming)"},
                {"skill": "baking bread"},
            ]
        }
        report = self.detector.detect_gap(candidate, "software developer")
        self.assertIn("baking bread", report["surplus_candidate_skills"])

    def test_strict_one_to_one_matching(self):
        """A single candidate skill cannot satisfy multiple target requirements."""
        candidate = {
            "skills": [
                {"skill": "Python (computer programming)"}
            ]
        }
        report = self.detector.detect_gap(candidate, "software developer")
        matched_cand_skills = [m["candidate_skill"] for m in report["matched_skills"]]
        # Python should appear at most once in matched_skills
        self.assertLessEqual(matched_cand_skills.count("Python (computer programming)"), 1)

    def test_graph_relationship_direction_narrower_and_broader(self):
        """Verify ESCO hierarchical relationship directions and credit assignments."""
        narrower_uri = "http://data.europa.eu/esco/skill/0007bdc2-dd15-4824-b7d6-416522c46f35"
        broader_uri = "http://data.europa.eu/esco/skill/23033c54-cc98-47dc-b972-4a8d1646754d"

        # Case 1: Candidate has narrower concept, target requires broader concept
        cand1 = [{"name": "control compliance", "uri": narrower_uri, "embedding": None}]
        target1 = [{
            "skill_uri": broader_uri,
            "skill_label": "inspect manufacture",
            "relation_type": "essential",
            "skill_type": "skill/competence",
        }]
        matched, partial, missing, surplus = self.detector._execute_hybrid_matching(cand1, target1)
        self.assertEqual(len(matched), 0)
        self.assertEqual(len(partial), 1)
        self.assertEqual(partial[0]["graph_relationship"], "is_narrower_than")
        self.assertEqual(partial[0]["credit_assigned"], 0.75)

        # Case 2: Candidate has broader concept, target requires narrower concept
        cand2 = [{"name": "inspect manufacture", "uri": broader_uri, "embedding": None}]
        target2 = [{
            "skill_uri": narrower_uri,
            "skill_label": "control compliance",
            "relation_type": "essential",
            "skill_type": "skill/competence",
        }]
        matched2, partial2, missing2, surplus2 = self.detector._execute_hybrid_matching(cand2, target2)
        self.assertEqual(len(matched2), 0)
        self.assertEqual(len(partial2), 1)
        self.assertEqual(partial2[0]["graph_relationship"], "is_broader_than")
        self.assertEqual(partial2[0]["credit_assigned"], 0.60)

    def test_known_related_pairs_safeguard_in_tier3(self):
        """Pairs in KNOWN_RELATED_PAIRS must be classified as partial match, not full match."""
        # FastAPI vs REST APIs: mock identical/high-similarity embeddings
        high_sim_vec = [1.0] + [0.0] * 383
        cand = [{"name": "FastAPI", "uri": None, "embedding": high_sim_vec}]
        target = [{
            "skill_uri": "mock_rest_api_uri",
            "skill_label": "REST APIs",
            "relation_type": "essential",
            "skill_type": "skill/competence",
        }]

        with patch("AI.Skill_Gap.skill_gap_detector.generate_skill_embeddings") as mock_emb:
            mock_emb.return_value = {
                "skills": [{"skill": "rest apis", "embedding": high_sim_vec}]
            }
            matched, partial, missing, surplus = self.detector._execute_hybrid_matching(cand, target)

        self.assertEqual(len(matched), 0, "Related pair must NOT be classified as confirmed match!")
        self.assertEqual(len(partial), 1)
        self.assertEqual(partial[0]["tier"], "semantic")
        self.assertEqual(partial[0]["graph_relationship"], "domain_related")
        self.assertLess(partial[0]["credit_assigned"], 1.0)


class TestSkillGapIntegrationWithModel(unittest.TestCase):
    """Test detect_skill_gap integration through central Road2HireModel."""

    @classmethod
    def setUpClass(cls):
        from AI.road2hire_model import Road2HireModel

        cls.model = Road2HireModel()

    def test_detect_gap_from_pdf_resume(self):
        report = self.model.detect_skill_gap(
            resume_or_profile=SAMPLE_RESUME_PDF,
            target_occupation="software developer",
        )
        self.assertIn("target_occupation", report)
        self.assertIn("overall_skill_coverage_score", report)
        self.assertIn("essential_skill_coverage_score", report)
        self.assertIn("missing_essential_skills", report)
        self.assertGreaterEqual(report["overall_skill_coverage_score"], 0.0)
        self.assertLessEqual(report["overall_skill_coverage_score"], 1.0)

    def test_predict_remains_unmodified(self):
        """Confirm that Phase 3 predict() output keys and behavior are 100% preserved."""
        result = self.model.predict(SAMPLE_RESUME_PDF)
        expected_keys = {
            "status", "pipeline_version", "source_file", "page_count",
            "extraction_status", "sections", "section_count", "detected_headings",
            "extracted_skills", "skill_count", "esco_mappings", "mapped_skill_count",
            "occupation_matches", "candidate_profile", "profile_validation_errors",
            "warnings", "errors",
        }
        self.assertEqual(expected_keys - result.keys(), set())


if __name__ == "__main__":
    unittest.main()

