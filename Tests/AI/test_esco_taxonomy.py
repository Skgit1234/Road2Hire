"""Automated tests for complete ESCO Taxonomy loading, indexing, caching, and relations."""

import pytest
from pathlib import Path

from AI.Skill_Extraction.esco_taxonomy import (
    DEFAULT_ESCO_DIR,
    ESCOSkill,
    ESCOTaxonomy,
    get_esco_taxonomy,
    normalize_skill_label,
)
from AI.Skill_Extraction.skill_taxonomy_mapper import (
    map_skills_to_complete_esco,
    map_skills_to_esco,
)
from AI.Skill_Extraction.skill_extractor import load_esco_skill_vocabulary


@pytest.fixture(scope="module")
def taxonomy() -> ESCOTaxonomy:
    """Load the complete ESCO taxonomy once for the test module."""
    return get_esco_taxonomy()


def test_esco_raw_directory_exists():
    assert DEFAULT_ESCO_DIR.is_dir()
    required_files = [
        "skills_en.csv",
        "skillSkillRelations_en.csv",
        "broaderRelationsSkillPillar_en.csv",
        "occupations_en.csv",
        "occupationSkillRelations_en.csv",
        "skillGroups_en.csv",
    ]
    for filename in required_files:
        assert (DEFAULT_ESCO_DIR / filename).is_file()


def test_complete_skill_counts(taxonomy: ESCOTaxonomy):
    report = taxonomy.get_report()

    # Raw ESCO has 13,960 skill rows and 13,939 unique concept URIs
    assert report.skills_raw_count == 13960
    assert report.skills_unique_count == 13939
    assert len(taxonomy.skills) == 13939


def test_duplicate_skill_uris_handled(taxonomy: ESCOTaxonomy):
    report = taxonomy.get_report()

    # 21 duplicate concept URIs in raw ESCO CSV
    assert report.duplicate_skill_uris_count == 21
    assert len(report.duplicate_skill_uris) == 21

    # Verify that each duplicate URI is present exactly once in the indexed dictionary
    for dup_uri in report.duplicate_skill_uris:
        assert dup_uri in taxonomy.skills
        assert isinstance(taxonomy.skills[dup_uri], ESCOSkill)


def test_alternative_labels_loaded(taxonomy: ESCOTaxonomy):
    report = taxonomy.get_report()

    assert report.alt_labels_total_count > 80000
    assert report.skills_with_alt_labels_count > 13900


def test_descriptions_loaded(taxonomy: ESCOTaxonomy):
    report = taxonomy.get_report()

    # 100% of deduplicated skills have non-empty descriptions
    assert report.skills_with_description_count == 13939


def test_missing_fields_reporting(taxonomy: ESCOTaxonomy):
    report = taxonomy.get_report()

    # In ESCO skills_en.csv, 5 DigComp concepts have empty skillType and reuseLevel
    assert report.missing_fields_summary["conceptUri"] == 0
    assert report.missing_fields_summary["preferredLabel"] == 0
    assert report.missing_fields_summary["description"] == 0
    assert report.missing_fields_summary["skillType"] == 5
    assert report.missing_fields_summary["reuseLevel"] == 5


def test_find_skill_by_preferred_label(taxonomy: ESCOTaxonomy):
    skill = taxonomy.find_skill("Python (computer programming)")
    assert skill is not None
    assert skill.preferred_label == "Python (computer programming)"
    assert skill.skill_type == "knowledge"

    ml_skill = taxonomy.find_skill("machine learning")
    assert ml_skill is not None
    assert ml_skill.preferred_label == "machine learning"


def test_find_skill_by_alternative_label(taxonomy: ESCOTaxonomy):
    # 'sports medicine' is an alternative label for 'sport and exercise medicine'
    skill = taxonomy.find_skill("sports medicine")
    assert skill is not None
    assert skill.preferred_label == "sport and exercise medicine"


def test_find_skill_case_and_whitespace_insensitivity(taxonomy: ESCOTaxonomy):
    skill1 = taxonomy.find_skill("  python (computer programming)  ")
    skill2 = taxonomy.find_skill("PYTHON (COMPUTER PROGRAMMING)")
    assert skill1 is not None
    assert skill2 is not None
    assert skill1.concept_uri == skill2.concept_uri


