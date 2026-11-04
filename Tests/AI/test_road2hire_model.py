"""Tests for the central Road2Hire model pipeline (Phase 3).

Covers:
- Model initialisation
- predict() happy-path integration on the sample résumé
- Input validation (missing file, non-PDF)
- Empty / OCR-only PDF handling
- Each major pipeline stage (skill extraction, ESCO normalisation,
  occupation matching, candidate profile)
- Structured output keys
- Profile validation errors propagated correctly
- Module-level singleton helper
- top_n_occupations parameter
- Occupation matching aggregation logic (unit-level)
"""

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Project root on sys.path so "AI.*" imports resolve.
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SAMPLE_PDF = PROJECT_ROOT / "Tests" / "AI" / "sample_resume.pdf"

# ---------------------------------------------------------------------------
# Required output keys for predict()
# ---------------------------------------------------------------------------

REQUIRED_OUTPUT_KEYS = {
    "status",
    "pipeline_version",
    "source_file",
    "page_count",
    "extraction_status",
    "sections",
    "section_count",
    "detected_headings",
    "extracted_skills",
    "skill_count",
    "esco_mappings",
    "mapped_skill_count",
    "occupation_matches",
    "candidate_profile",
    "profile_validation_errors",
    "warnings",
    "errors",
}

REQUIRED_PROFILE_KEYS = {
    "schema_version",
    "source_file",
    "candidate",
    "skills",
    "education",
    "experience",
    "projects",
    "certifications",
    "metadata",
}


# ===========================================================================
# Helper: minimal mock for Road2HireModel internals
# ===========================================================================


def _make_minimal_resume_data():
    return {
        "source_file": str(SAMPLE_PDF),
        "page_count": 1,
        "character_count": 100,
        "extraction_status": "success",
        "text": "Python SQL Git",
        "pages": [{"page_number": 1, "text": "Python SQL Git"}],
        "sections": {"skills": "Python SQL Git", "experience": "", "education": ""},
        "detected_headings": ["Skills"],
        "detected_section_names": ["skills"],
        "section_count": 3,
        "section_detection_method": "pattern",
        "pipeline_version": "1.0.0",
    }


def _make_minimal_extracted():
    return {
        "source_file": str(SAMPLE_PDF),
        "extraction_method": "knowledge_graph_keyword_matching",
        "skills": [{"skill": "Python (computer programming)", "source_sections": ["skills"], "occurrences": []}],
        "skill_count": 1,
    }


def _make_minimal_esco_mappings():
    return [
        {
            "skill": "Python (computer programming)",
            "source_sections": ["skills"],
            "occurrences": [],
            "ESCO_Skill_Id": "http://data.europa.eu/esco/skill/4c5b2a62-5a76-4d99-a7a8-cbf04e9e8d1e",
            "ESCO_Skill_Name": "Python (computer programming)",
            "ESCO_Skill_Type": "skill/competence",
            "ESCO_Reuse_Level": "cross-sector",
            "ESCO_Mapping_Type": "exact_preferred",
        }
    ]


def _make_minimal_embedding_data():
    return {
        "model_name": "sentence-transformers/all-MiniLM-L6-v2",
        "embedding_dimension": 384,
        "skills": [
            {
                "skill": "Python (computer programming)",
                "embedding": [0.0] * 384,
            }
        ],
    }


# ===========================================================================
# Test classes
# ===========================================================================


