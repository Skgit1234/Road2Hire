"""Tests for Road2Hire candidate profile integration."""

from AI.Candidate_Profile.profile_validator import validate_candidate_profile


def sample_profile():
    return {
        "schema_version": "1.0.0",
        "source_file": "sample_resume.pdf",
        "candidate": {},
        "skills": [
            {
                "skill": "Python",
                "ESCO_Skill_Id": "",
                "ESCO_Skill_Name": "",
                "ESCO_Mapping_Type": "unmapped",
                "embedding": [0.1, 0.2],
            }
        ],
        "education": [],
        "experience": [],
        "projects": [],
        "certifications": [],
        "metadata": {"skill_count": 1},
    }


def test_valid_profile_has_no_errors():
    assert validate_candidate_profile(sample_profile()) == []


def test_missing_required_field_is_reported():
    profile = sample_profile()
    del profile["skills"]

    errors = validate_candidate_profile(profile)

    assert any("skills" in error for error in errors)


def test_invalid_skills_type_is_reported():
    profile = sample_profile()
    profile["skills"] = "Python"

    errors = validate_candidate_profile(profile)

    assert any("'skills' must be a list" in error for error in errors)


def test_duplicate_skills_are_reported():
    profile = sample_profile()
    profile["skills"].append(profile["skills"][0].copy())

    errors = validate_candidate_profile(profile)

    assert any("Duplicate skills" in error for error in errors)


def test_invalid_embedding_type_is_reported():
    profile = sample_profile()
    profile["skills"][0]["embedding"] = "not-a-vector"

    errors = validate_candidate_profile(profile)

    assert any("Embedding" in error for error in errors)
def test_build_candidate_profile_from_sample_resume():
    from pathlib import Path
    from AI.Candidate_Profile.profile_builder import build_candidate_profile

    resume_path = Path("Tests/AI/sample_resume.pdf")
    profile = build_candidate_profile(resume_path)

    assert profile["schema_version"] == "1.0.0"
    assert profile["source_file"] is not None
    assert isinstance(profile["skills"], list)
    assert isinstance(profile["metadata"], dict)
    assert profile["metadata"]["embedding_dimension"] == 384
def test_profile_preserves_detected_section_text():
    from pathlib import Path
    from AI.Candidate_Profile.profile_builder import build_candidate_profile

    profile = build_candidate_profile(Path("Tests/AI/sample_resume.pdf"))

    assert isinstance(profile["candidate"]["raw_contact_information"], str)
    assert isinstance(profile["candidate"]["raw_summary"], str)
    assert isinstance(profile["metadata"]["sections_available"], list)
    assert profile["metadata"]["section_content_is_raw"] is True

    for section in ("education", "experience", "projects", "certifications"):
        assert isinstance(profile[section], list)
