
"""Validate structured Road2Hire candidate profiles."""

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


def validate_candidate_profile(
    profile: dict[str, Any],
) -> list[str]:
    """Return validation errors; an empty list means the profile is valid."""

    errors = []

    if not isinstance(profile, dict):
        return ["Profile must be a dictionary."]

    missing = REQUIRED_FIELDS - profile.keys()
    if missing:
        errors.append(
            f"Missing required fields: {', '.join(sorted(missing))}"
        )

    for field in (
        "candidate",
        "metadata",
    ):
        if field in profile and not isinstance(profile[field], dict):
            errors.append(f"'{field}' must be a dictionary.")

    for field in (
        "skills",
        "education",
        "experience",
        "projects",
        "certifications",
    ):
        if field in profile:
            if not isinstance(profile[field], list):
                errors.append(f"'{field}' must be a list.")
            elif not all(isinstance(item, dict) for item in profile[field]):
                errors.append(f"Every item in '{field}' must be a dictionary.")

    if isinstance(profile.get("skills"), list):
        skill_names = [
            item.get("skill", "").strip().casefold()
            for item in profile["skills"]
            if isinstance(item, dict)
            and isinstance(item.get("skill"), str)
        ]
        if len(skill_names) != len(set(skill_names)):
            errors.append("Duplicate skills found in profile.")

        for item in profile["skills"]:
            if not isinstance(item, dict):
                continue
            embedding = item.get("embedding")
            if embedding is not None and not isinstance(embedding, list):
                errors.append(
                    f"Embedding for '{item.get('skill', 'unknown')}' "
                    "must be a list or None."
                )

    return errors
