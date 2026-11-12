"""Deterministic parsers for structured resume section extraction.

Extracts structured records for:
- Candidate contact & personal info (name, email, phone, location, summary)
- Education (degree, field of study, institution, dates, grade/CGPA, level)
- Experience (title, company, employment type, dates, responsibilities, skills)
- Projects (name, description, technologies, contributions, related skills)
- Certifications (name, issuer, issue date, expiration date, credential ID)

Rule-based, conservative, and deterministic: never hallucinates missing information.
Always preserves raw text snippets for provenance and auditability.
"""

from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# Regex Patterns
# ---------------------------------------------------------------------------

EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
)

PHONE_PATTERN = re.compile(
    r"(?:(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}(?:[-.\s]?\d{1,4})?)"
)

YEAR_RANGE_PATTERN = re.compile(
    r"\b(19\d{2}|20\d{2})\s*(?:[-–—]|to)\s*(19\d{2}|20\d{2}|[Pp]resent|[Ee]xpected|[Cc]urrent)\b"
)

EXPERIENCE_DATE_PATTERN = re.compile(
    r"((?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+)?(?:19|20)\d{2})\s*(?:[-–—]|to)\s*((?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+)?(?:19|20)\d{2}|[Pp]resent|[Cc]urrent)",
    re.IGNORECASE,
)

SINGLE_YEAR_PATTERN = re.compile(r"\b(19\d{2}|20\d{2})\b")

CGPA_PATTERN = re.compile(
    r"\b(?:CGPA|GPA|grade)[\s:]*([0-9]+(?:\.[0-9]+)?)(?:\s*/\s*([0-9]+(?:\.[0-9]+)?))?\b",
    re.IGNORECASE,
)

PERCENTAGE_PATTERN = re.compile(
    r"\b([0-9]+(?:\.[0-9]+)?)\s*%"
)

DEGREE_LEVEL_MAP: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"\b(?:ph\.?d|doctor\s+of\s+philosophy|doctorate)\b", re.I), "Doctorate", "doctorate"),
    (re.compile(r"\b(?:master\s+of\s+technology|m\.?tech|m\.?s\.?|master\s+of\s+science|m\.?b\.?a|master\s+of\s+business|master\s+of\s+engineering|m\.?e\.?|master)\b", re.I), "Master", "master"),
    (re.compile(r"\b(?:bachelor\s+of\s+technology|b\.?tech|b\.?s\.?|bachelor\s+of\s+science|b\.?e\.?|bachelor\s+of\s+engineering|bachelor\s+of\s+arts|b\.?a\.?|b\.?com|bachelor)\b", re.I), "Bachelor", "bachelor"),
    (re.compile(r"\b(?:diploma|associate|polytechnic)\b", re.I), "Diploma", "diploma"),
    (re.compile(r"\b(?:high\s+school|secondary|hsc|ssc|12th|10th)\b", re.I), "Secondary", "secondary"),
]

EMPLOYMENT_TYPE_PATTERNS = [
    (re.compile(r"\b(?:intern|internship)\b", re.I), "internship"),
    (re.compile(r"\b(?:full[- ]time)\b", re.I), "full-time"),
    (re.compile(r"\b(?:part[- ]time)\b", re.I), "part-time"),
    (re.compile(r"\b(?:contract|contractor|freelance|consultant)\b", re.I), "contract"),
]

KNOWN_TECH_FORMATTING = {
    "python": "Python",
    "java": "Java",
    "c++": "C++",
    "c#": "C#",
    "c": "C",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "html": "HTML",
    "css": "CSS",
    "sql": "SQL",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "sqlite": "SQLite",
    "redis": "Redis",
    "nosql": "NoSQL",
    "git": "Git",
    "github": "GitHub",
    "gitlab": "GitLab",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "aws": "AWS",
    "azure": "Azure",
    "gcp": "GCP",
    "linux": "Linux",
    "bash": "Bash",
    "rest": "REST",
    "rest api": "REST APIs",
    "rest apis": "REST APIs",
    "graphql": "GraphQL",
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "react": "React",
    "react.js": "React",
    "angular": "Angular",
    "vue": "Vue",
    "node.js": "Node.js",
    "express": "Express",
    "scikit-learn": "Scikit-Learn",
    "sklearn": "Scikit-Learn",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "tensorflow": "TensorFlow",
    "pytorch": "PyTorch",
    "keras": "Keras",
    "machine learning": "Machine Learning",
    "deep learning": "Deep Learning",
    "nlp": "NLP",
    "data analysis": "Data Analysis",
    "tableau": "Tableau",
    "power bi": "Power BI",
    "excel": "Excel",
    "spark": "Spark",
    "hadoop": "Hadoop",
    "figma": "Figma",
}

