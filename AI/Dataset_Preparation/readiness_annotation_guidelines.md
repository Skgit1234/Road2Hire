# Road2Hire — M4.3 Career Readiness Annotation Guidelines & Rubric

**Document Version:** 1.0.0  
**Target Milestone:** M4.3 (Career Readiness Label Strategy)  
**Schema Definition:** [`AI/Dataset_Preparation/readiness_label_schema.json`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Dataset_Preparation/readiness_label_schema.json)  
**Reference Dataset:** [`Datasets/Processed/candidate_occupation_dataset.jsonl`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Datasets/Processed/candidate_occupation_dataset.jsonl)  

---

## 1. Objective and Scope

This document establishes the official protocol and evidence-based rubric for creating human-annotated **career readiness ground-truth labels** for the Road2Hire platform.

The goal is to produce a high-fidelity, auditable benchmark dataset to train and evaluate supervised machine learning models that assess whether a candidate is prepared to enter and succeed in a specified target occupation.

> [!IMPORTANT]
> **Anti-Circularity Mandate:**
> Annotators and data engineers must **never** infer, threshold, or derive career readiness labels from existing rule-based skill coverage scores or compatibility scores.
> Annotations must be grounded strictly in **independent, holistic evidence** (practical application, project depth, work responsibilities, verified tool execution, and academic foundations).

---

## 2. Core Conceptual Disambiguation

A foundational requirement of Road2Hire's research methodology is the strict separation of three frequently conflated concepts:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             THREE DISTINCT TASKS                            │
├───────────────────────┬────────────────────────────┬────────────────────────┤
│   CAREER READINESS    │ CANDIDATE-JOB COMPATIBILITY│     SKILL COVERAGE     │
│       (M4.3)          │       (gold_labels)        │          (M3)          │
├───────────────────────┼────────────────────────────┼────────────────────────┤
│ "Is this individual   │ "Does this candidate match │ "What percentage of    │
│ competent and ready   │ the specific hiring needs, │ an ESCO occupation's   │
│ to perform the core   │ location, and constraints  │ catalog of 50-120      │
│ responsibilities of   │ of employer X's job post?" │ skills are matched on  │
│ this occupation in    │                            │ paper by the resume?"  │
│ the labor market?"    │                            │                        │
└───────────────────────┴────────────────────────────┴────────────────────────┘
```

### Detailed Distinctions

| Dimension | Career Readiness (M4.3) | Candidate-Job Compatibility (`gold_labels.json`) | Skill Coverage Feature (M3) |
|:---|:---|:---|:---|
| **Question Answered** | Is the candidate qualified to execute this occupational role in industry? | Does the candidate satisfy a specific employer's requisition? | What fraction of canonical taxonomy skills match resume strings? |
| **Scope** | Broad labor market occupation (ESCO). | Specific job posting (e.g., scraped LinkedIn post). | Canonical taxonomy concept list. |
| **Influencing Factors** | Practical problem-solving, engineering autonomy, experience depth, projects, core competencies. | Commute/location, salary budget, notice period, company size, rigid tech stack filters. | Text keyword matching, graph distance, semantic embedding similarity. |
| **Example Divergence** | A Senior Java Engineer is **100% Job Ready** as a Software Developer. | But **Incompatible** with a remote Python/Django vacancy in Berlin paying below market rate. | Their ESCO software developer skill coverage may only be **8.5%** because ESCO lists 90+ skills. |
| **Role in ML Pipeline** | **Supervised Target Label ($y$)** to be predicted in M4.3. | **External Baseline / Filter** for job recommendation. | **Input Feature ($X$)** describing lexical and graph alignment. |

---

## 3. Reference Framework: ESCO Occupation Expectations

Human annotators must evaluate readiness against the **core occupational function** defined in the European Skills, Competences, Qualifications and Occupations (ESCO) taxonomy:

1. **Focus on Core Occupational Purpose:**  
   ESCO occupations (such as *Software Developer*, *Data Scientist*, or *ICT System Administrator*) contain between 30 and 120 associated skills. Annotators must **not** require a candidate to possess every single listed skill. Instead, evaluate whether the candidate demonstrates practical competence in the **core foundational competencies** (e.g., for a Software Developer: programming logic, software design, debugging, version control, and database interaction).
2. **Essential vs. Optional Requirements:**  
   Focus primary scrutiny on the occupation's **essential skills**. Optional skills serve as positive signals for specialization, not hard barriers to entry.
3. **Occupation-Specific Seniority Context:**  
   Evaluate readiness at the threshold of a **standard professional entry point** (e.g., junior to mid-level workforce entry). The baseline expectation is that a "Job Ready" candidate can execute standard day-to-day tasks with normal team collaboration rather than needing complete technical retraining.

---

## 4. The Three-Class Career Readiness Rubric

Every candidate–occupation pair is assigned exactly one of three mutually exclusive classes:

```
       [Not Ready]  ───────────►  [Developing]  ───────────►  [Job Ready]
