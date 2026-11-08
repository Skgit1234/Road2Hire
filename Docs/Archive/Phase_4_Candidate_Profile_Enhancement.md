# Phase 4 — Candidate Profile Enhancement

## 1. Overview

**Project:** Road2Hire  
**Module:** AI / Candidate Profile  
**Phase:** 4 — Candidate Profile Enhancement  
**Status:** Completed  
**Schema Version:** `1.1.0`  
**Branch:** `main`

### Objective

Enhance the Road2Hire candidate profile pipeline to convert extracted résumé text into fully structured, granular, and validated candidate profiles.

Previously, while skills were normalized to ESCO and occupations matched via the Knowledge Graph, education, work experience, projects, and certifications were represented primarily as raw text blocks (`[{"raw_text": sections[...]}]`). Phase 4 replaces these unparsed text wrappers with typed, deterministic records, preserves full backward compatibility, provides clear separation of fatal validation errors versus informational warnings, and centralizes parsing logic across the entire platform.

---

## 2. Existing Limitations (Prior to Phase 4)

1. **Unstructured Section Content**: `education`, `experience`, `projects`, and `certifications` contained only `[{"raw_text": sections[...]}]`, making down-stream indexing, querying, and database persistence impractical.
2. **Missing Granular Candidate Info**: Candidate contact details (`name`, `email`, `phone`, `location`) were not extracted into structured fields. If contact information was placed at the top of the résumé before the first section heading, it was omitted from the section map.
3. **Multi-Item Coalescing**: Multiple degrees, companies, and projects in a single section were lumped into a single text block rather than parsed into individual entries.
4. **Duplicated Profile Assembly**: Both `AI/Candidate_Profile/profile_builder.py` and `AI/road2hire_model.py` had duplicate code to format profile dictionaries.
5. **Permissive Validation**: The validator only verified that sections were lists of dictionaries and that skills were non-duplicate; it did not validate scores (CGPA, percentage), date chronologies, or record types.

---

## 3. Updated Architecture

```text
               Resume PDF
                   │
                   ▼
         [pdf_extractor.py]
         Extract Clean Text
                   │
                   ▼
        [section_detector.py]
      Detect Sections & Headers
                   │
                   ├──────────────────────────────────┐
                   ▼                                  ▼
         [skill_extractor.py]              [section_parsers.py]
         Extract ESCO Skills               Deterministic Parsers:
                   │                       ├─ extract_candidate_info (name, email, phone, loc)
                   ▼                       ├─ parse_education_section (degree, school, dates, CGPA)
      [skill_taxonomy_mapper.py]           ├─ parse_experience_section (role, company, dates, bullets)
        Map to 13,939 ESCO concepts        ├─ parse_projects_section (name, tools, contributions)
                   │                       └─ parse_certifications_section (name, issuer, date, ID)
                   ▼                                  │
         [skill_embeddings.py]                        │
       Generate Vectors (384-d)                       │
                   │                                  │
                   └─────────────────┬────────────────┘
                                     │
                                     ▼
                        [assemble_candidate_profile]
                        Centralized Factory Method
                                     │
                                     ▼
                       [profile_validator.py]
                     Validate Schema Version 1.1.0
                     (Fatal Errors vs Warnings)
                                     │
                                     ▼
                        Structured CandidateProfile
```

### Key Architectural Enhancements

- **`AI/Candidate_Profile/section_parsers.py`**: Modular, rule-based deterministic parsers that extract structured records without hallucinating missing data.
- **Centralized Assembly**: `assemble_candidate_profile()` in `AI/Candidate_Profile/profile_builder.py` serves as the single source of truth for profile construction across both standalone scripts and the central `Road2HireModel` pipeline.
- **Top-of-Resume Contact Extraction**: Evaluates lines preceding the first detected section header in addition to explicit `contact_information` sections.
- **Schema Version `1.1.0`**: Fully typed additive schema (`AI/Candidate_Profile/profile_schema.py`) supporting both legacy and granular fields.