KNOWN_TECH_TERMS = set(KNOWN_TECH_FORMATTING.keys())


def format_tech_name(tech_key: str) -> str:
    """Format canonical display name for a technology."""
    return KNOWN_TECH_FORMATTING.get(tech_key.lower(), tech_key.title())


# ---------------------------------------------------------------------------
# Candidate Contact & Personal Info
# ---------------------------------------------------------------------------

def extract_candidate_info(
    full_text: str,
    sections: dict[str, str],
) -> dict[str, Any]:
    """Extract candidate name, contact details, and summary.

    Looks in both the detected sections and the raw full resume text
    (especially lines preceding the first section header).
    """
    raw_contact = sections.get("contact_information", "").strip()
    raw_summary = sections.get("summary", "").strip()

    # If contact_information section was not detected as a separate header,
    # collect header lines from full_text before any major section header.
    header_text = raw_contact
    if not header_text and full_text:
        lines = [line.strip() for line in full_text.splitlines() if line.strip()]
        # Take the top lines until a typical section heading or up to 6 lines
        top_lines: list[str] = []
        for line in lines[:8]:
            if line.upper() in {
                "PROFESSIONAL SUMMARY", "SUMMARY", "EDUCATION", "EXPERIENCE",
                "SKILLS", "PROJECTS", "CERTIFICATIONS", "WORK EXPERIENCE"
            }:
                break
            top_lines.append(line)
        header_text = "\n".join(top_lines)

    search_text = f"{header_text}\n{raw_contact}" if raw_contact else header_text

    # 1. Email extraction
    email: str | None = None
    email_match = EMAIL_PATTERN.search(search_text)
    if not email_match and full_text:
        email_match = EMAIL_PATTERN.search(full_text)
    if email_match:
        email = email_match.group(0).strip()

    # 2. Phone extraction
    phone: str | None = None
    # Look for candidate phone numbers
    for line in search_text.splitlines():
        # Match lines or segments containing numbers and typical phone separators
        matches = list(PHONE_PATTERN.finditer(line))
        for m in matches:
            cand = m.group(0).strip()
            # Must contain at least 7 digits to be a legitimate phone number
            digits = re.sub(r"\D", "", cand)
            if 7 <= len(digits) <= 15:
                phone = cand
                break
        if phone:
            break

    # 3. Location extraction
    location: str | None = None
    for line in search_text.splitlines():
        # Avoid lines that have email or phone
        cleaned_line = line
        if email:
            cleaned_line = cleaned_line.replace(email, "")
        if phone:
            cleaned_line = cleaned_line.replace(phone, "")
        cleaned_line = re.sub(r"[|•\-\–]", " ", cleaned_line).strip()
        # Location heuristic: City, Country or City, State
        if re.search(r"\b[A-Z][a-zA-Z\s]+,\s*[A-Z][a-zA-Z\s]+\b", cleaned_line):
            match = re.search(r"\b[A-Z][a-zA-Z\s]+,\s*[A-Z][a-zA-Z\s]+\b", cleaned_line)
            if match:
                loc_cand = match.group(0).strip()
                # Ensure it's not a degree or company
                if not re.search(r"\b(university|institute|bachelor|master|technologies)\b", loc_cand, re.I):
                    location = loc_cand
                    break

    # 4. Name extraction
    name: str | None = None
    lines_for_name = search_text.splitlines() if search_text else full_text.splitlines()
    for raw_line in lines_for_name:
        line = raw_line.strip()
        if not line:
            continue
        # Remove pipe-separated contact info if on same line
        first_segment = line.split("|")[0].strip()
        # Remove emails/phones/links
        if "@" in first_segment or re.search(r"\d", first_segment):
            continue
        # Check if line looks like a human name: 2-4 capitalized words, no common section verbs
        words = first_segment.split()
        if 2 <= len(words) <= 4 and all(w[0].isupper() and w.isalpha() for w in words):
            if first_segment.upper() not in {
                "PROFESSIONAL SUMMARY", "WORK EXPERIENCE", "TECHNICAL SKILLS",
                "CAREER OBJECTIVE", "CURRICULUM VITAE", "RESUME"
            }:
                name = first_segment
                break

    # 5. Summary extraction
    summary: str | None = raw_summary if raw_summary else None

    return {
        "name": name,
        "email": email,
        "phone": phone,
        "location": location,
        "summary": summary,
        "raw_contact_information": raw_contact or header_text,
        "raw_summary": raw_summary,
    }