(Lacks Core Foundation)     (Foundational / Trainee)    (Autonomous / Industry Ready)
```

### Class 1: Not Ready

*The candidate lacks the fundamental technical competencies, practical exposure, and professional context required to perform the occupation.*

- **Qualifying Evidence Criteria:**
  - Has zero or negligible demonstrable grasp of the essential skills required by the occupation.
  - Work experience (if any) is completely unrelated to the target occupation (e.g., hospitality worker evaluated for data science).
  - Possesses no technical projects, or only trivial copy-paste tutorial snippets lacking original implementation.
  - Shows no evidence of understanding modern developer workflows, toolchains, or core principles.
- **Typical Candidate Profiles:**
  - Complete career switchers without technical training, coursework, or portfolio.
  - Resumes listing high-level buzzwords with zero supporting project or experiential context.
- **Actionable Meaning:** Requires structured foundational education or intensive bootcamps before being employable in any technical capacity for this occupation.

---

### Class 2: Developing

*The candidate demonstrates foundational technical knowledge and basic implementation skills, but lacks the practical depth, production experience, or independence required for autonomous professional contribution.*

- **Qualifying Evidence Criteria:**
  - Demonstrates clear understanding of primary technical concepts (e.g., knows Python, OOP, SQL, data structures).
  - Has completed relevant academic coursework, personal portfolio projects, or an internship.
  - Work experience is either limited (e.g., < 1–2 years), junior-level, or consists primarily of guided student/academic work.
  - Can build small standalone applications or follow structured specifications, but lacks evidence of building production-grade, end-to-end, or scalable systems.
  - May have noticeable gaps in secondary tooling (e.g., CI/CD, containerization, cloud deployment, automated testing).
- **Typical Candidate Profiles:**
  - Recent computer science or STEM university graduates with good coursework and capstone projects.
  - Junior developers with 6–18 months of internship or entry-level experience.
  - Self-taught developers or bootcamp graduates with a functional GitHub portfolio of completed projects.
- **Actionable Meaning:** Highly suitable for junior positions, apprenticeships, internships, or structured graduate training programs with mentorship.

---

### Class 3: Job Ready

*The candidate demonstrates autonomous competence, verifiable practical application, and solid mastery of the core competencies required for the target occupation.*

- **Qualifying Evidence Criteria:**
  - Solid mastery over the essential core skills of the occupation (e.g., proficient in the relevant language, framework, database, and development environment).
  - Demonstrates substantial, relevant work experience (typically $\ge 2$ years) OR possesses an advanced, complex, production-level portfolio demonstrating end-to-end delivery.
  - Evidence of practical execution: built, tested, deployed, and maintained real software, data pipelines, or infrastructure.
  - Familiarity with modern engineering practices: version control (Git), automated testing, REST APIs, database design, and collaborative workflows.
  - Capable of resolving bugs, designing modular code, and delivering functional features independently with minimal onboarding.
- **Typical Candidate Profiles:**
  - Mid-level or senior software engineers, data analysts, or system administrators with verified professional tenure.
  - Highly accomplished junior candidates who have built substantial, deployed, open-source or commercial applications.
- **Actionable Meaning:** Immediately competitive for standard professional industry roles without foundational retraining.

---

## 5. Independent Evidence Evaluation Dimensions

Annotators must systematically review four independent evidence dimensions from the [`CandidateProfile`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Candidate_Profile/profile_schema.py#L79):

### Dimension 1: Essential Skill Proficiency
- **Proficient:** Demonstrates mastery of core programming languages, frameworks, and architecture needed for the role.
- **Foundational:** Understands syntax and primary concepts, but limited framework exposure or narrow technical breath.
- **Insufficient:** Missing the primary tools of the trade (e.g., applying for Backend Developer with only HTML/CSS).

### Dimension 2: Relevant Work Experience
- **Substantial and Direct:** $\ge 2$ years of direct professional experience performing duties corresponding to the target occupation.
- **Partial or Junior:** $\le 2$ years, internship experience, or experience in an adjacent technical role with transferable overlap.
- **Irrelevant or None:** No professional history or work history in non-technical, unrelated fields.

### Dimension 3: Practical Application & Projects
- **Production / End-to-End Systems:** Built, deployed, or contributed to multi-component systems (e.g., microservices, full-stack web apps with databases, data pipelines with analytics).
- **Academic or Demo Projects:** Small-scale course assignments, single-script utilities, or standard tutorial clones (e.g., basic To-Do app).
- **None Observed:** No project descriptions, repository references, or implementation details provided.

### Dimension 4: Academic Foundation & Certifications
- **Directly Aligned Degree:** B.S./M.S. in Computer Science, Software Engineering, Information Technology, or closely related engineering field.
- **Related / Quantitative Degree:** Mathematics, Physics, Electrical Engineering, or Statistics.
- **Non-Technical / None:** Unrelated degree or no formal credentials recorded.
- **Certifications:** Recognized industry credentials (AWS Certified Developer, CKA, RedHat, Azure Solutions Architect).

---

## 6. Decision Matrix for Annotators

The following matrix guides the synthesis of evidence across dimensions into a final class:

| Essential Skill Proficiency | Work Experience Relevance | Practical Application Evidence | Education / Certifications | Resulting Readiness Label |
|:---|:---|:---|:---|:---|
| **Proficient** | Substantial & Direct | Production / End-to-End | Aligned or Related | **Job Ready** |
| **Proficient** | Partial or Junior | Production / End-to-End | Any | **Job Ready** |
| **Foundational** | Substantial & Direct | Production / End-to-End | Aligned or Related | **Job Ready** |
| **Foundational** | Partial or Junior | Academic / Demo Projects | Aligned Degree | **Developing** |
| **Foundational** | Irrelevant or None | Production / End-to-End | Any | **Developing** |
| **Proficient** | Irrelevant or None | Academic / Demo Projects | Related Degree | **Developing** |
| **Insufficient** | Partial or Junior | Academic / Demo Projects | Any | **Developing** *(Edge Case)* |
| **Insufficient** | Irrelevant or None | Academic / Demo Projects | Non-Technical | **Not Ready** |
| **Foundational** | Irrelevant or None | None Observed | Non-Technical | **Not Ready** |
| **Insufficient** | Irrelevant or None | None Observed | Any | **Not Ready** |

---

## 7. Dataset Feasibility & Evidence Audit

Programmatic analysis of the 1,140 records in `Datasets/Processed/candidate_occupation_dataset.jsonl` yields the following evidence availability:

```
Total Records: 1,140
 ├── Master Resumes (500 records)
 │    ├── 401 records (80.2%)  ──> Complete Evidence: Skills + Experience + Education + Projects [High Confidence]
 │    ├──  95 records (19.0%)  ──> Substantial Evidence: Skills + Experience + Education [Medium-High Confidence]
 │    └──   4 records  (0.8%)  ──> Experience + Education + Projects (implicit skills) [Reviewable]
 │
 └── Synthetic Profiles (640 records)
      ├── 638 records (99.7%)  ──> Semi-structured: Declared Skills + Seniority + Exp Years [Silver / Coarse Only]
      └──   2 records  (0.3%)  ──> 0 Years Experience (Entry-Level) [Silver Only]
