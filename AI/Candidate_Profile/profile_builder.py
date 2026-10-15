"""Build structured candidate profiles from resume intelligence outputs."""

from pathlib import Path
from typing import Any

from AI.Resume_Processing.resume_pipeline import process_resume
from AI.Skill_Extraction.skill_extractor import extract_skills
from AI.Skill_Extraction.skill_taxonomy_mapper import map_skills_to_esco
from AI.Skill_Extraction.skill_embeddings import generate_skill_embeddings


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

    sections = resume_data.get("sections", {})

    return {
        "schema_version": "1.0.0",
        "source_file": resume_data.get("source_file"),
        "candidate": {
            "raw_contact_information": sections.get(
                "contact_information", ""
            ),
            "raw_summary": sections.get("summary", ""),
        },
        "skills": profile_skills,
        "education": [
            {"raw_text": sections["education"]}
        ] if sections.get("education") else [],
        "experience": [
            {"raw_text": sections["experience"]}
        ] if sections.get("experience") else [],
        "projects": [
            {"raw_text": sections["projects"]}
        ] if sections.get("projects") else [],
        "certifications": [
            {"raw_text": sections["certifications"]}
        ] if sections.get("certifications") else [],
        "metadata": {
            "page_count": resume_data.get("page_count", 0),
            "extraction_status": resume_data.get("extraction_status"),
            "section_count": resume_data.get("section_count", 0),
            "detected_headings": resume_data.get("detected_headings", []),
            "skill_count": len(profile_skills),
            "embedding_model": embedding_data["model_name"],
            "embedding_dimension": embedding_data["embedding_dimension"],
            "sections_available": list(sections.keys()),
            "section_content_is_raw": True,
            "pipeline_version": "1.0.0",
        },
    }
