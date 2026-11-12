import unittest
from types import SimpleNamespace
from unittest.mock import patch

from Services.job_matching import match_job_requirements
from AI.Semantic_Matching.semantic_matcher import SemanticSkillMatcher


class StubMatcher:
    def __init__(self, assignments=(), related=()):
        self.assignments = assignments
        self.related = related
        self.received = None

    def match(self, candidates, requirements):
        self.received = (candidates, requirements)
        return {"assignments": list(self.assignments), "related_skills": list(self.related)}


class JobMatchingTests(unittest.TestCase):
    @patch("AI.Semantic_Matching.semantic_matcher.generate_skill_embeddings")
    def test_shared_matcher_confirms_exact_and_semantic_matches_without_model_download(self, embed):
        vectors = {
            "Python": [1.0, 0.0],
            "React framework": [0.99, 0.01],
            "React library": [1.0, 0.0],
        }
        embed.side_effect = lambda names, model_name: {
            "skills": [{"skill": name, "embedding": vectors[name]} for name in names]
        }
        matcher = SemanticSkillMatcher(use_taxonomy=False)
        exact = matcher.match(["Python"], ["Python"])
        semantic = matcher.match(["React framework"], ["React library"])
        self.assertEqual(exact["assignments"][0]["status"], "confirmed_match")
        self.assertEqual(exact["assignments"][0]["similarity_score"], 1.0)
        self.assertEqual(semantic["assignments"][0]["status"], "confirmed_match")

    def test_confirmed_matches_score_essential_and_optional_requirements(self):
        matcher = StubMatcher(assignments=[
            {"candidate_skill": "Python", "required_skill": "Python", "status": "confirmed_match",
             "similarity_score": 1.0, "evidence": "Canonical/exact equality"},
            {"candidate_skill": "React", "required_skill": "React UI", "status": "confirmed_match",
             "similarity_score": 0.87, "evidence": "Semantic threshold confirmed"},
        ])
        result = match_job_requirements(
            [{"skill": "Python"}, {"skill": "React"}],
            [{"skill_name": "Python"}, {"skill_name": "React UI", "importance": "optional"}],
            job_id=7, pipeline_run_id=12, matcher=matcher,
        )
        self.assertEqual(matcher.received[0], ["Python", "React"])
        self.assertTrue(all(item["matched"] for item in result["requirements"]))
        self.assertEqual(result["scores"], {"essential": 1.0, "optional": 1.0, "overall": 1.0})
        self.assertEqual((result["job_id"], result["pipeline_run_id"]), (7, 12))
        self.assertFalse(result["candidate_skills_are_verified"])

    def test_duplicate_requirement_name_uses_only_one_candidate_assignment(self):
        matcher = StubMatcher(assignments=[{
            "candidate_skill": "Python", "required_skill": "Python", "status": "confirmed_match",
            "similarity_score": 1.0, "evidence": "Canonical/exact equality",
        }])
        result = match_job_requirements(
            ["Python"],
            [{"skill_name": "Python", "importance": "essential"},
             {"skill_name": "Python", "importance": "optional"}],
            job_id=1, pipeline_run_id=2, matcher=matcher,
        )
        self.assertEqual([item["matched"] for item in result["requirements"]], [True, False])
        self.assertEqual([item["match_status"] for item in result["requirements"]],
                         ["confirmed_match", "non_match"])
        self.assertEqual(result["scores"], {"essential": 1.0, "optional": 0.0, "overall": 0.75})

    def test_duplicate_candidate_entries_and_duplicate_assignments_cannot_double_credit(self):
        matcher = StubMatcher(assignments=[
            {"candidate_skill": "Python", "required_skill": "Python", "status": "confirmed_match",
             "similarity_score": 1.0, "evidence": "first assignment"},
            {"candidate_skill": "Python", "required_skill": "Python", "status": "confirmed_match",
             "similarity_score": 1.0, "evidence": "duplicate candidate assignment"},
        ])
        result = match_job_requirements(
            ["Python", "Python"],
            [{"skill_name": "Python", "importance": "essential"},
             {"skill_name": "Python", "importance": "optional"}],
            job_id=1, pipeline_run_id=2, matcher=matcher,
        )
        self.assertEqual(matcher.received[0], ["Python"])
        self.assertEqual([item["matched"] for item in result["requirements"]], [True, False])
        self.assertEqual(result["scores"]["overall"], 0.75)

    def test_uncertain_evidence_is_preserved_without_coverage(self):
        matcher = StubMatcher(assignments=[{
            "candidate_skill": "Nearby", "required_skill": "Required", "status": "uncertain_match",
            "similarity_score": 0.7, "evidence": "Similarity in uncertain band",
        }])
        result = match_job_requirements(
            ["Nearby"], [{"skill_name": "Required"}],
            job_id=1, pipeline_run_id=2, matcher=matcher,
        )
        requirement = result["requirements"][0]
        self.assertEqual(requirement["match_status"], "uncertain_match")
        self.assertFalse(requirement["matched"])
        self.assertEqual(requirement["candidate_skill"], "Nearby")
        self.assertEqual(requirement["similarity_score"], 0.7)
        self.assertEqual(requirement["evidence"], "Similarity in uncertain band")
        self.assertEqual(result["scores"]["essential"], 0.0)

    def test_related_evidence_is_preserved_without_coverage(self):
        matcher = StubMatcher(related=[{
            "candidate_skill": "Docker", "required_skill": "Kubernetes",
            "similarity_score": 0.81, "relation": "Containerization ecosystem", "is_equivalent": False,
        }])
        result = match_job_requirements(
            ["Docker"], [{"skill_name": "Kubernetes", "importance": "optional"}],
            job_id=1, pipeline_run_id=2, matcher=matcher,
        )
        requirement = result["requirements"][0]
        self.assertEqual(requirement["match_status"], "related_skill")
        self.assertFalse(requirement["matched"])
        self.assertEqual(requirement["candidate_skill"], "Docker")
        self.assertEqual(requirement["similarity_score"], 0.81)
        self.assertEqual(requirement["related_evidence"][0]["relation"], "Containerization ecosystem")
        self.assertEqual(result["scores"]["optional"], 0.0)

    def test_only_confirmed_matches_contribute_to_all_coverage_scores(self):
        matcher = StubMatcher(assignments=[
            {"candidate_skill": "Good", "required_skill": "Good", "status": "confirmed_match",
             "similarity_score": 1.0, "evidence": "exact"},
            {"candidate_skill": "Maybe", "required_skill": "Maybe", "status": "uncertain_match",
             "similarity_score": 0.7, "evidence": "uncertain"},
        ], related=[{
            "candidate_skill": "Related", "required_skill": "Related", "similarity_score": 0.8,
            "relation": "Related only", "is_equivalent": False,
        }])
        result = match_job_requirements(
            ["Good", "Maybe", "Related"],
            [
                {"skill_name": "Good"},
                {"skill_name": "Maybe"},
                {"skill_name": "Related", "importance": "optional"},
                {"skill_name": "Absent", "importance": "optional"},
            ],
            job_id=1, pipeline_run_id=2, matcher=matcher,
        )
        self.assertEqual(result["scores"], {"essential": 0.5, "optional": 0.0, "overall": 0.375})

    def test_non_match_and_missing_are_distinguished(self):
        non_match = match_job_requirements(
            ["Python"], [{"skill_name": "Unrelated"}],
            job_id=1, pipeline_run_id=2, matcher=StubMatcher(),
        )["requirements"][0]
        missing = match_job_requirements(
            [], [{"skill_name": "Unrelated"}],
            job_id=1, pipeline_run_id=2,
        )["requirements"][0]
        self.assertEqual(non_match["match_status"], "non_match")
        self.assertFalse(non_match["matched"])
        self.assertEqual(missing["match_status"], "missing")
        self.assertFalse(missing["matched"])

    def test_duplicate_candidate_names_are_deduplicated(self):
        matcher = StubMatcher()
        match_job_requirements(
            [{"skill": "Python"}, {"skill": " python "}, "Python"],
            [{"skill_name": "Python"}], job_id=1, pipeline_run_id=2, matcher=matcher,
        )
        self.assertEqual(matcher.received[0], ["Python"])

    def test_only_skills_in_extracted_list_are_passed_to_matcher(self):
        matcher = StubMatcher()
        extracted_skills = [{"skill": "Python"}]
        _profile_skills = [{"skill": "Profile only"}]
        _inferred_occupation_skills = [{"skill": "Occupation only"}]
        match_job_requirements(
            extracted_skills, [{"skill_name": "Python"}],
            job_id=1, pipeline_run_id=2, matcher=matcher,
        )
        self.assertEqual(matcher.received[0], ["Python"])

    def test_empty_candidates_and_empty_requirements(self):
        matcher = StubMatcher()
        result = match_job_requirements(
            [], [{"skill_name": "Python"}], job_id=1, pipeline_run_id=2, matcher=matcher,
        )
        self.assertEqual(result["requirements"][0]["match_status"], "missing")
        self.assertEqual(result["scores"]["essential"], 0.0)
        self.assertIsNone(matcher.received)

        empty = match_job_requirements([], [], job_id=1, pipeline_run_id=2)
        self.assertEqual(empty["status"], "no_requirements")
        self.assertEqual(empty["requirements"], [])
        self.assertEqual(empty["canonical_uri_matching"], "not_used")

    def test_invalid_saved_requirements_are_rejected(self):
        invalid = (
            ["Python"],
            [{"skill_name": "Python", "importance": "required"}],
            [{"skill_name": "  "}],
            [{"skill_name": "Python", "canonical_uri": 42}],
        )
        for requirements in invalid:
            with self.subTest(requirements=requirements):
                with self.assertRaises(ValueError):
                    match_job_requirements([], requirements, job_id=1, pipeline_run_id=2)

    @patch("AI.Skill_Extraction.esco_taxonomy.get_esco_taxonomy")
    def test_matching_uses_only_resolvable_equal_canonical_uris(self, get_taxonomy):
        valid_uri = "https://example.test/esco/skill/valid"
        fake_taxonomy = SimpleNamespace(
            get_skill_by_uri=lambda uri: (
                SimpleNamespace(concept_uri=uri) if uri == valid_uri else None
            )
        )
        get_taxonomy.return_value = fake_taxonomy
        result = match_job_requirements(
            [{"skill": "Candidate label"}],
            [{"skill_name": "Different requirement label", "canonical_uri": valid_uri}],
            job_id=1, pipeline_run_id=2,
            candidate_mappings=[{"skill": "Candidate label", "ESCO_Skill_Id": valid_uri}],
        )
        requirement = result["requirements"][0]
        self.assertTrue(requirement["matched"])
        self.assertEqual(requirement["match_status"], "confirmed_match")
        self.assertEqual(requirement["candidate_skill"], "Candidate label")
        self.assertEqual(result["canonical_uri_matching"], "used")

    @patch("AI.Skill_Extraction.esco_taxonomy.get_esco_taxonomy")
    def test_invalid_or_unlinked_canonical_uri_falls_back_to_skill_names(self, get_taxonomy):
        get_taxonomy.return_value = SimpleNamespace(get_skill_by_uri=lambda _uri: None)
        matcher = StubMatcher()
        result = match_job_requirements(
            [{"skill": "Python"}],
            [{"skill_name": "Python", "canonical_uri": "unresolvable"}],
            job_id=1, pipeline_run_id=2, matcher=matcher,
            candidate_mappings=[{"skill": "Python", "ESCO_Skill_Id": "also-invalid"}],
        )
        self.assertEqual(matcher.received[1], ["Python"])
        self.assertEqual(result["canonical_uri_matching"], "unresolved_or_unmatched")
        self.assertEqual(result["requirements"][0]["match_status"], "non_match")


if __name__ == "__main__":
    unittest.main()
