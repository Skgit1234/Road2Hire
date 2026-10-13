"""Automated tests for Road2Hire skill extraction and normalization."""

from AI.Skill_Extraction.skill_extractor import (
    extract_skills,
    load_skill_vocabulary,
    normalize_skill_name,
)


def test_load_skill_vocabulary():
    vocabulary = load_skill_vocabulary()

    assert "Python" in vocabulary
    assert "Machine Learning" in vocabulary
    assert "NumPy" in vocabulary
    assert "Pandas" in vocabulary
    assert "Scikit-learn" in vocabulary


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
