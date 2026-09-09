# Annotation Strategy

## Objective

## Resume Annotation Labels
| Label | Meaning | Example |
| --- | --- | --- |
| SKILL | Technical skill mentioned in resume. | Python |
| TOOL | Software or developer tool. | Git, Docker |
| FRAMEWORK | Library or framework. | React, FastAPI |
| DATABASE | Database technology. | PostgreSQL |
| EDUCATION | Degree or qualification. | B.Tech Computer Engineering |
| CERTIFICATION | Professional certification. | AWS Certified Cloud Practitioner |
| EXPERIENCE | Experience duration or role. | 2 Years Software Engineer |
| PROJECT | Project name. | Road2Hire |
These labels will be used for Resume Skill Extraction (NER).

## Job Description Annotation Labels
| Label | Meaning | Example |
| --- | --- | --- |
| REQUIRED_SKILL | Mandatory skill. | SQL |
| PREFERRED_SKILL | Good-to-have skill. | Docker |
| REQUIRED_TOOL | Required software/tool. | Git |
| EXPERIENCE_REQUIRED | Required years of experience. | 3 Years |
| EDUCATION_REQUIRED | Required qualification. | Bachelor's Degree |
| ROLE | Job role/title. | Backend Developer |
These labels will be used while parsing job descriptions.

## Skill Gap Annotation Labels
| Label | Meaning |
| --- | --- |
| PRESENT | Skill exists in both resume and job description. |
| MISSING | Required by job but absent in resume. |
| PARTIAL | Related skill exists but exact skill is missing. |
| EXTRA | Skill appears only in resume. |
Road2Hire's Skill Gap Detection model will predict these labels.

## Skill Importance Labels
| Importance | Score |
| --- | --- |
| Essential | 5 |
| High | 4 |
| Medium | 3 |
| Low | 2 |
| Nice_To_Have | 1 |
Later, ESCO and O*NET values will populate these scores automatically.

## Career Readiness Labels
| Label | Meaning |
| --- | --- |
| READY | Candidate satisfies essential skills. |
| NEAR_READY | Missing a few important skills. |
| DEVELOPING | Missing multiple essential skills. |
| BEGINNER | Foundation skills only. |

## Annotation Workflow
1. Load the resume or job description.
2. Identify and annotate relevant entities using the defined labels.
3. Normalize extracted skills against the ESCO and O*NET mappings.
4. Assign skill importance where applicable.
5. Compare resume skills with job requirements.
6. Generate skill gap labels.
7. Use the resulting annotations as input for downstream Road2Hire AI models.

## Annotation Guidelines
- Annotate only information explicitly present in the source text.
- Preserve the original entity text in Entity_Text.
- Use the predefined labels consistently.
- Do not create new labels without updating this strategy.
- Prefer standardized ESCO and O*NET skill names during normalization.
- Do not infer skills that are not supported by the source text.
- Keep annotation boundaries aligned with the relevant text span.
- Use the same annotation rules across resumes and job descriptions.
