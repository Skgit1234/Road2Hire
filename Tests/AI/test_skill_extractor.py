"""Automated tests for Road2Hire skill extraction, normalization, and embeddings."""

import pytest

from AI.Skill_Extraction.skill_extractor import (
    extract_skills,
    load_skill_vocabulary,
    normalize_skill_name,
)
from AI.Skill_Extraction.skill_taxonomy_mapper import (
    load_esco_mapping,
    map_skills_to_esco,
)
from AI.Skill_Extraction.skill_embeddings import (
    cosine_similarity,
    generate_skill_embeddings,
)


def test_load_skill_vocabulary():
    vocabulary = load_skill_vocabulary()

    assert "Python" in vocabulary
    assert "Machine Learning" in vocabulary
    assert "NumPy" in vocabulary
    assert "Pandas" in vocabulary
    assert "Scikit-learn" in vocabulary

    assert "SQL" in vocabulary
    assert "Git" in vocabulary
    assert "REST APIs" in vocabulary
    assert "Data Analysis" in vocabulary


def test_normalize_skill_aliases():
    assert normalize_skill_name("python") == "Python"
    assert normalize_skill_name("ML") == "Machine Learning"
    assert normalize_skill_name("sklearn") == "Scikit-learn"
    assert normalize_skill_name("scikit learn") == "Scikit-learn"


def test_unknown_skill_returns_none():
    assert normalize_skill_name("unknown skill") is None


def test_extract_skills_from_resume_sections():
    resume_data = {
        "source_file": "test_resume.pdf",
        "sections": {
            "skills": "Python, ML, NumPy, Pandas, sklearn"
        },
    }

    result = extract_skills(resume_data)
    extracted_names = {item["skill"] for item in result["skills"]}

    assert extracted_names == {
        "Python",
        "Machine Learning",
        "NumPy",
        "Pandas",
        "Scikit-learn",
    }
    assert result["skill_count"] == 5


def test_unknown_text_returns_no_skills():
    resume_data = {
        "sections": {
            "skills": "Communication, teamwork, problem solving"
        }
    }

    result = extract_skills(resume_data)

    assert result["skills"] == []
    assert result["skill_count"] == 0


def test_contact_information_is_ignored():
    resume_data = {
        "sections": {
            "contact_information": "Python developer",
            "skills": "Pandas and NumPy",
        }
    }

    result = extract_skills(resume_data)
    extracted_names = {item["skill"] for item in result["skills"]}

    assert extracted_names == {"Pandas", "NumPy"}
    assert "Python" not in extracted_names


def test_load_esco_mapping():
    mappings = load_esco_mapping()

    assert mappings["python"]["Mapping_Type"] == "exact_concept"
    assert mappings["python"]["ESCO_Skill_Id"].startswith(
        "http://data.europa.eu/esco/skill/"
    )
    assert mappings["machine learning"]["Mapping_Type"] == "exact_concept"


def test_map_extracted_skills_to_esco():
    extracted_skills = [
        {
            "skill": "Python",
            "source_sections": ["skills"],
            "occurrences": [],
        },
        {
            "skill": "Machine Learning",
            "source_sections": ["projects"],
            "occurrences": [],
        },
        {
            "skill": "NumPy",
            "source_sections": ["skills"],
            "occurrences": [],
        },
    ]

    mapped = map_skills_to_esco(extracted_skills)
    by_name = {item["skill"]: item for item in mapped}

    assert (
        by_name["Python"]["ESCO_Skill_Name"]
        == "Python (computer programming)"
    )
    assert by_name["Machine Learning"]["ESCO_Mapping_Type"] == "exact_concept"
    assert by_name["NumPy"]["ESCO_Mapping_Type"] == "unmapped"
    assert by_name["NumPy"]["ESCO_Skill_Id"] == ""


def test_esco_mapping_preserves_extraction_details():
    extracted_skills = [
        {
            "skill": "Python",
            "source_sections": ["skills"],
            "occurrences": [
                {
                    "section": "skills",
                    "text": "Python",
                    "start": 0,
                    "end": 6,
                }
            ],
        }
    ]

    mapped = map_skills_to_esco(extracted_skills)

    assert mapped[0]["source_sections"] == ["skills"]
    assert mapped[0]["occurrences"] == extracted_skills[0]["occurrences"]


