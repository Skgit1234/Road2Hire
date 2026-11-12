"""Candidate Adapter for External Job-Resume Matching Benchmark.

Converts raw candidate rows from cv.csv into validated Road2Hire CandidateProfile
structures (schema version 1.1.0).

Ensures:
- Absolute candidate privacy (name is 'Not provided', zero PII hallucination).
- Rigorous ESCO skill normalization with taxonomy grounding.
- Provenance tracking (original candidate_id and target_position preserved).
- Complete conformance to CandidateProfile schema v1.1.0.
"""

from __future__ import annotations

import logging
from typing import Any

from AI.Candidate_Profile.profile_schema import (
    SCHEMA_VERSION,
    CandidateInfo,
    CandidateProfile,
    EducationRecord,
    ExperienceRecord,
)
from AI.Candidate_Profile.section_parsers import (
    parse_education_section,
    parse_experience_section,
)
from AI.Dataset_Preparation.external_dataset_loader import safe_parse_json_list
from AI.Skill_Extraction.esco_taxonomy import ESCOTaxonomy

logger = logging.getLogger(__name__)


def adapt_external_cv_to_candidate_profile(
    row: dict[str, Any],
    taxonomy: ESCOTaxonomy | None = None,
) -> CandidateProfile:
    """Adapt a raw CV record from cv.csv into a validated CandidateProfile.

    Parameters
    ----------
    row:
        Dictionary representing a single row from cv.csv.
    taxonomy:
        Optional pre-loaded ESCOTaxonomy for skill normalization.

    Returns
    -------
    A CandidateProfile dictionary conforming to Road2Hire schema v1.1.0.
    """
    candidate_id = str(row.get("candidate_id", "")).strip()
    target_position = str(row.get("target_position", "")).strip()
    resume_text = str(row.get("resume_text", "")).strip()
    education_text = str(row.get("education_text", "")).strip()
    experience_text = str(row.get("experience_text", "")).strip()
    inferred_category = str(row.get("inferred_category", "")).strip()

    try:
        years_exp = float(row.get("years_experience", 0.0) or 0.0)
    except (ValueError, TypeError):
        years_exp = 0.0

    # 1. Candidate Personal Info (Strict Privacy & Provenance)
    # Never hallucinate or synthesize candidate names or personal contacts
    summary_text = ""
    if resume_text:
        # Extract first non-empty paragraph or sentence as summary preview
        lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
        if lines:
            summary_text = lines[0]
            if len(summary_text) < 40 and len(lines) > 1:
                summary_text = f"{summary_text}. {lines[1]}"

    candidate_info: CandidateInfo = {
        "name": "Not provided",
        "email": None,
        "phone": None,
        "location": None,
        "summary": summary_text or None,
        "raw_contact_information": "",
        "raw_summary": summary_text,
    }

    # 2. Extract and Normalize Skills
    skills_raw = row.get("skills_list")
    if skills_raw is None:
        skills_raw = safe_parse_json_list(
            row.get("clean_skills_json") or row.get("clean_skills")
        )

    profile_skills: list[dict[str, Any]] = []
    seen_skills: set[str] = set()
    normalized_count = 0

    for skill_name in skills_raw:
        if not skill_name or not isinstance(skill_name, str):
            continue
        clean_name = skill_name.strip()
        canon_key = clean_name.casefold()
        if canon_key in seen_skills:
            continue
        seen_skills.add(canon_key)

        esco_skill = taxonomy.find_skill(clean_name) if taxonomy else None
        if esco_skill:
            normalized_count += 1
            pref_label = getattr(esco_skill, "preferred_label", clean_name)
            uri = getattr(esco_skill, "concept_uri", "")
            cat = getattr(esco_skill, "skill_type", "skill")
            profile_skills.append({
                "skill": pref_label,
                "raw_name": clean_name,
                "ESCO_Skill_Id": uri,
                "ESCO_Skill_Name": pref_label,
                "category": cat,
                "source": "external_cv_esco_normalized",
            })
        else:
            profile_skills.append({
                "skill": clean_name,
                "raw_name": clean_name,
                "ESCO_Skill_Id": "",
                "ESCO_Skill_Name": "",
                "category": "unmapped",
                "source": "external_cv_unmapped",
            })

    # 3. Parse Education
    education_records: list[EducationRecord] = []
    if education_text:
        parsed_edu = parse_education_section(education_text)
        for edu in parsed_edu:
            education_records.append({
                "degree": edu.get("degree"),
                "field_of_study": edu.get("field_of_study"),
                "institution": edu.get("institution"),
                "start_year": edu.get("start_year"),
                "end_year": edu.get("end_year"),
                "cgpa": edu.get("cgpa"),
                "percentage": edu.get("percentage"),
                "academic_level": edu.get("academic_level"),
                "raw_text": edu.get("raw_text", education_text),
            })
    if not education_records and education_text:
        # Fallback baseline record when deterministic parser finds no tokens
        education_records.append({
            "degree": education_text.splitlines()[0][:100].strip(),
            "field_of_study": None,
            "institution": None,
            "start_year": None,
            "end_year": None,
            "cgpa": None,
            "percentage": None,
            "academic_level": None,
            "raw_text": education_text,
        })

    # 4. Parse Experience
    experience_records: list[ExperienceRecord] = []
    if experience_text:
        parsed_exp = parse_experience_section(experience_text)
        for exp in parsed_exp:
            experience_records.append({
                "job_title": exp.get("job_title") or target_position or None,
                "organization": exp.get("organization"),
                "employment_type": exp.get("employment_type"),
                "start_date": exp.get("start_date"),
                "end_date": exp.get("end_date"),
                "responsibilities": exp.get("responsibilities", []),
                "skills_used": [s["skill"] for s in profile_skills[:10]],
                "raw_text": exp.get("raw_text", experience_text),
            })
    if not experience_records:
        experience_records.append({
            "job_title": target_position or None,
            "organization": None,
            "employment_type": None,
            "start_date": None,
            "end_date": None,
            "responsibilities": [experience_text] if experience_text else [],
            "skills_used": [s["skill"] for s in profile_skills[:10]],
            "raw_text": experience_text or f"{years_exp:.1f} years in {target_position}",
        })

    return {
        "schema_version": SCHEMA_VERSION,
        "source_file": f"Datasets/External/Job_Resume_Matching/cv.csv#{candidate_id}",
        "candidate": candidate_info,
        "skills": profile_skills,
        "education": education_records,
        "experience": experience_records,
        "projects": [],
        "certifications": [],
        "metadata": {
            "original_candidate_id": candidate_id,
            "source": "external_job_resume_matching",
            "target_position": target_position,
            "years_experience": years_exp,
            "inferred_category": inferred_category,
            "total_raw_skills": len(skills_raw),
            "normalized_skills_count": normalized_count,
            "raw_text_length": len(resume_text),
        },
    }

