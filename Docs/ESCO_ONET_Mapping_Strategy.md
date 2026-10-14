# ESCO And O*NET Mapping Strategy

## Objective

Road2Hire uses ESCO (European Skills, Competences, Qualifications and Occupations) and O*NET (Occupational Information Network) as the standard skill foundation for the AI pipeline. The objective of this mapping strategy is to normalize skills extracted from resumes and job descriptions into a common taxonomy, assign standardized identifiers, and use occupation-skill relationships to detect skill gaps and generate career recommendations.

This strategy ensures that different representations of the same skill are mapped to a single standardized skill before further processing.

---

## Why ESCO And O*NET

### ESCO

ESCO provides a standardized taxonomy of occupations and skills used across industries. It includes:

* Occupation definitions.
* Skill definitions.
* Skill groups and categories.
* Occupation-to-skill relationships.
* Essential and optional skills for occupations.

Road2Hire uses ESCO as the primary source for skill normalization and occupation mapping.

### O*NET

O*NET is an occupational database maintained by the U.S. Department of Labor. It provides:

* Skill importance scores.
* Skill level scores.
* Technology skills.
* Knowledge areas.
* Abilities required for occupations.

Road2Hire uses O*NET to measure the importance of skills when calculating career readiness and prioritizing missing skills.

---

## Skill Normalization Strategy

Skills extracted from resumes and job descriptions may appear in different formats. Before comparison, every extracted skill is normalized into a canonical skill.

### Normalization Rules

| Extracted Skill | Normalized Skill |
| --------------- | ---------------- |
| JS              | JavaScript       |
| ReactJS         | React            |
| React.js        | React            |
| Node            | Node.js          |
| Postgres        | PostgreSQL       |
| Py              | Python           |
| Tensor Flow     | TensorFlow       |

### Normalization Workflow

1. Extract raw skill from resume or job description.
2. Convert to lowercase for matching.
3. Remove punctuation and unnecessary whitespace.
4. Match aliases against the skill taxonomy.
5. Replace with standardized ESCO/O*NET skill name.
6. Store the corresponding ESCO and O*NET identifiers.

This ensures that skills are compared consistently across all datasets.

---

## Occupation To Skill Mapping

Each occupation is linked with a set of standardized skills using ESCO occupation-skill relationships.

### Mapping Logic

| Occupation        | Skill            | Mapping Type |
| ----------------- | ---------------- | ------------ |
| Data Scientist    | Python           | Essential    |
| Data Scientist    | SQL              | Essential    |
| Data Scientist    | Machine Learning | Essential    |
| Data Scientist    | TensorFlow       | Optional     |
| Backend Developer | FastAPI          | Essential    |
| Backend Developer | PostgreSQL       | Essential    |
| Backend Developer | Docker           | Optional     |

### Usage In Road2Hire

* Identify required skills for a target career.
* Compare resume skills with occupation skills.
* Detect missing skills.
* Recommend learning resources for missing skills.

---

## Skill Importance Mapping

O*NET assigns importance and level values to occupational skills.

### Importance Scale Used In Road2Hire

| Importance Label | Score |
| ---------------- | ----: |
| Essential        |     5 |
| High             |     4 |
| Medium           |     3 |
| Low              |     2 |
| Nice To Have     |     1 |

### Example

| Skill       | Importance Score |
| ----------- | ---------------: |
| Programming |                5 |
| SQL         |                5 |
| Docker      |                3 |
| Kubernetes  |                2 |

Road2Hire converts these scores into weighted values during Career Readiness Score calculation.

---

## Alias Mapping Strategy

Many resumes contain abbreviations or alternative names for the same skill. Alias mapping converts these into standardized taxonomy entries.

### Alias Examples

| Alias        | Standard Skill |
| ------------ | -------------- |
| JS           | JavaScript     |
| TS           | TypeScript     |
| ReactJS      | React          |
| Node         | Node.js        |
| Postgres     | PostgreSQL     |
| Scikit Learn | Scikit-learn   |
| AWS EC2      | Amazon EC2     |

Alias mapping improves recall during skill extraction and prevents duplicate skill entries.

---

## How Road2Hire Uses The Mapping

The ESCO and O*NET mapping is used throughout the AI pipeline.

### Resume Parsing

Skills extracted from resumes are normalized using the ESCO/O*NET taxonomy.

### Job Description Parsing

Required and preferred skills are extracted and mapped to standardized skill identifiers.

### Skill Gap Detection

Resume skills are compared with required occupation skills to identify:

* Present skills.
* Missing skills.
* Partial matches.
* Additional skills.

### Career Readiness Score

Missing skills are weighted using O*NET importance values. Essential skills contribute more to the readiness score than optional skills.

### Personalized Learning Roadmap

Every missing skill is linked with learning resources from the Learning Resources dataset to generate a personalized roadmap for the candidate.

---

## Mapping Workflow

1. Resume Parsing extracts candidate skills.
2. Job Parsing extracts required job skills.
3. Skills are normalized using ESCO aliases.
4. ESCO identifiers are attached to normalized skills.
5. O*NET importance scores are added.
6. Skill Gap Detection compares standardized skills.
7. Career Readiness Score is calculated.
8. Learning resources are recommended for missing skills.

---

## Output Files Used In Road2Hire

| File                     | Purpose                                        |
| ------------------------ | ---------------------------------------------- |
| `Skill_Taxonomy.csv`     | Master normalized skill taxonomy.              |
| `ESCO_Skill_Mapping.csv` | ESCO skill identifiers and occupation mapping. |
| `ONET_Skill_Mapping.csv` | O*NET importance and level mapping.            |
| `Resume_Annotations.csv` | Resume entity annotations.                     |
| `Job_Annotations.csv`    | Job description annotations.                   |

These mapping files form the foundation of the Road2Hire AI/ML pipeline for Skill Extraction, Skill Normalization, Skill Gap Detection, Career Recommendation, and Personalized Learning Roadmaps.