class TestModelInitialisation(unittest.TestCase):
    """Road2HireModel can be constructed without errors."""

    def test_model_instantiates(self):
        """Importing and creating Road2HireModel raises no exception."""
        from AI.road2hire_model import Road2HireModel

        model = Road2HireModel()
        self.assertIsNotNone(model)

    def test_model_has_taxonomy(self):
        """The model exposes a loaded ESCO taxonomy after init."""
        from AI.road2hire_model import Road2HireModel

        model = Road2HireModel()
        self.assertIsNotNone(model._taxonomy)

    def test_model_has_graph(self):
        """The model exposes a loaded ESCO knowledge graph after init."""
        from AI.road2hire_model import Road2HireModel

        model = Road2HireModel()
        self.assertIsNotNone(model._graph)

    def test_pipeline_version_constant(self):
        """PIPELINE_VERSION is set to 3.0.0."""
        from AI.road2hire_model import PIPELINE_VERSION

        self.assertEqual(PIPELINE_VERSION, "3.0.0")

    def test_singleton_helper(self):
        """get_road2hire_model returns the same instance on repeated calls."""
        # Reset singleton first so the test is deterministic
        import AI.road2hire_model as _mod

        _mod._model_singleton = None

        from AI.road2hire_model import get_road2hire_model

        m1 = get_road2hire_model()
        m2 = get_road2hire_model()
        self.assertIs(m1, m2)


class TestPredictInputValidation(unittest.TestCase):
    """predict() raises the correct exceptions for bad inputs."""

    @classmethod
    def setUpClass(cls):
        from AI.road2hire_model import Road2HireModel

        cls.model = Road2HireModel()

    def test_missing_file_raises_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            self.model.predict("nonexistent_path/fake.pdf")

    def test_non_pdf_extension_raises_value_error(self):
        # Create a temporary non-PDF file so the existence check passes.
        import tempfile, os

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(b"not a pdf")
            tmp_path = tmp.name

        try:
            with self.assertRaises(ValueError):
                self.model.predict(tmp_path)
        finally:
            os.unlink(tmp_path)

    def test_path_object_accepted(self):
        """predict() accepts pathlib.Path objects, not just strings."""
        with self.assertRaises(FileNotFoundError):
            # Non-existent path given as Path — should still raise FNFE
            self.model.predict(Path("definitely/does/not/exist.pdf"))


class TestPredictSampleResume(unittest.TestCase):
    """Integration test on the real sample résumé."""

    @classmethod
    def setUpClass(cls):
        from AI.road2hire_model import Road2HireModel

        cls.model = Road2HireModel()
        cls.result = cls.model.predict(str(SAMPLE_PDF))

    def test_status_is_success_or_warning(self):
        self.assertIn(self.result["status"], {"success", "warning"})

    def test_all_required_keys_present(self):
        missing = REQUIRED_OUTPUT_KEYS - self.result.keys()
        self.assertSetEqual(missing, set(), msg=f"Missing output keys: {missing}")

    def test_pipeline_version_in_result(self):
        self.assertEqual(self.result["pipeline_version"], "3.0.0")

    def test_source_file_is_string(self):
        self.assertIsInstance(self.result["source_file"], str)

    def test_page_count_positive(self):
        self.assertGreater(self.result["page_count"], 0)

    def test_sections_is_dict(self):
        self.assertIsInstance(self.result["sections"], dict)

    def test_extracted_skills_is_list(self):
        self.assertIsInstance(self.result["extracted_skills"], list)

    def test_skill_count_non_negative(self):
        self.assertGreaterEqual(self.result["skill_count"], 0)

    def test_esco_mappings_is_list(self):
        self.assertIsInstance(self.result["esco_mappings"], list)

    def test_mapped_skill_count_matches_list(self):
        self.assertEqual(
            self.result["mapped_skill_count"],
            len(self.result["esco_mappings"]),
        )

    def test_occupation_matches_is_list(self):
        self.assertIsInstance(self.result["occupation_matches"], list)

    def test_occupation_matches_capped_at_top_n(self):
        self.assertLessEqual(len(self.result["occupation_matches"]), 10)

    def test_warnings_is_list(self):
        self.assertIsInstance(self.result["warnings"], list)

    def test_errors_is_list(self):
        self.assertIsInstance(self.result["errors"], list)

    def test_profile_validation_errors_is_list(self):
        self.assertIsInstance(self.result["profile_validation_errors"], list)