# ---------------------------------------------------------------------------
# Education Parser
# ---------------------------------------------------------------------------

def parse_education_section(text: str) -> list[dict[str, Any]]:
    """Parse education text into structured academic records."""
    if not isinstance(text, str) or not text.strip():
        return []

    # Split into entries: by double newline or distinct blocks
    raw_blocks = [b.strip() for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]
    records: list[dict[str, Any]] = []

    for block in raw_blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue

        degree: str | None = None
        academic_level: str | None = None
        field_of_study: str | None = None
        institution: str | None = None
        start_year: int | None = None
        end_year: int | None = None
        cgpa: float | None = None
        percentage: float | None = None

        full_block_text = " ".join(lines)

        # 1. Detect Degree and Academic Level
        for pat, deg_name, level in DEGREE_LEVEL_MAP:
            m = pat.search(full_block_text)
            if m:
                # Capture the full degree phrase if possible from the line
                for line in lines:
                    if pat.search(line):
                        degree = line.split("|")[0].strip()
                        break
                if not degree:
                    degree = m.group(0).title()
                academic_level = level
                break

        # 2. Field of study (e.g. "in Computer Science", "in Information Technology")
        fos_match = re.search(r"\b(?:in|of)\s+([A-Z][a-zA-Z\s]+(?:\s+(?:Engineering|Science|Technology|Studies|Arts|Business|Administration))?)", full_block_text)
        if fos_match:
            field_cand = fos_match.group(1).strip()
            # Clean trailing separators
            field_cand = re.sub(r"\s*[|,\-].*$", "", field_cand).strip()
            if len(field_cand) > 2 and field_cand.lower() not in {"technology", "science", "arts"}:
                field_of_study = field_cand

        # 3. Institution (words containing University, Institute, College, School, Academy)
        for line in lines:
            parts = [p.strip() for p in line.split("|")]
            for part in parts:
                if re.search(r"\b(?:University|Institute|College|School|Academy)\b", part, re.I):
                    inst_cand = re.sub(r"\b(?:19|20)\d{2}.*$", "", part).strip()
                    if inst_cand:
                        institution = inst_cand
                        break
            if institution:
                break

        # Fallback for institution if not found above: 2nd line if it has no degree/dates
        if not institution and len(lines) >= 2:
            second_line = lines[1].split("|")[0].strip()
            if not any(pat.search(second_line) for pat, _, _ in DEGREE_LEVEL_MAP):
                if not YEAR_RANGE_PATTERN.search(second_line) and len(second_line) > 3:
                    institution = second_line

        # 4. Dates / Years
        year_match = YEAR_RANGE_PATTERN.search(full_block_text)
        if year_match:
            start_year = int(year_match.group(1))
            end_cand = year_match.group(2)
            if end_cand.isdigit():
                end_year = int(end_cand)
        else:
            single_years = SINGLE_YEAR_PATTERN.findall(full_block_text)
            if single_years:
                end_year = int(single_years[-1])
                if len(single_years) >= 2:
                    start_year = int(single_years[0])

        # 5. CGPA / Percentage
        cgpa_match = CGPA_PATTERN.search(full_block_text)
        if cgpa_match:
            try:
                cgpa = float(cgpa_match.group(1))
            except ValueError:
                pass

        perc_match = PERCENTAGE_PATTERN.search(full_block_text)
        if perc_match:
            try:
                percentage = float(perc_match.group(1))
            except ValueError:
                pass

        records.append({
            "degree": degree,
            "field_of_study": field_of_study,
            "institution": institution,
            "start_year": start_year,
            "end_year": end_year,
            "cgpa": cgpa,
            "percentage": percentage,
            "academic_level": academic_level,
            "raw_text": block,
        })

    return records


