"""Tests for Road2Hire candidate profile integration (Phase 4).

Covers:
- Base profile validation and backward compatibility
- Schema version 1.1.0 verification
- Basic candidate info extraction (name, email, phone, location, summary)
- Education structuring (degrees, institutions, dates, grades, multi-record)
- Experience structuring (job title, organization, dates, responsibilities, tools, empty for freshers)
- Projects structuring (name, description, tools, contributions, multiple projects)
- Certifications structuring (name, issuing organization, dates, credential ID)
- Invalid data rejection (invalid dates, invalid scores, duplicate skills)
- Comprehensive validation (distinguishing errors from warnings)
- Pipeline integration from sample resume
"""

from pathlib import Path
from typing import Any

from AI.Candidate_Profile.profile_builder import (
    assemble_candidate_profile,
    build_candidate_profile,
)
from AI.Candidate_Profile.profile_schema import SCHEMA_VERSION
from AI.Candidate_Profile.profile_validator import (
    validate_candidate_profile,
    validate_candidate_profile_comprehensive,
)
from AI.Candidate_Profile.section_parsers import (
    extract_candidate_info,
    parse_certifications_section,
    parse_education_section,
    parse_experience_section,
    parse_projects_section,
)

SAMPLE_RESUME_PATH = Path("Tests/AI/sample_resume.pdf")


def sample_profile() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "source_file": "sample_resume.pdf",
        "candidate": {
            "name": "Alex Morgan",
            "email": "alex.morgan@example.com",
            "phone": "+1-555-010-2040",
            "location": "Pune, India",
            "summary": "Software engineer with background in Python and data analysis.",
            "raw_contact_information": "Alex Morgan | alex.morgan@example.com | +1-555-010-2040",
            "raw_summary": "Software engineer with background in Python and data analysis.",
        },
        "skills": [
            {
                "skill": "Python",
                "ESCO_Skill_Id": "http://data.europa.eu/esco/skill/4c5b2a62-5a76-4d99-a7a8-cbf04e9e8d1e",
                "ESCO_Skill_Name": "Python (computer programming)",
                "ESCO_Mapping_Type": "exact_preferred",
                "embedding": [0.1, 0.2],
            }
        ],
        "education": [
            {
                "degree": "Bachelor of Technology in Computer Science",
                "field_of_study": "Computer Science",
                "institution": "Example Institute",
                "start_year": 2022,
                "end_year": 2026,
                "cgpa": 8.5,
                "percentage": None,
                "academic_level": "bachelor",
                "raw_text": "Bachelor of Technology in Computer Science\nExample Institute | 2022 - 2026\nCGPA: 8.5/10",
            }
        ],
        "experience": [
            {
                "job_title": "Software Development Intern",
                "organization": "Example Technologies",
                "employment_type": "internship",
                "start_date": "January 2026",
                "end_date": "June 2026",
                "responsibilities": ["Developed Python scripts", "Used Git"],
                "skills_used": ["Python", "Git"],
                "raw_text": "Software Development Intern | Example Technologies\nJanuary 2026 - June 2026",
            }
        ],
        "projects": [
            {
                "project_name": "Roadmap Planner",
                "description": "Built a project planner using Python.",
                "technologies": ["Python"],
                "responsibilities": ["Created structured outputs for project reports"],
                "related_skills": ["Python"],
                "raw_text": "Roadmap Planner\n- Built a project planner using Python.",
            }
        ],
        "certifications": [
            {
                "name": "Python Programming Certificate",
                "issuing_organization": "Example Learning Academy",
                "issue_date": "2025",
                "expiration_date": None,
                "credential_id": None,
                "raw_text": "Python Programming Certificate\nExample Learning Academy | 2025",
            }
        ],
        "metadata": {
            "page_count": 1,
            "extraction_status": "success",
            "section_count": 6,
            "detected_headings": ["EDUCATION", "EXPERIENCE", "SKILLS", "PROJECTS", "CERTIFICATIONS"],
            "skill_count": 1,
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            "embedding_dimension": 384,
            "sections_available": ["summary", "education", "experience", "skills", "projects", "certifications"],
            "section_content_is_raw": True,
            "pipeline_version": "1.0.0",
        },
    }