class TestCandidateProfileIntegration(unittest.TestCase):
    """candidate_profile has the correct CandidateProfile schema."""

    @classmethod
    def setUpClass(cls):
        from AI.road2hire_model import Road2HireModel

        cls.model = Road2HireModel()
        cls.result = cls.model.predict(str(SAMPLE_PDF))
        cls.profile = cls.result["candidate_profile"]

    def test_profile_is_dict(self):
        self.assertIsInstance(self.profile, dict)

    def test_required_profile_keys(self):
        missing = REQUIRED_PROFILE_KEYS - self.profile.keys()
        self.assertSetEqual(missing, set(), msg=f"Missing profile keys: {missing}")

    def test_schema_version(self):
        self.assertEqual(self.profile["schema_version"], "1.0.0")

    def test_skills_is_list(self):
        self.assertIsInstance(self.profile["skills"], list)

    def test_metadata_pipeline_version(self):
        self.assertEqual(self.profile["metadata"]["pipeline_version"], "3.0.0")

    def test_metadata_embedding_dimension(self):
        self.assertEqual(self.profile["metadata"]["embedding_dimension"], 384)

    def test_profile_passes_validator(self):
        from AI.Candidate_Profile.profile_validator import validate_candidate_profile

        errors = validate_candidate_profile(self.profile)
        self.assertEqual(errors, [], msg=f"Validator errors: {errors}")

    def test_no_pipeline_validation_errors_in_result(self):
        """Profile validation errors list in result must be empty."""
        self.assertEqual(self.result["profile_validation_errors"], [])


class TestEscoMappingIntegration(unittest.TestCase):
    """Every ESCO mapping entry has the expected fields."""

    @classmethod
    def setUpClass(cls):
        from AI.road2hire_model import Road2HireModel

        cls.model = Road2HireModel()
        result = cls.model.predict(str(SAMPLE_PDF))
        cls.mappings = result["esco_mappings"]

    def test_all_mappings_have_esco_mapping_type(self):
        for m in self.mappings:
            self.assertIn(
                "ESCO_Mapping_Type",
                m,
                msg=f"Missing ESCO_Mapping_Type in {m}",
            )

    def test_mapping_types_are_known_values(self):
        valid_types = {"exact_preferred", "alternative_label", "unmapped"}
        for m in self.mappings:
            self.assertIn(
                m.get("ESCO_Mapping_Type"),
                valid_types,
                msg=f"Unexpected mapping type: {m.get('ESCO_Mapping_Type')}",
            )

    def test_mapped_skills_have_esco_id(self):
        """Skills that are not 'unmapped' must carry a non-empty ESCO URI."""
        for m in self.mappings:
            if m.get("ESCO_Mapping_Type") != "unmapped":
                self.assertTrue(
                    bool(m.get("ESCO_Skill_Id")),
                    msg=f"Mapped skill missing ESCO_Skill_Id: {m}",
                )