---

## 4. Candidate Profile Structure & Field Descriptions

The candidate profile conforms to TypedDict definitions in `AI/Candidate_Profile/profile_schema.py`:

### Top-Level Fields

| Field | Type | Description |
|---|---|---|
| `schema_version` | `str` | Profile schema version (`"1.1.0"`). |
| `source_file` | `str \| None` | Filename of the source résumé. |
| `candidate` | `CandidateInfo` | Candidate contact details, name, and summary. |
| `skills` | `list[dict]` | Extracted skills with ESCO mappings and embeddings. |
| `education` | `list[EducationRecord]` | Structured academic history. |
| `experience` | `list[ExperienceRecord]` | Structured work and internship experience. |
| `projects` | `list[ProjectRecord]` | Structured project achievements and tools. |
| `certifications` | `list[CertificationRecord]`| Structured credentials and licenses. |
| `metadata` | `dict` | Extraction metadata, model details, and status. |

### Sub-Record Fields

#### `candidate` (`CandidateInfo`)
- `name: str | None`: Full name (when reliably identified).
- `email: str | None`: Email address (regex-validated format).
- `phone: str | None`: Phone number including country/area codes.
- `location: str | None`: City, state, or country.
- `summary: str | None`: Professional summary or objective statement.
- `raw_contact_information: str`: Preserved original contact text (backward compatibility).
- `raw_summary: str`: Preserved original summary text (backward compatibility).

#### `education` (`EducationRecord`)
- `degree: str | None`: Full degree title (e.g. "Bachelor of Technology in Computer Science").
- `field_of_study: str | None`: Academic major/discipline (e.g. "Computer Science").
- `institution: str | None`: College or university name.
- `start_year: int | None`: Matriculation year (e.g. `2022`).
- `end_year: int | None`: Graduation or expected graduation year (e.g. `2026`).
- `cgpa: float | None`: Cumulative grade point average (e.g. `8.8`).
- `percentage: float | None`: Academic marks percentage (e.g. `85.0`).
- `academic_level: str | None`: Normalized level (`"bachelor"`, `"master"`, `"doctorate"`, `"diploma"`, `"secondary"`).
- `raw_text: str`: Raw text snippet from résumé.

#### `experience` (`ExperienceRecord`)
- `job_title: str | None`: Title or role (e.g. "Software Development Intern").
- `organization: str | None`: Employer or organization name.
- `employment_type: str | None`: `"internship"`, `"full-time"`, `"part-time"`, `"contract"`.
- `start_date: str | None`: Start month/year.
- `end_date: str | None`: End month/year or `"Present"`.
- `responsibilities: list[str]`: Bullet points describing contributions.
- `skills_used: list[str]`: Canonical technologies/skills referenced.
- `raw_text: str`: Raw text snippet.

#### `projects` (`ProjectRecord`)
- `project_name: str | None`: Project title.
- `description: str | None`: Overview or purpose of the project.
- `technologies: list[str]`: Tools and frameworks used (e.g. `["Python", "FastAPI"]`).
- `responsibilities: list[str]`: Key contributions or deliverables.
- `related_skills: list[str]`: Skills tied to project execution.
- `raw_text: str`: Raw text snippet.

#### `certifications` (`CertificationRecord`)
- `name: str | None`: Name of credential.
- `issuing_organization: str | None`: Issuer (e.g. "Amazon Web Services").
- `issue_date: str | None`: Date issued.
- `expiration_date: str | None`: Date expired or renewal deadline.
- `credential_id: str | None`: Verification ID or license code.
- `raw_text: str`: Raw text snippet.

---

## 5. Validation Rules

The validator (`AI/Candidate_Profile/profile_validator.py`) enforces strict schema rules while distinguishing fatal errors from informational warnings:

### Fatal Errors (`validate_candidate_profile()`)
A non-empty error list indicates a malformed or corrupted profile:
1. **Root Type**: Profile must be a Python dictionary.
2. **Required Keys**: Must contain all 9 top-level keys.
3. **Field Types**: `candidate` and `metadata` must be dictionaries; `skills`, `education`, `experience`, `projects`, `certifications` must be lists of dictionaries.
4. **Duplicate Skills**: No duplicate skill names within `profile["skills"]`.
5. **Embedding Vectors**: Every skill embedding must be a list of floats or `None`.
6. **Email Format**: Candidate email (if provided) must follow standard RFC email syntax.
7. **Score Bounds**: CGPA must be between $0.0$ and $10.0$; percentage must be between $0.0$ and $100.0$.
8. **Chronological Logic**: In education entries where both are integers, `start_year` must not be strictly greater than `end_year`.

### Informational Warnings (`validate_candidate_profile_comprehensive()`)
Non-blocking notices that flag incomplete or fresher profiles:
- Missing candidate name, email, or phone.
- Empty optional sections: **a student or fresher résumé with zero work experience or certifications is completely valid and produces only warnings, never fatal errors.**
- Empty skills or education sections.
- Unrecognized schema versions.

---

## 6. Pipeline Integration

In `AI/road2hire_model.py`:
- `_build_profile()` calls `assemble_candidate_profile()` with `pipeline_version="3.0.0"`.
- Profile validation is executed via `validate_candidate_profile()`.
- Resulting profile is returned under `result["candidate_profile"]` with `result["profile_validation_errors"]`.
- Backward compatibility is maintained with existing callers expecting `raw_contact_information`, `raw_summary`, and entry-level `raw_text`.

---

## 7. Sample Structured Profile Output

```json
{
  "schema_version": "1.1.0",
  "source_file": "sample_resume.pdf",
  "candidate": {
    "name": "Alex Morgan",
    "email": "alex.morgan@example.com",
    "phone": "+1-555-010-2040",
    "location": "Pune, India",
    "summary": "Computer science graduate interested in software development and data analysis.",
    "raw_contact_information": "Alex Morgan\nalex.morgan@example.com | +1-555-010-2040\nPune, India",
    "raw_summary": "Computer science graduate interested in software development and data analysis."
  },
  "skills": [
    {
      "skill": "Python (computer programming)",
      "source_sections": ["skills"],
      "occurrences": [{"section": "skills", "text": "Python", "start": 0, "end": 6}],
      "ESCO_Skill_Id": "http://data.europa.eu/esco/skill/4c5b2a62-5a76-4d99-a7a8-cbf04e9e8d1e",
      "ESCO_Skill_Name": "Python (computer programming)",
      "ESCO_Skill_Type": "skill/competence",
      "ESCO_Reuse_Level": "cross-sector",
      "ESCO_Mapping_Type": "alternative_label",
      "embedding": [-0.0384, 0.0512, 0.0128]
    }
  ],
  "education": [
    {
      "degree": "Bachelor of Technology in Computer Science",
      "field_of_study": "Computer Science",
      "institution": "Example Institute",
      "start_year": 2022,
      "end_year": 2026,
      "cgpa": null,
      "percentage": null,
      "academic_level": "bachelor",
      "raw_text": "Bachelor of Technology in Computer Science\nExample Institute | 2022 - 2026"
    }
  ],
  "experience": [
    {
      "job_title": "Software Development Intern",
      "organization": "Example Technologies",
      "employment_type": "internship",
      "start_date": "January 2026",
      "end_date": "June 2026",
      "responsibilities": [
        "Developed Python scripts for data processing.",
        "Used Git for version control."
      ],
      "skills_used": ["Git", "Python"],
      "raw_text": "Software Development Intern\nExample Technologies | January 2026 - June 2026\n- Developed Python scripts for data processing.\n- Used Git for version control."
    }
  ],
  "projects": [
    {
      "project_name": "Roadmap Planner",
      "description": "Roadmap Planner",
      "technologies": ["Python"],
      "responsibilities": [
        "Built a project planner using Python.",
        "Created structured outputs for project reports."
      ],
      "related_skills": ["Python"],
      "raw_text": "Roadmap Planner\n- Built a project planner using Python.\n- Created structured outputs for project reports."
    }
  ],
  "certifications": [
    {
      "name": "Python Programming Certificate",
      "issuing_organization": "Example Learning Academy",
      "issue_date": "2025",
      "expiration_date": null,
      "credential_id": null,
      "raw_text": "Python Programming Certificate\nExample Learning Academy | 2025"
    }
  ],
  "metadata": {
    "page_count": 1,
    "extraction_status": "success",
    "section_count": 6,
    "detected_headings": ["summary", "education", "experience", "skills", "projects", "certifications"],
    "skill_count": 1,
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    "embedding_dimension": 384,
    "sections_available": ["summary", "education", "experience", "skills", "projects", "certifications"],
    "section_content_is_raw": true,
    "pipeline_version": "3.0.0"
  }
}
```