```

### Critical Annotatability Findings:
1. **Primary Ground-Truth Source (Master Resumes — 500 Records):**  
   - **401 master resumes** possess complete multi-modal evidence across all four dimensions (professional work history, detailed technical project descriptions, degree credentials, and normalized skills). These 401 records represent the ideal candidates for **rigorous, multi-annotator human gold-standard labeling**.
   - **95 master resumes** lack a distinct projects section, but provide full multi-year professional employment histories and accredited degrees. These can also be reliably annotated with high confidence.
2. **Synthetic Profiles Limitation (640 Records):**  
   - Synthetic profiles specify declared primary/secondary skills, target roles, seniority, and years of experience, but **completely lack project descriptions, educational credentials, and workplace narrative text**.
   - Human annotators evaluating synthetic profiles must rely on declared summary parameters rather than qualitative execution proof.
   - **Protocol Decision:** Do **not** ask human annotators to hallucinate project details for synthetic profiles. Synthetic records should either be annotated with explicit `confidence: "Medium"` / `"Low"`, or partitioned for secondary synthetic heuristic validation rather than gold-standard human evaluation.

---

## 8. Annotation Record Specification

Every completed human annotation must conform to [`AI/Dataset_Preparation/readiness_label_schema.json`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Dataset_Preparation/readiness_label_schema.json).

### Example: Verified "Job Ready" Annotation Record

```json
{
  "annotation_id": "mr_12__software_developer__ann",
  "pair_id": "mr_12__http://data.europa.eu/esco/occupation/f2b15a0e-e65a-438a-affb-29b9d50b77d1",
  "candidate_id": "mr_12",
  "candidate_source": "master_resumes",
  "target_occupation_uri": "http://data.europa.eu/esco/occupation/f2b15a0e-e65a-438a-affb-29b9d50b77d1",
  "target_occupation_title": "software developer",
  "readiness_label": "Job Ready",
  "confidence": "High",
  "evidence": {
    "essential_skill_proficiency": "Proficient",
    "work_experience_relevance": "Substantial_and_Direct",
    "practical_application_evidence": "Production_or_EndToEnd_Systems",
    "education_relevance": "Directly_Aligned_Degree",
    "certifications_observed": [],
    "key_evidence_summary": "Candidate holds a B.E. in Computer Science with 3 years of direct full-stack developer experience. Demonstrated practical mastery through 2 deployed projects utilizing React, Node.js, and PostgreSQL with Docker containerization."
  },
  "reviewer_status": "Verified",
  "annotator_id": "expert_reviewer_01",
  "annotation_timestamp": "2026-11-05T12:00:00Z",
  "annotation_notes": "Candidate demonstrates independent engineering competence across core software lifecycle. Strong project portfolio compensates for absence of vendor certifications."
}
```

### Example: Verified "Developing" Annotation Record

```json
{
  "annotation_id": "mr_88__data_scientist__ann",
  "pair_id": "mr_88__http://data.europa.eu/esco/occupation/258e46f9-0075-4a2e-adae-1ff0477e0f30",
  "candidate_id": "mr_88",
  "candidate_source": "master_resumes",
  "target_occupation_uri": "http://data.europa.eu/esco/occupation/258e46f9-0075-4a2e-adae-1ff0477e0f30",
  "target_occupation_title": "data scientist",
  "readiness_label": "Developing",
  "confidence": "High",
  "evidence": {
    "essential_skill_proficiency": "Foundational",
    "work_experience_relevance": "Partial_or_Junior",
    "practical_application_evidence": "Academic_or_Demo_Projects",
    "education_relevance": "Related_Degree",
    "certifications_observed": [],
    "key_evidence_summary": "Recent B.Sc. graduate in Statistics with 6 months of data internship experience. Demonstrates solid Python, Pandas, and exploratory data analysis skills on Kaggle datasets, but lacks experience in production ML pipelines or model deployment."
  },
  "reviewer_status": "Verified",
  "annotator_id": "expert_reviewer_02",
  "annotation_timestamp": "2026-11-05T12:15:00Z",
  "annotation_notes": "Strong quantitative foundation and enthusiasm. Needs mentorship in MLOps, CI/CD, and production serving before functioning as an autonomous data scientist."
}
```

---

## 9. Recommended Next Steps for M4.3 Execution

1. **Annotate Gold Pilot Batch ($N=100$ Master Resumes):**
   - Sample 100 master resumes possessing complete evidence ($N=401$ pool).
   - Have two independent technical reviewers annotate each candidate using the rubric.
   - Calculate Inter-Annotator Agreement (Cohen's Kappa / Krippendorff's Alpha). Target agreement: $\kappa \ge 0.75$.
2. **Reconcile Disagreements:**
   - Any record with conflicting labels (`Disputed`) is reviewed by a third senior reviewer to reach consensus and refine edge-case guidelines.
3. **Expand to Full Master Resume Benchmark ($N=400$):**
   - Produce a benchmark dataset of 400 verified gold-standard records for supervised model training and evaluation.

