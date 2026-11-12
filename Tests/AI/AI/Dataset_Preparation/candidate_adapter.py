"""Candidate Profile Adapters for Road2Hire M4.2.

Converts raw records from diverse sources (master_resumes.jsonl, synthetic_profiles.json)
into validated, standardized Road2Hire CandidateProfile dictionaries (schema v1.1.0).

Reuses existing ESCO taxonomy normalization and knowledge graph logic without duplication.
Cleans placeholder artifacts ("Unknown", null) and ensures full schema conformance.
"""

from __future__ import annotations

import re
from typing import Any

from AI.Candidate_Profile.profile_schema import (
    SCHEMA_VERSION,
    CandidateInfo,
    CandidateProfile,
    CertificationRecord,
    EducationRecord,
    ExperienceRecord,
    ProjectRecord,
)
from AI.Skill_Extraction.esco_taxonomy import ESCOTaxonomy, get_esco_taxonomy

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _clean_str(value: Any) -> str | None:
    """Return stripped string or None if empty or 'Unknown'."""
    if not isinstance(value, str):
        return None
    val = value.strip()
    if not val or val.casefold() in ("unknown", "n/a", "none", "null"):
        return None
    return val


def adapt_master_resume_to_candidate_profile(
    raw_record: dict[str, Any],
    candidate_id: str | int | None = None,
    taxonomy: ESCOTaxonomy | None = None,
) -> CandidateProfile:
    """Adapt a raw record from master_resumes.jsonl into a valid CandidateProfile (v1.1.0).

    Parameters
    ----------
    raw_record:
        Dictionary parsed from master_resumes.jsonl.
    candidate_id:
        Optional identifier for the candidate.
    taxonomy:
        Optional ESCOTaxonomy instance for skill normalization.

    Returns
    -------
    CandidateProfile dictionary conforming to schema v1.1.0.
    """
    tax = taxonomy if taxonomy is not None else get_esco_taxonomy()

    # 1. Candidate Personal Info
    raw_pi = raw_record.get("personal_info", {})
    raw_email = _clean_str(raw_pi.get("email"))
    # Only keep valid email strings
    clean_email = raw_email if (raw_email and EMAIL_REGEX.match(raw_email)) else None

    # Location assembly
    loc_data = raw_pi.get("location", {})
    loc_str: str | None = None
    if isinstance(loc_data, dict):
        city = _clean_str(loc_data.get("city"))
        country = _clean_str(loc_data.get("country"))
        if city and country:
            loc_str = f"{city}, {country}"
        elif city:
            loc_str = city
        elif country:
            loc_str = country
    elif isinstance(loc_data, str):
        loc_str = _clean_str(loc_data)

    cand_info: CandidateInfo = {
        "name": _clean_str(raw_pi.get("name")),
        "email": clean_email,
        "phone": _clean_str(raw_pi.get("phone")),
        "location": loc_str,
        "summary": _clean_str(raw_pi.get("summary")),
        "raw_contact_information": "",
        "raw_summary": _clean_str(raw_pi.get("summary")) or "",
    }

    # 2. Extract and Normalize Skills
    profile_skills: list[dict[str, Any]] = []
    seen_skill_names: set[str] = set()

    raw_skills = raw_record.get("skills", {})
    extracted_names: list[str] = []

    if isinstance(raw_skills, dict):
        tech_block = raw_skills.get("technical", {})
        if isinstance(tech_block, dict):
            for category_items in tech_block.values():
                if isinstance(category_items, list):
                    for item in category_items:
                        if isinstance(item, dict):
                            s_name = _clean_str(item.get("name"))
                            if s_name:
                                extracted_names.append(s_name)
                        elif isinstance(item, str):
                            s_name = _clean_str(item)
                            if s_name:
                                extracted_names.append(s_name)

    # Map extracted skills to ESCO
    for name in extracted_names:
        esco_skill = tax.find_skill(name)
        final_skill_name = esco_skill.preferred_label if esco_skill else name
        norm_key = final_skill_name.casefold()
        if norm_key in seen_skill_names:
            continue
        seen_skill_names.add(norm_key)

        if esco_skill:
            profile_skills.append({
                "skill": esco_skill.preferred_label,
                "ESCO_Skill_Id": esco_skill.concept_uri,
                "ESCO_Skill_Name": esco_skill.preferred_label,
            })
        else:
            profile_skills.append({
                "skill": name,
                "ESCO_Skill_Id": "",
                "ESCO_Skill_Name": "",
            })

    # 3. Experience Records
    experience_records: list[ExperienceRecord] = []
    for exp in raw_record.get("experience", []):
        if not isinstance(exp, dict):
            continue
        title = _clean_str(exp.get("title"))
        company = _clean_str(exp.get("company"))
        emp_type = _clean_str(exp.get("employment_type"))

        dates = exp.get("dates", {}) if isinstance(exp.get("dates"), dict) else {}
        start_date = _clean_str(dates.get("start"))
        end_date = _clean_str(dates.get("end"))

        responsibilities = [
            r for r in exp.get("responsibilities", []) if isinstance(r, str) and _clean_str(r)
        ]

        # Collect skills used
        skills_used: list[str] = []
        tech_env = exp.get("technical_environment", {})
        if isinstance(tech_env, dict):
            for t in tech_env.get("technologies", []) + tech_env.get("tools", []):
                cl = _clean_str(t)
                if cl and cl not in skills_used:
                    skills_used.append(cl)

        experience_records.append({
            "job_title": title,
            "organization": company,
            "employment_type": emp_type,
            "start_date": start_date,
            "end_date": end_date,
            "responsibilities": responsibilities,
            "skills_used": skills_used,
            "raw_text": f"{title or ''} at {company or ''}".strip(),
        })

    # 4. Education Records
    education_records: list[EducationRecord] = []
    for edu in raw_record.get("education", []):
        if not isinstance(edu, dict):
            continue
        deg_info = edu.get("degree", {}) if isinstance(edu.get("degree"), dict) else {}
        inst_info = edu.get("institution", {}) if isinstance(edu.get("institution"), dict) else {}

        deg_level = _clean_str(deg_info.get("level"))
        deg_field = _clean_str(deg_info.get("field"))
        inst_name = _clean_str(inst_info.get("name"))

        achievements = edu.get("achievements", {}) if isinstance(edu.get("achievements"), dict) else {}
        gpa = achievements.get("gpa")
        cgpa_val: float | None = None
        if isinstance(gpa, (int, float)) and 0.0 <= gpa <= 10.0:
            cgpa_val = float(gpa)

        education_records.append({
            "degree": deg_level,
            "field_of_study": deg_field,
            "institution": inst_name,
            "start_year": None,
            "end_year": None,
            "cgpa": cgpa_val,
            "percentage": None,
            "academic_level": deg_level,
            "raw_text": f"{deg_level or ''} in {deg_field or ''} from {inst_name or ''}".strip(),
        })

    # 5. Project Records
    project_records: list[ProjectRecord] = []
    for proj in raw_record.get("projects", []):
        if not isinstance(proj, dict):
            continue
        p_name = _clean_str(proj.get("name"))
        p_desc = _clean_str(proj.get("description"))
        p_techs = [
            t for t in proj.get("technologies", []) if isinstance(t, str) and _clean_str(t)
        ]

        project_records.append({
            "project_name": p_name,
            "description": p_desc,
            "technologies": p_techs,
            "responsibilities": [],
            "related_skills": p_techs,
            "raw_text": f"{p_name or ''}: {p_desc or ''}".strip(),
        })

    # 6. Certifications Records
    certification_records: list[CertificationRecord] = []
    raw_certs = raw_record.get("certifications", [])
    if isinstance(raw_certs, list):
        for cert in raw_certs:
            if isinstance(cert, dict):
                c_name = _clean_str(cert.get("name"))
                if c_name:
                    certification_records.append({
                        "name": c_name,
                        "issuing_organization": _clean_str(cert.get("issuer")),
                        "issue_date": _clean_str(cert.get("date")),
                        "expiration_date": None,
                        "credential_id": None,
                        "raw_text": c_name,
                    })
            elif isinstance(cert, str):
                c_name = _clean_str(cert)
                if c_name:
                    certification_records.append({
                        "name": c_name,
                        "issuing_organization": None,
                        "issue_date": None,
                        "expiration_date": None,
                        "credential_id": None,
                        "raw_text": c_name,
                    })

    source_id_str = str(candidate_id) if candidate_id is not None else "master_resume"

    return {
        "schema_version": SCHEMA_VERSION,
        "source_file": f"master_resumes:{source_id_str}",
        "candidate": cand_info,
        "skills": profile_skills,
        "education": education_records,
        "experience": experience_records,
        "projects": project_records,
        "certifications": certification_records,
        "metadata": {
            "source": "master_resumes.jsonl",
            "candidate_id": source_id_str,
            "skill_count": len(profile_skills),
            "experience_count": len(experience_records),
            "education_count": len(education_records),
            "project_count": len(project_records),
            "certification_count": len(certification_records),
        },
    }


