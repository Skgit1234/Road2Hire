"""Occupation and Job Adapter for External Job-Resume Matching Benchmark.

Adapts job postings from job.csv into structured occupation representations compatible
with Road2Hire's OccupationRequirementSummary schema.

Features:
- Grounding to canonical ESCO occupations via RoleOccupationResolver when possible.
- Transparent preservation of unresolvable titles (sets esco_uri to None without false mappings).
- ESCO skill normalization for job requirements.
- Retains original job identifiers, categories, experience thresholds, and full descriptions.
"""

from __future__ import annotations

import logging
from typing import Any

from AI.Dataset_Preparation.build_unified_dataset import RoleOccupationResolver
from AI.Dataset_Preparation.external_dataset_loader import safe_parse_json_list
from AI.Dataset_Preparation.unified_schema import OccupationRequirementSummary
from AI.Skill_Extraction.esco_taxonomy import ESCOTaxonomy

logger = logging.getLogger(__name__)


def adapt_external_job_to_occupation(
    row: dict[str, Any],
    taxonomy: ESCOTaxonomy | None = None,
    resolver: RoleOccupationResolver | None = None,
) -> dict[str, Any]:
    """Adapt a raw job record from job.csv into a structured occupation record.

    Parameters
    ----------
    row:
        Dictionary representing a single row from job.csv.
    taxonomy:
        Optional pre-loaded ESCOTaxonomy instance for skill normalization.
    resolver:
        Optional pre-loaded RoleOccupationResolver instance for title grounding.

    Returns
    -------
    Dictionary combining OccupationRequirementSummary fields with external benchmark metadata.
    """
    job_id = str(row.get("job_id", "")).strip()
    job_title = str(row.get("job_title", "")).strip()
    category = str(row.get("category", "")).strip()
    description = str(row.get("job_description", "")).strip()
    education_text = str(row.get("education_text", "")).strip()

    try:
        years_required = float(row.get("years_required", 0.0) or 0.0)
    except (ValueError, TypeError):
        years_required = 0.0

    # 1. Canonical ESCO Occupation Grounding
    esco_uri: str | None = None
    esco_preferred_label: str | None = None
    is_esco_grounded = False

    if resolver and job_title:
        resolved = resolver.resolve(job_title)
        if resolved:
            esco_uri, esco_preferred_label = resolved
            is_esco_grounded = True

    # 2. Extract and Normalize Job Required Skills
    skills_raw = row.get("skills_list")
    if skills_raw is None:
        skills_raw = safe_parse_json_list(
            row.get("clean_skills_json") or row.get("clean_skills")
        )

    required_skills: list[dict[str, Any]] = []
    seen_skills: set[str] = set()
    normalized_skill_names: list[str] = []
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
            required_skills.append({
                "skill": pref_label,
                "raw_name": clean_name,
                "ESCO_Skill_Id": uri,
                "ESCO_Skill_Name": pref_label,
                "category": cat,
                "source": "external_job_esco_normalized",
            })
            normalized_skill_names.append(pref_label)
        else:
            required_skills.append({
                "skill": clean_name,
                "raw_name": clean_name,
                "ESCO_Skill_Id": "",
                "ESCO_Skill_Name": "",
                "category": "unmapped",
                "source": "external_job_unmapped",
            })
            normalized_skill_names.append(clean_name)

    return {
        "job_id": job_id,
        "job_title": job_title,
        "category": category,
        "is_esco_grounded": is_esco_grounded,
        "esco_uri": esco_uri,
        "esco_preferred_label": esco_preferred_label,
        "years_required": years_required,
        "education_text": education_text,
        "total_required_skills": len(required_skills),
        "normalized_skills_count": normalized_count,
        "required_skills": required_skills,
        "essential_skills": normalized_skill_names,
        "optional_skills": [],
        "description": description,
        "metadata": {
            "source": "external_job_resume_matching",
            "original_job_id": job_id,
            "raw_text_length": len(description),
        },
    }