# ===========================================================================
# Baseline Validation Tests (Preserved & Enhanced)
# ===========================================================================

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
    profile = build_candidate_profile(SAMPLE_RESUME_PATH)

    assert profile["schema_version"] == "1.1.0"
    assert profile["source_file"] is not None
    assert isinstance(profile["skills"], list)
    assert isinstance(profile["metadata"], dict)
    assert profile["metadata"]["embedding_dimension"] == 384


def test_profile_preserves_detected_section_text():
    profile = build_candidate_profile(SAMPLE_RESUME_PATH)

    assert isinstance(profile["candidate"]["raw_contact_information"], str)
    assert isinstance(profile["candidate"]["raw_summary"], str)
    assert isinstance(profile["metadata"]["sections_available"], list)
    assert profile["metadata"]["section_content_is_raw"] is True

    for section in ("education", "experience", "projects", "certifications"):
        assert isinstance(profile[section], list)
        assert len(profile[section]) > 0
        assert "raw_text" in profile[section][0]


# ===========================================================================
# Phase 4: Candidate Information Tests
# ===========================================================================

def test_candidate_info_extraction_sample_resume():
    profile = build_candidate_profile(SAMPLE_RESUME_PATH)
    cand = profile["candidate"]

    assert cand["name"] == "Alex Morgan"
    assert cand["email"] == "alex.morgan@example.com"
    assert "+1-555-010-2040" in cand["phone"]
    assert "Pune" in cand["location"]
    assert "software development" in cand["summary"].lower()


def test_candidate_info_missing_fields_not_hallucinated():
    text = "Only summary text here."
    sections = {"summary": "Brief statement"}
    cand = extract_candidate_info(text, sections)

    assert cand["name"] is None
    assert cand["email"] is None
    assert cand["phone"] is None
    assert cand["location"] is None
    assert cand["summary"] == "Brief statement"


# ===========================================================================
# Phase 4: Education Extraction & Validation Tests
# ===========================================================================

def test_education_parsing_single_record():
    edu_text = """Bachelor of Technology in Computer Science
Example Institute | 2022 - 2026
CGPA: 8.8/10"""

    records = parse_education_section(edu_text)
    assert len(records) == 1
    rec = records[0]

    assert "Bachelor of Technology" in rec["degree"]
    assert rec["academic_level"] == "bachelor"
    assert "Computer Science" in rec["field_of_study"]
    assert "Example Institute" in rec["institution"]
    assert rec["start_year"] == 2022
    assert rec["end_year"] == 2026
    assert rec["cgpa"] == 8.8
    assert rec["raw_text"] == edu_text


def test_education_parsing_multiple_records():
    edu_text = """Master of Science in Data Analytics
Stanford University | 2024 - 2026
CGPA: 3.9

Bachelor of Engineering in Information Technology
Pune University | 2020 - 2024
Grade: 85%"""

    records = parse_education_section(edu_text)
    assert len(records) == 2

    assert records[0]["academic_level"] == "master"
    assert records[0]["start_year"] == 2024
    assert records[0]["end_year"] == 2026
    assert records[0]["cgpa"] == 3.9

    assert records[1]["academic_level"] == "bachelor"
    assert records[1]["start_year"] == 2020
    assert records[1]["end_year"] == 2024
    assert records[1]["percentage"] == 85.0


def test_education_validation_score_ranges():
    profile = sample_profile()
    profile["education"][0]["cgpa"] = 14.5  # Invalid CGPA > 10.0
    errors = validate_candidate_profile(profile)
    assert any("CGPA" in err for err in errors)

    profile["education"][0]["cgpa"] = 9.2
    profile["education"][0]["percentage"] = 110.0  # Invalid percentage > 100
    errors = validate_candidate_profile(profile)
    assert any("percentage" in err for err in errors)


def test_education_validation_chronological_order():
    profile = sample_profile()
    profile["education"][0]["start_year"] = 2026
    profile["education"][0]["end_year"] = 2022  # start > end
    errors = validate_candidate_profile(profile)
    assert any("start_year" in err and "greater than end_year" in err for err in errors)