def adapt_synthetic_profile_to_candidate_profile(
    raw_record: dict[str, Any],
    taxonomy: ESCOTaxonomy | None = None,
) -> CandidateProfile:
    """Adapt a raw record from synthetic_profiles.json into a valid CandidateProfile (v1.1.0).

    Parameters
    ----------
    raw_record:
        Dictionary parsed from synthetic_profiles.json.
    taxonomy:
        Optional ESCOTaxonomy instance for skill normalization.

    Returns
    -------
    CandidateProfile dictionary conforming to schema v1.1.0.
    """
    tax = taxonomy if taxonomy is not None else get_esco_taxonomy()

    profile_id = raw_record.get("profile_id", "unknown")
    career_intent = _clean_str(raw_record.get("career_intent"))

    # Location from preferences
    prefs = raw_record.get("preferences", {})
    loc_str: str | None = None
    if isinstance(prefs, dict):
        locs = prefs.get("locations", [])
        if isinstance(locs, list) and locs:
            loc_str = _clean_str(locs[0])

    cand_info: CandidateInfo = {
        "name": None,
        "email": None,
        "phone": None,
        "location": loc_str,
        "summary": career_intent,
        "raw_contact_information": "",
        "raw_summary": career_intent or "",
    }

    # Extract and normalize skills (primary + secondary)
    profile_skills: list[dict[str, Any]] = []
    seen_skill_names: set[str] = set()

    primary_skills = raw_record.get("skills_primary", []) or []
    secondary_skills = raw_record.get("skills_secondary", []) or []
    all_raw_skills = primary_skills + secondary_skills

    for s in all_raw_skills:
        s_clean = _clean_str(s)
        if not s_clean:
            continue

        esco_skill = tax.find_skill(s_clean)
        final_skill_name = esco_skill.preferred_label if esco_skill else s_clean
        norm_key = final_skill_name.casefold()
        if norm_key in seen_skill_names:
            continue
        seen_skill_names.add(norm_key)

        if esco_skill:
            profile_skills.append({
                "skill": esco_skill.preferred_label,
                "ESCO_Skill_Id": esco_skill.concept_uri,
                "ESCO_Skill_Name": esco_skill.preferred_label,
            })
        else:
            profile_skills.append({
                "skill": s_clean,
                "ESCO_Skill_Id": "",
                "ESCO_Skill_Name": "",
            })

    # Experience from roles, seniority, experience_years, domains
    roles = raw_record.get("roles", []) or []
    seniority = _clean_str(raw_record.get("seniority"))
    exp_years = raw_record.get("experience_years", 0)
    domains = raw_record.get("domains", []) or []

    experience_records: list[ExperienceRecord] = []
    if roles or (isinstance(exp_years, (int, float)) and exp_years > 0) or seniority:
        primary_role = _clean_str(roles[0]) if roles else "Software Professional"
        domains_str = ", ".join(str(d) for d in domains if _clean_str(d)) or "Technology"
        raw_exp_text = f"{seniority or ''} {primary_role or ''} ({exp_years or 0} yrs in {domains_str})".strip()

        experience_records.append({
            "job_title": primary_role,
            "organization": None,
            "employment_type": "full-time",
            "start_date": None,
            "end_date": "Present",
            "responsibilities": [],
            "skills_used": [s["skill"] for s in profile_skills],
            "raw_text": raw_exp_text,
        })

    return {
        "schema_version": SCHEMA_VERSION,
        "source_file": f"synthetic_profiles:{profile_id}",
        "candidate": cand_info,
        "skills": profile_skills,
        "education": [],
        "experience": experience_records,
        "projects": [],
        "certifications": [],
        "metadata": {
            "source": "synthetic_profiles.json",
            "candidate_id": str(profile_id),
            "seniority": seniority,
            "experience_years": exp_years,
            "domains": domains,
            "roles": roles,
            "career_intent": career_intent,
            "skill_count": len(profile_skills),
            "experience_count": len(experience_records),
            "education_count": 0,
            "project_count": 0,
            "certification_count": 0,
        },
    }