def test_skill_skill_relations_loaded(taxonomy: ESCOTaxonomy):
    report = taxonomy.get_report()

    # 5,818 skill-to-skill relations in raw ESCO
    assert report.skill_skill_relations_count == 5818
    assert report.skill_skill_relation_types["optional"] == 5629
    assert report.skill_skill_relation_types["essential"] == 189

    # Test related skills for Python (has incoming relation from 'use scripting programming')
    py_skill = taxonomy.find_skill("Python (computer programming)")
    assert py_skill is not None
    related = taxonomy.get_related_skills(py_skill.concept_uri, direction="both")
    assert len(related) > 0
    assert any("scripting" in r["preferred_label"].lower() for r in related)


def test_broader_and_narrower_skill_hierarchy(taxonomy: ESCOTaxonomy):
    report = taxonomy.get_report()

    assert report.broader_relations_total == 20819
    assert report.broader_skill_to_skill_count == 6460

    # Python has broader skill 'computer programming'
    py_skill = taxonomy.find_skill("Python (computer programming)")
    assert py_skill is not None
    broader = taxonomy.get_broader_skills(py_skill.concept_uri)
    assert any(s.preferred_label == "computer programming" for s in broader)

    # 'computer programming' has narrower skill 'Python (computer programming)'
    cp_skill = taxonomy.find_skill("computer programming")
    assert cp_skill is not None
    narrower = taxonomy.get_narrower_skills(cp_skill.concept_uri)
    assert any(s.concept_uri == py_skill.concept_uri for s in narrower)


def test_occupations_and_relations_loaded(taxonomy: ESCOTaxonomy):
    report = taxonomy.get_report()

    assert report.occupations_unique_count == 3039
    assert report.occupation_skill_relations_total == 126051
    assert report.essential_occupation_skill_relations_count == 67600
    assert report.optional_occupation_skill_relations_count == 58451

    # Check skills for 'data scientist' occupation
    ds_skills = taxonomy.get_skills_for_occupation("data scientist")
    assert len(ds_skills) > 0
    # Must have both essential and optional skills
    essential = [s for s in ds_skills if s["relation_type"] == "essential"]
    optional = [s for s in ds_skills if s["relation_type"] == "optional"]
    assert len(essential) > 0
    assert len(optional) > 0


def test_get_complete_vocabulary(taxonomy: ESCOTaxonomy):
    vocab = taxonomy.get_vocabulary(include_alt_labels=False)
    assert len(vocab) == 13939
    assert "Python (computer programming)" in vocab
    assert "machine learning" in vocab

    vocab_with_alts = taxonomy.get_vocabulary(include_alt_labels=True)
    assert len(vocab_with_alts) > 90000


def test_load_esco_skill_vocabulary_helper():
    vocab = load_esco_skill_vocabulary()
    assert len(vocab) == 13939


def test_map_skills_to_complete_esco(taxonomy: ESCOTaxonomy):
    input_skills = [
        {"skill": "Python (computer programming)"},
        {"skill": "sports medicine"},
        {"skill": "nonexistent skill xyz"},
    ]

    mapped = map_skills_to_complete_esco(input_skills, taxonomy=taxonomy)
    assert len(mapped) == 3

    # Exact preferred match
    assert mapped[0]["ESCO_Mapping_Type"] == "exact_preferred"
    assert mapped[0]["ESCO_Skill_Name"] == "Python (computer programming)"

    # Alternative label match
    assert mapped[1]["ESCO_Mapping_Type"] == "alternative_label"
    assert mapped[1]["ESCO_Skill_Name"] == "sport and exercise medicine"

    # Unmapped
    assert mapped[2]["ESCO_Mapping_Type"] == "unmapped"
    assert mapped[2]["ESCO_Skill_Id"] == ""


def test_singleton_caching_performance():
    import time
    t0 = time.perf_counter()
    inst1 = get_esco_taxonomy()
    inst2 = get_esco_taxonomy()
    dur = time.perf_counter() - t0

    assert inst1 is inst2
    # Cached access should take less than 5 milliseconds
    assert dur < 0.005