class TestOccupationMatchingUnit(unittest.TestCase):
    """Unit-level tests for _match_occupations using a mocked graph."""

    def setUp(self):
        from AI.road2hire_model import Road2HireModel

        self.model = Road2HireModel()

    def test_empty_mappings_returns_empty_list(self):
        result = self.model._match_occupations([])
        self.assertEqual(result, [])

    def test_unmapped_skills_skipped(self):
        """Skills with no ESCO URI must not query the graph."""
        unmapped = [
            {
                "skill": "FakeSkill",
                "ESCO_Skill_Id": "",
                "ESCO_Mapping_Type": "unmapped",
            }
        ]
        result = self.model._match_occupations(unmapped)
        self.assertEqual(result, [])

    def test_occupation_ranked_by_score(self):
        """Occupations with higher skill overlap rank first."""
        occ_a = {
            "occupation_uri": "http://esco/occ/A",
            "occupation_label": "Occupation A",
            "relation_type": "essential",
        }
        occ_b = {
            "occupation_uri": "http://esco/occ/B",
            "occupation_label": "Occupation B",
            "relation_type": "optional",
        }

        def fake_get_occupations(uri):
            if "skill1" in uri:
                return [occ_a, occ_b]
            return [occ_a]  # skill2 only links to A

        self.model._graph.get_occupations_for_skill = fake_get_occupations

        mappings = [
            {"skill": "Skill1", "ESCO_Skill_Id": "http://esco/skill1", "ESCO_Mapping_Type": "exact_preferred", "ESCO_Skill_Name": "Skill1"},
            {"skill": "Skill2", "ESCO_Skill_Id": "http://esco/skill2", "ESCO_Mapping_Type": "exact_preferred", "ESCO_Skill_Name": "Skill2"},
        ]
        ranked = self.model._match_occupations(mappings)
        # A should be first with score 2, B second with score 1
        self.assertGreaterEqual(len(ranked), 2)
        self.assertEqual(ranked[0]["occupation_uri"], "http://esco/occ/A")
        self.assertEqual(ranked[0]["score"], 2)
        self.assertEqual(ranked[1]["occupation_uri"], "http://esco/occ/B")

    def test_top_n_respected(self):
        """predict() truncates occupation matches to top_n_occupations."""
        import AI.road2hire_model as _mod

        small_model = _mod.Road2HireModel(top_n_occupations=3)

        # Give it enough occupation matches to test truncation
        occs = [
            {"occupation_uri": f"http://esco/occ/{i}", "occupation_label": f"Occ {i}", "relation_type": "optional"}
            for i in range(10)
        ]
        small_model._graph.get_occupations_for_skill = lambda uri: occs

        mappings = [
            {"skill": "S", "ESCO_Skill_Id": "http://esco/s1", "ESCO_Mapping_Type": "exact_preferred", "ESCO_Skill_Name": "S"},
        ]
        # Call _match_occupations, then apply truncation as predict() does
        all_matches = small_model._match_occupations(mappings)
        truncated = all_matches[: small_model._top_n]
        self.assertLessEqual(len(truncated), 3)


class TestProfileValidationErrorPropagation(unittest.TestCase):
    """profile_validation_errors are populated when the profile is invalid."""

    def test_invalid_profile_errors_propagated(self):
        """When _build_profile returns a broken profile, errors appear in result."""
        from AI.road2hire_model import Road2HireModel

        model = Road2HireModel()

        broken_profile = {"schema_version": "1.0.0"}  # missing required keys

        with patch.object(model, "_run_resume_processing", return_value=_make_minimal_resume_data()), \
             patch.object(model, "_run_skill_extraction", return_value=_make_minimal_extracted()), \
             patch.object(model, "_run_esco_normalisation", return_value=_make_minimal_esco_mappings()), \
             patch.object(model, "_run_embeddings", return_value=_make_minimal_embedding_data()), \
             patch.object(model, "_match_occupations", return_value=[]), \
             patch.object(model, "_build_profile", return_value=broken_profile):

            result = model.predict(str(SAMPLE_PDF))

        self.assertGreater(len(result["profile_validation_errors"]), 0)


class TestEmptyTextHandling(unittest.TestCase):
    """predict() handles PDFs that yield no readable text gracefully."""

    def test_empty_pdf_does_not_crash(self):
        from AI.road2hire_model import Road2HireModel

        model = Road2HireModel()

        empty_resume = _make_minimal_resume_data()
        empty_resume["text"] = ""
        empty_resume["sections"] = {}
        empty_resume["extraction_status"] = "needs_ocr"

        with patch.object(model, "_run_resume_processing", return_value=empty_resume), \
             patch.object(model, "_run_skill_extraction", return_value={"skills": [], "skill_count": 0, "source_file": ""}), \
             patch.object(model, "_run_esco_normalisation", return_value=[]), \
             patch.object(model, "_run_embeddings", return_value={"model_name": "m", "embedding_dimension": 384, "skills": []}), \
             patch.object(model, "_match_occupations", return_value=[]):

            result = model.predict(str(SAMPLE_PDF))

        self.assertIn(result["status"], {"warning", "error"})
        self.assertIsInstance(result["warnings"], list)
        self.assertGreater(len(result["warnings"]), 0)


if __name__ == "__main__":
    unittest.main()