# ---------------------------------------------------------------------------
# Experience Parser
# ---------------------------------------------------------------------------

def parse_experience_section(text: str) -> list[dict[str, Any]]:
    """Parse professional experience text into structured job records."""
    if not isinstance(text, str) or not text.strip():
        return []

    # Split into entries by double newline or role blocks
    raw_blocks = [b.strip() for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]
    records: list[dict[str, Any]] = []

    for block in raw_blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue

        job_title: str | None = None
        organization: str | None = None
        employment_type: str | None = None
        start_date: str | None = None
        end_date: str | None = None
        responsibilities: list[str] = []
        skills_used: list[str] = []

        header_lines: list[str] = []
        for line in lines:
            if line.startswith(("-", "•", "*", "–", "—")) or re.match(r"^\d+\.", line):
                resp_text = re.sub(r"^[-•*–—\d.]+\s*", "", line).strip()
                if resp_text:
                    responsibilities.append(resp_text)
            else:
                header_lines.append(line)

        # Parse header lines for title, org, dates
        if header_lines:
            first_line = header_lines[0]
            first_parts = [p.strip() for p in first_line.split("|")]

            # Check if first line is exclusively a date / employment metadata line
            is_date_line = bool(
                EXPERIENCE_DATE_PATTERN.search(first_parts[0]) or YEAR_RANGE_PATTERN.search(first_parts[0])
            )

            if is_date_line and len(header_lines) > 1:
                title_line = header_lines[1]
                t_parts = [p.strip() for p in title_line.split("|")]
                if len(t_parts) > 1:
                    job_title = t_parts[0]
                    organization = t_parts[1]
                elif " - " in title_line:
                    t_sub = title_line.split(" - ", 1)
                    job_title = t_sub[0].strip()
                    organization = t_sub[1].strip()
                elif ", " in title_line:
                    t_sub = title_line.rsplit(", ", 1)
                    job_title = t_sub[0].strip()
                    organization = t_sub[1].strip()
                else:
                    job_title = title_line
            else:
                job_title = first_parts[0]
                if len(first_parts) > 1:
                    organization = first_parts[1]
                elif len(header_lines) > 1:
                    second_line = header_lines[1]
                    second_parts = [p.strip() for p in second_line.split("|")]
                    organization = second_parts[0]

        # Employment type
        full_block = " ".join(lines)
        for pat, emp_type in EMPLOYMENT_TYPE_PATTERNS:
            if pat.search(full_block):
                employment_type = emp_type
                break

        # Dates
        # Matches e.g. "January 2026 - June 2026" or "2022 - 2024" or "May 2023 - Present"
        date_match = EXPERIENCE_DATE_PATTERN.search(full_block)
        if date_match:
            start_date = date_match.group(1).strip()
            end_date = date_match.group(2).strip()
        else:
            # Fallback to single year range
            yr_match = YEAR_RANGE_PATTERN.search(full_block)
            if yr_match:
                start_date = yr_match.group(1)
                end_date = yr_match.group(2)

        # Clean dates from organization if it was matched there
        if organization and (start_date or end_date):
            organization = re.sub(EXPERIENCE_DATE_PATTERN, "", organization).strip(" |-–—")

        # Extract skills used mentioned in the block
        lower_block = full_block.lower()
        for tech in KNOWN_TECH_TERMS:
            pattern = rf"(?<!\w){re.escape(tech)}(?!\w)"
            if re.search(pattern, lower_block):
                skills_used.append(format_tech_name(tech))

        records.append({
            "job_title": job_title,
            "organization": organization,
            "employment_type": employment_type,
            "start_date": start_date,
            "end_date": end_date,
            "responsibilities": responsibilities,
            "skills_used": list(dict.fromkeys(skills_used)),
            "raw_text": block,
        })

    return records


