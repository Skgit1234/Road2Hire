"""Validate structured Road2Hire candidate profiles.

Phase 4 Enhancement:
- Validates top-level schema conformance and schema versioning.
- Validates record-level types, score ranges (CGPA, percentage), and chronological logic.
- Distinguishes fatal validation ERRORS from informational WARNINGS.
- A student / fresher resume without work experience or certifications is valid
  and generates only warnings, never fatal errors.
"""

from __future__ import annotations

import re
from typing import Any

REQUIRED_FIELDS = {
    "schema_version",
    "source_file",
    "candidate",
    "skills",
    "education",
    "experience",
    "projects",
    "certifications",
    "metadata",
}

SUPPORTED_SCHEMA_VERSIONS = {"1.0.0", "1.1.0"}


def validate_candidate_profile_comprehensive(
    profile: dict[str, Any],
) -> dict[str, list[str]]:
    """Perform comprehensive validation, returning separated errors and warnings.

    Returns
    -------
    dict with keys 'errors' and 'warnings', each mapping to a list of strings.
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(profile, dict):
        return {
            "errors": ["Profile must be a dictionary."],
            "warnings": [],
        }

    # 1. Top-level required fields
    missing = REQUIRED_FIELDS - profile.keys()
    if missing:
        errors.append(f"Missing required fields: {', '.join(sorted(missing))}")

    # Schema version check
    schema_version = profile.get("schema_version")
    if schema_version and schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        warnings.append(
            f"Unsupported schema version '{schema_version}'. Expected one of {sorted(SUPPORTED_SCHEMA_VERSIONS)}."
        )

    # 2. Candidate section validation
    candidate = profile.get("candidate")
    if "candidate" in profile:
        if not isinstance(candidate, dict):
            errors.append("'candidate' must be a dictionary.")
        else:
            if not candidate.get("name"):
                warnings.append("Candidate name is missing.")
            if not candidate.get("email"):
                warnings.append("Candidate email is missing.")
            elif not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", candidate["email"]):
                errors.append(f"Invalid candidate email format: {candidate['email']}")
            if not candidate.get("phone"):
                warnings.append("Candidate phone number is missing.")

    # 3. Metadata validation
    if "metadata" in profile and not isinstance(profile["metadata"], dict):
        errors.append("'metadata' must be a dictionary.")

    # 4. List sections structure validation
    for field in ("skills", "education", "experience", "projects", "certifications"):
        if field in profile:
            items = profile[field]
            if not isinstance(items, list):
                errors.append(f"'{field}' must be a list.")
            elif not all(isinstance(item, dict) for item in items):
                errors.append(f"Every item in '{field}' must be a dictionary.")

    # 5. Skills validation
    if isinstance(profile.get("skills"), list):
        skill_items = [s for s in profile["skills"] if isinstance(s, dict)]
        if not skill_items:
            warnings.append("Candidate profile contains no extracted skills.")

        skill_names = [
            s.get("skill", "").strip().casefold()
            for s in skill_items
            if isinstance(s.get("skill"), str) and s.get("skill", "").strip()
        ]
        if len(skill_names) != len(set(skill_names)):
            errors.append("Duplicate skills found in profile.")

        for item in skill_items:
            embedding = item.get("embedding")
            if embedding is not None and not isinstance(embedding, list):
                errors.append(
                    f"Embedding for '{item.get('skill', 'unknown')}' must be a list or None."
                )

    # 6. Education validation
    if isinstance(profile.get("education"), list):
        edu_items = [e for e in profile["education"] if isinstance(e, dict)]
        if not edu_items:
            warnings.append("Education section is empty.")

        for idx, edu in enumerate(edu_items):
            start = edu.get("start_year")
            end = edu.get("end_year")
            if isinstance(start, int) and isinstance(end, int):
                if start > end:
                    errors.append(
                        f"Education entry #{idx + 1} has start_year ({start}) greater than end_year ({end})."
                    )

            cgpa = edu.get("cgpa")
            if cgpa is not None:
                if not isinstance(cgpa, (int, float)):
                    errors.append(f"Education entry #{idx + 1} CGPA must be a number.")
                elif cgpa < 0.0 or cgpa > 10.0:
                    errors.append(
                        f"Education entry #{idx + 1} CGPA ({cgpa}) out of valid range (0.0 to 10.0)."
                    )

            percentage = edu.get("percentage")
            if percentage is not None:
                if not isinstance(percentage, (int, float)):
                    errors.append(f"Education entry #{idx + 1} percentage must be a number.")
                elif percentage < 0.0 or percentage > 100.0:
                    errors.append(
                        f"Education entry #{idx + 1} percentage ({percentage}) out of valid range (0 to 100)."
                    )

    # 7. Experience validation (optional section: empty is completely valid)
    if isinstance(profile.get("experience"), list):
        exp_items = [e for e in profile["experience"] if isinstance(e, dict)]
        if not exp_items:
            warnings.append("Experience section is empty (acceptable for students and freshers).")

    # 8. Projects validation
    if isinstance(profile.get("projects"), list):
        proj_items = [p for p in profile["projects"] if isinstance(p, dict)]
        if not proj_items:
            warnings.append("Projects section is empty.")

    # 9. Certifications validation (optional section)
    if isinstance(profile.get("certifications"), list):
        cert_items = [c for c in profile["certifications"] if isinstance(c, dict)]
        if not cert_items:
            warnings.append("Certifications section is empty.")

    return {
        "errors": errors,
        "warnings": warnings,
    }


def validate_candidate_profile(
    profile: dict[str, Any],
) -> list[str]:
    """Return validation errors; an empty list means the profile is valid.

    Maintains full backward compatibility with existing tests and modules.
    Only fatal errors are returned. Informational notices (such as an empty
    experience list for freshers) are treated as warnings and omitted.
    """
    result = validate_candidate_profile_comprehensive(profile)
    return result["errors"]