def test_cosine_similarity():
    similarity = cosine_similarity(
        [1.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
    )

    assert abs(similarity - 1.0) < 1e-9


def test_cosine_similarity_rejects_mismatched_dimensions():
    with pytest.raises(ValueError, match="equal dimensions"):
        cosine_similarity([1.0, 0.0], [1.0])


def test_generate_skill_embeddings():
    result = generate_skill_embeddings(["Python", "Machine Learning"])

    assert result["model_name"] == "sentence-transformers/all-MiniLM-L6-v2"
    assert result["embedding_dimension"] == 384
    assert len(result["skills"]) == 2

    for item in result["skills"]:
        assert len(item["embedding"]) == 384
        assert all(isinstance(value, float) for value in item["embedding"])


def test_generate_skill_embeddings_removes_duplicates():
    result = generate_skill_embeddings(
        ["Python", "Python", "Machine Learning"]
    )

    names = [item["skill"] for item in result["skills"]]

    assert names == ["Python", "Machine Learning"]


def test_generate_skill_embeddings_empty_input():
    result = generate_skill_embeddings([])

    assert result["skills"] == []
    assert result["embedding_dimension"] == 384


def test_extract_additional_skills():
    resume_data = {
        "source_file": "test_resume.pdf",
        "sections": {
            "skills": "SQL, Git, REST APIs, Data Analysis"
        },
    }

    result = extract_skills(resume_data)
    extracted_names = {item["skill"] for item in result["skills"]}

    assert extracted_names == {
        "SQL",
        "Git",
        "REST APIs",
        "Data Analysis",
    }
    assert result["skill_count"] == 4


def test_extract_all_skills_from_sample_resume():
    from AI.Resume_Processing.resume_pipeline import process_resume

    resume_data = process_resume("Tests/AI/sample_resume.pdf")
    result = extract_skills(resume_data)
    extracted_names = {item["skill"] for item in result["skills"]}

    assert extracted_names == {
        "Python",
        "SQL",
        "Git",
        "REST APIs",
        "Data Analysis",
    }
    assert result["skill_count"] == 5


def test_skill_matcher_word_boundaries_false_positive_prevention():
    """Verify that substring matches inside unrelated words are strictly prevented."""
    from AI.Skill_Extraction.skill_extractor import SkillMatcher

    vocab = ["C", "Java", "Rust", "Go", "R"]
    matcher = SkillMatcher(vocab)

    # Text containing words that embed those short skill names
    text = "We trust our Category of Good JavaScript developers to read literature."
    matches = matcher.find_in_text(text)

    # None of the skills should match inside 'trust', 'Category', 'Good', 'JavaScript'
    assert "C" not in matches
    assert "Java" not in matches
    assert "Rust" not in matches
    assert "Go" not in matches

    # Now test valid boundaries
    valid_text = "Proficient in C, Java, and Rust; some Go experience."
    valid_matches = matcher.find_in_text(valid_text)
    assert "C" in valid_matches
    assert "Java" in valid_matches
    assert "Rust" in valid_matches
    assert "Go" in valid_matches


def test_skill_matcher_synonym_resolution():
    """Verify that configured synonyms resolve to canonical skill names."""
    from AI.Skill_Extraction.skill_extractor import extract_skills

    resume_data = {
        "sections": {
            "skills": "Experienced in ML, sklearn, and numpy for predictive modeling."
        }
    }
    result = extract_skills(resume_data, vocabulary=["Machine Learning", "Scikit-learn", "NumPy"])
    skills_found = {s["skill"] for s in result["skills"]}
    assert skills_found == {"Machine Learning", "Scikit-learn", "NumPy"}


def test_large_vocabulary_performance_benchmark():
    """Verify that full ESCO vocabulary matching (~100k items) runs in < 0.05 seconds with cached trie."""
    import time
    from AI.Skill_Extraction.esco_taxonomy import get_esco_taxonomy
    from AI.Skill_Extraction.skill_extractor import extract_skills, load_esco_skill_vocabulary

    tax = get_esco_taxonomy()
    esco_vocab = load_esco_skill_vocabulary(taxonomy=tax, include_alt_labels=True)
    assert len(esco_vocab) > 50000

    sample_resume_data = {
        "sections": {
            "skills": "Python, SQL, Git, Linux, Docker, PostgreSQL, Data Analysis",
            "experience": "Senior software engineer building backend services using Python and SQL databases.",
        }
    }

    # Warm-up call builds and caches the trie
    extract_skills(sample_resume_data, vocabulary=esco_vocab)

    # Benchmark cached search execution
    t0 = time.perf_counter()
    result = extract_skills(sample_resume_data, vocabulary=esco_vocab)
    elapsed = time.perf_counter() - t0

    assert elapsed < 0.05, f"Cached skill extraction took {elapsed:.4f}s, expected < 0.05s"
    assert result["skill_count"] > 0