# ---------------------------------------------------------------------------
# Project Parser
# ---------------------------------------------------------------------------

def parse_projects_section(text: str) -> list[dict[str, Any]]:
    """Parse projects section text into structured project records."""
    if not isinstance(text, str) or not text.strip():
        return []

    # Projects can be separated by blank lines or headers
    raw_blocks = [b.strip() for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]
    records: list[dict[str, Any]] = []

    for block in raw_blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue

        project_name: str | None = None
        description: str | None = None
        technologies: list[str] = []
        responsibilities: list[str] = []
        related_skills: list[str] = []

        header_lines: list[str] = []
        for line in lines:
            if line.startswith(("-", "•", "*", "–", "—")) or re.match(r"^\d+\.", line):
                resp_text = re.sub(r"^[-•*–—\d.]+\s*", "", line).strip()
                if resp_text:
                    responsibilities.append(resp_text)
            else:
                header_lines.append(line)

        if header_lines:
            first_line = header_lines[0]
            first_parts = [p.strip() for p in first_line.split("|")]
            project_name = first_parts[0]
            if len(first_parts) > 1:
                # Might have technologies after pipe
                tech_cand = first_parts[1]
                technologies.extend([t.strip() for t in re.split(r"[,/]", tech_cand) if t.strip()])
            if len(header_lines) > 1:
                description = " ".join(header_lines[1:])
        elif responsibilities:
            description = responsibilities[0]

        # Extract technologies & skills from full block text
        full_block = " ".join(lines)
        lower_block = full_block.lower()
        for tech in KNOWN_TECH_TERMS:
            pattern = rf"(?<!\w){re.escape(tech)}(?!\w)"
            if re.search(pattern, lower_block):
                formatted = format_tech_name(tech)
                if formatted not in technologies:
                    technologies.append(formatted)
                if formatted not in related_skills:
                    related_skills.append(formatted)

        records.append({
            "project_name": project_name,
            "description": description,
            "technologies": technologies,
            "responsibilities": responsibilities,
            "related_skills": related_skills,
            "raw_text": block,
        })

    return records


# ---------------------------------------------------------------------------
# Certification Parser
# ---------------------------------------------------------------------------

def parse_certifications_section(text: str) -> list[dict[str, Any]]:
    """Parse certifications section text into structured credential records."""
    if not isinstance(text, str) or not text.strip():
        return []

    raw_blocks = [b.strip() for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]
    records: list[dict[str, Any]] = []

    for block in raw_blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue

        name: str | None = None
        issuing_organization: str | None = None
        issue_date: str | None = None
        expiration_date: str | None = None
        credential_id: str | None = None

        first_line = lines[0]
        first_parts = [p.strip() for p in first_line.split("|")]
        name = first_parts[0]

        if len(first_parts) > 1:
            issuing_organization = first_parts[1]
        elif len(lines) > 1:
            second_line = lines[1]
            second_parts = [p.strip() for p in second_line.split("|")]
            issuing_organization = second_parts[0]

        # Look for dates
        full_block = " ".join(lines)
        date_match = re.search(
            r"\b((?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+)?(?:19|20)\d{2})\b",
            full_block,
            re.IGNORECASE,
        )
        if date_match:
            issue_date = date_match.group(1).strip()

        # Clean dates from issuer if merged
        if issuing_organization and issue_date:
            issuing_organization = issuing_organization.replace(issue_date, "").strip(" |-–—")

        # Credential ID or URL if present
        id_match = re.search(r"\b(?:ID|Credential ID|Code)[\s:]*([A-Za-z0-9\-]+)\b", full_block, re.I)
        if id_match:
            credential_id = id_match.group(1).strip()

        records.append({
            "name": name,
            "issuing_organization": issuing_organization or None,
            "issue_date": issue_date,
            "expiration_date": expiration_date,
            "credential_id": credential_id,
            "raw_text": block,
        })

    return records