---

## 8. Test Coverage

Comprehensive automated tests verify the enhanced pipeline:

- `test_valid_profile_has_no_errors`: Ensures canonical profile passes validation.
- `test_missing_required_field_is_reported`: Detects missing required keys.
- `test_invalid_skills_type_is_reported`: Flags malformed skills lists.
- `test_duplicate_skills_are_reported`: Detects duplicate skills in profile.
- `test_invalid_embedding_type_is_reported`: Rejects non-vector embeddings.
- `test_build_candidate_profile_from_sample_resume`: Tests end-to-end PDF processing to profile with schema version 1.1.0.
- `test_profile_preserves_detected_section_text`: Confirms backward compatibility.
- `test_candidate_info_extraction_sample_resume`: Verifies name, email, phone, location, and summary extraction.
- `test_candidate_info_missing_fields_not_hallucinated`: Confirms null fields are not guessed.
- `test_education_parsing_single_record`: Validates degree, level, institution, year, CGPA extraction.
- `test_education_parsing_multiple_records`: Validates multi-degree parsing.
- `test_education_validation_score_ranges`: Enforces CGPA and percentage bounds.
- `test_education_validation_chronological_order`: Detects inverted start/end years.
- `test_experience_parsing_structured_fields`: Validates title, company, dates, bullets, and tools.
- `test_empty_experience_is_valid_for_freshers`: Asserts freshers/students produce zero errors.
- `test_projects_parsing_multiple_projects`: Verifies multiple project separation and tech detection.
- `test_certifications_parsing`: Verifies credential names, issuers, dates, and IDs.
- `test_assemble_candidate_profile_centralized`: Tests centralized profile assembly factory.

### Test Results
- Total Tests: **161 passed** in 132.04s.
- `Tests/AI/test_candidate_profile.py`: 18/18 passed.
- `Tests/AI/test_road2hire_model.py`: 40/40 passed.
- Regressions: **0**.

---

## 9. Known Limitations

1. **Non-Standard Layouts**: Two-column résumés or complex graphic layouts may yield interleaved text from PDF extraction before section detection.
2. **Varied Date Formats**: Unconventional date representations (e.g. Roman numerals or quarters like "Q3 2025") may not populate structured date fields and remain in `raw_text`.
3. **Freeform Bullet Formats**: Non-standard bullet glyphs or unbroken paragraph descriptions may be captured as a single responsibility string.

---

## 10. Future Improvements

1. **Named Entity Recognition (NER)**: Complement rule-based parsing with lightweight domain-specific NER for complex international names and institutions.
2. **PostgreSQL Relational Schema**: Map `EducationRecord`, `ExperienceRecord`, `ProjectRecord`, and `CertificationRecord` to 3NF relational database tables with foreign keys to candidate user IDs.
3. **Skill-to-Project Association Graph**: Automatically associate ESCO skills directly with individual projects and work experiences where they were utilized.

