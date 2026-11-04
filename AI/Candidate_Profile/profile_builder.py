"""Build structured candidate profiles from resume intelligence outputs."""

from pathlib import Path
from typing import Any

from AI.Candidate_Profile.profile_schema import SCHEMA_VERSION
from AI.Candidate_Profile.section_parsers import (
    extract_candidate_info,
    parse_certifications_section,
    parse_education_section,
    parse_experience_section,
    parse_projects_section,
)
from AI.Resume_Processing.resume_pipeline import process_resume
from AI.Skill_Extraction.skill_embeddings import generate_skill_embeddings
from AI.Skill_Extraction.skill_extractor import extract_skills
from AI.Skill_Extraction.skill_taxonomy_mapper import map_skills_to_esco


def assemble_candidate_profile(
    resume_data: dict[str, Any],
    profile_skills: list[dict[str, Any]],
    embedding_data: dict[str, Any],
    pipeline_version: str = "1.0.0",
) -> dict[str, Any]:
    """Assemble a complete, structured CandidateProfile dictionary.

    Centralized factory used by both ``build_candidate_profile`` and
    ``Road2HireModel._build_profile`` to eliminate duplicated logic.
    """
    sections = resume_data.get("sections", {})
    full_text = resume_data.get("text", "")

    # Extract structured candidate info (name, email, phone, location, summary)
    candidate_info = extract_candidate_info(full_text=full_text, sections=sections)

    # Parse individual sections into structured records
    education = parse_education_section(sections.get("education", ""))
    experience = parse_experience_section(sections.get("experience", ""))
    projects = parse_projects_section(sections.get("projects", ""))
    certifications = parse_certifications_section(sections.get("certifications", ""))

    return {
        "schema_version": SCHEMA_VERSION,
        "source_file": resume_data.get("source_file"),
        "candidate": candidate_info,
        "skills": profile_skills,
        "education": education,
        "experience": experience,
        "projects": projects,
        "certifications": certifications,
        "metadata": {
            "page_count": resume_data.get("page_count", 0),
            "extraction_status": resume_data.get("extraction_status"),
            "section_count": resume_data.get("section_count", 0),
            "detected_headings": resume_data.get("detected_headings", []),
            "skill_count": len(profile_skills),
            "embedding_model": embedding_data.get("model_name", ""),
            "embedding_dimension": embedding_data.get("embedding_dimension", 384),
            "sections_available": list(sections.keys()),
            "section_content_is_raw": True,
            "pipeline_version": pipeline_version,
        },
    }


def build_candidate_profile(pdf_path: str | Path) -> dict[str, Any]:
    """Combine resume processing, skill extraction, mapping, and embeddings."""
    resume_data = process_resume(pdf_path)
    extracted_data = extract_skills(resume_data)

    mapped_skills = map_skills_to_esco(extracted_data["skills"])

    skill_names = [item["skill"] for item in mapped_skills]
    embedding_data = generate_skill_embeddings(skill_names)

    embedding_lookup = {
        item["skill"].casefold(): item["embedding"]
        for item in embedding_data["skills"]
    }

    profile_skills = [
        {
            **item,
            "embedding": embedding_lookup.get(item["skill"].casefold()),
        }
        for item in mapped_skills
    ]

    return assemble_candidate_profile(
        resume_data=resume_data,
        profile_skills=profile_skills,
        embedding_data=embedding_data,
        pipeline_version="1.0.0",
    )