# ===========================================================================
# Phase 4: Experience Extraction & Fresher Handling Tests
# ===========================================================================

def test_experience_parsing_structured_fields():
    exp_text = """Software Development Intern
Example Technologies | January 2026 - June 2026
- Developed Python scripts for data processing.
- Used Git for version control."""

    records = parse_experience_section(exp_text)
    assert len(records) == 1
    rec = records[0]

    assert rec["job_title"] == "Software Development Intern"
    assert "Example Technologies" in rec["organization"]
    assert rec["employment_type"] == "internship"
    assert rec["start_date"] == "January 2026"
    assert rec["end_date"] == "June 2026"
    assert len(rec["responsibilities"]) == 2
    assert "Python" in rec["skills_used"]
    assert "Git" in rec["skills_used"]


def test_empty_experience_is_valid_for_freshers():
    profile = sample_profile()
    profile["experience"] = []

    # Fatal errors must be empty
    errors = validate_candidate_profile(profile)
    assert errors == []

    # Comprehensive validation shows informational warning, not error
    comp = validate_candidate_profile_comprehensive(profile)
    assert comp["errors"] == []
    assert any("Experience section is empty" in w for w in comp["warnings"])


# ===========================================================================
# Phase 4: Projects Extraction Tests
# ===========================================================================

def test_projects_parsing_multiple_projects():
    proj_text = """Roadmap Planner
- Built a career planner using Python and FastAPI.
- Deployed on Docker container.

AI Resume Parser
- Created resume parsing pipeline with SQL and Python.
- Designed JSON schema."""

    records = parse_projects_section(proj_text)
    assert len(records) == 2

    assert records[0]["project_name"] == "Roadmap Planner"
    assert "Python" in records[0]["technologies"]
    assert "FastAPI" in records[0]["technologies"]
    assert len(records[0]["responsibilities"]) == 2

    assert records[1]["project_name"] == "AI Resume Parser"
    assert "SQL" in records[1]["technologies"]
    assert "Python" in records[1]["technologies"]


# ===========================================================================
# Phase 4: Certifications Extraction Tests
# ===========================================================================

def test_certifications_parsing():
    cert_text = """AWS Certified Cloud Practitioner
Amazon Web Services | 2025 | ID: AWS-987654

Python Programming Certificate
Example Learning Academy | 2024"""

    records = parse_certifications_section(cert_text)
    assert len(records) == 2

    assert "AWS Certified Cloud Practitioner" in records[0]["name"]
    assert "Amazon Web Services" in records[0]["issuing_organization"]
    assert records[0]["issue_date"] == "2025"
    assert records[0]["credential_id"] == "AWS-987654"

    assert "Python Programming Certificate" in records[1]["name"]
    assert "Example Learning Academy" in records[1]["issuing_organization"]
    assert records[1]["issue_date"] == "2024"


# ===========================================================================
# Phase 4: Assembly & Centralization Tests
# ===========================================================================

def test_assemble_candidate_profile_centralized():
    resume_data = {
        "source_file": "candidate_test.pdf",
        "text": "Alex Morgan\nalex@example.com\n\nEDUCATION\nBachelor of Science | 2020-2024",
        "sections": {
            "education": "Bachelor of Science\nExample Univ | 2020 - 2024",
            "skills": "Python, SQL",
        },
        "page_count": 1,
        "extraction_status": "success",
        "section_count": 2,
        "detected_headings": ["EDUCATION", "SKILLS"],
    }
    profile_skills = [{"skill": "Python", "embedding": [0.1] * 384}]
    embedding_data = {"model_name": "mini", "embedding_dimension": 384}

    profile = assemble_candidate_profile(
        resume_data=resume_data,
        profile_skills=profile_skills,
        embedding_data=embedding_data,
        pipeline_version="3.0.0",
    )

    assert profile["schema_version"] == "1.1.0"
    assert profile["candidate"]["name"] == "Alex Morgan"
    assert profile["candidate"]["email"] == "alex@example.com"
    assert len(profile["education"]) == 1
    assert profile["education"][0]["academic_level"] == "bachelor"
    assert profile["metadata"]["pipeline_version"] == "3.0.0"
    assert validate_candidate_profile(profile) == []
