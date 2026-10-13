"""Detect common sections in cleaned resume text."""

import re
from typing import Any


SECTION_ALIASES = {
    "contact_information": {
        "contact",
        "contact information",
        "personal details",
        "personal information",
    },
    "education": {
        "education",
        "educational background",
        "academic background",
        "academic qualifications",
    },
    "experience": {
        "experience",
        "work experience",
        "professional experience",
        "employment history",
        "work history",
        "internship experience",
    },
    "skills": {
        "skills",
        "technical skills",
        "core skills",
        "key skills",
        "skills and competencies",
        "technical competencies",
    },
    "projects": {
        "projects",
        "personal projects",
        "academic projects",
        "key projects",
        "project experience",
    },
    "certifications": {
        "certifications",
        "certificates",
        "licenses and certifications",
        "licenses & certifications",
        "professional certifications",
    },
    "summary": {
        "summary",
        "professional summary",
        "profile",
        "career summary",
        "objective",
        "career objective",
    },
}


def normalize_heading(line: str) -> str:
    """Normalize a candidate section heading for matching."""
    line = line.strip().lower()
    line = re.sub(r"^[\W_]+|[\W_]+$", "", line)
    line = re.sub(r"\s+", " ", line)
    return line


def detect_resume_sections(text: str) -> dict[str, Any]:
    """
    Detect major resume sections using common heading aliases.

    Returns section text, detected headings, and detection metadata.
    This is a rule-based baseline, not a machine-learning classifier.
    """
    if not isinstance(text, str):
        raise TypeError("Resume text must be a string.")

    lines = text.splitlines()
    detected: list[tuple[int, str, str]] = []

    for index, line in enumerate(lines):
        heading = normalize_heading(line)

        # Also handle common headings such as "SKILLS:" and "Education -".
        heading = re.sub(r"\s*[:\-–—]\s*$", "", heading).strip()

        for section_name, aliases in SECTION_ALIASES.items():
            if heading in aliases:
                detected.append((index, section_name, line.strip()))
                break

    sections: dict[str, str] = {}
    headings: dict[str, list[str]] = {}

    for position, (line_index, section_name, heading_text) in enumerate(detected):
        next_line_index = (
            detected[position + 1][0]
            if position + 1 < len(detected)
            else len(lines)
        )

        body = "\n".join(lines[line_index + 1:next_line_index]).strip()

        # Preserve repeated occurrences rather than silently overwriting them.
        if body:
            sections[section_name] = (
                f"{sections[section_name]}\n\n{body}"
                if sections.get(section_name)
                else body
            )

        headings.setdefault(section_name, []).append(heading_text)

    return {
        "sections": sections,
        "detected_headings": headings,
        "detected_section_names": list(sections.keys()),
        "section_count": len(sections),
        "detection_method": "rule_based_heading_matching",
    }