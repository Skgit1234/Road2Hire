# External Dataset Audit Report: Job-Resume Matching Benchmark

**Audit Date:** 2026-11-06  
**Auditor:** Road2Hire Senior AI/ML Research Team  
**Dataset Location:** `Datasets/External/Job_Resume_Matching/`  
**Inspected Files:**
- `cv.csv` (194.0 MB)
- `job.csv` (32.9 MB)
- `matches.csv` (19.7 MB)

---

## 1. Executive Summary

A comprehensive structural, referential, and methodological audit was conducted on the newly acquired external job-resume matching dataset in `Datasets/External/Job_Resume_Matching/`.

The dataset constitutes a high-volume, synthetically curated bipartite matching benchmark comprising **9,544 candidate resumes**, **1,167 job postings**, and **122,560 candidate-job matching records**. 

### Primary Audit Findings:
1. **Data Completeness & Cleanliness:** All three files exhibit **zero null values** ($0.0\%$) and **zero duplicate records** in primary keys or unique text descriptions.
2. **Referential Integrity:** 100% of candidate and job references in `matches.csv` map to valid records in `cv.csv` and `job.csv` with zero dangling foreign keys.
3. **Discretized Match Labels:** `label_strength` in `matches.csv` consists exclusively of positive retrieval tiers (`strong_positive`, `medium_positive`, `weak_positive`). Mathematical audit confirms these labels are deterministic threshold buckets of `final_score` ($0.68 \le \text{strong}$, $0.58 \le \text{medium} < 0.68$, $\text{weak} < 0.58$), containing zero human ground-truth readiness annotations and zero negative examples.
4. **Methodological Recommendation:**
   - **DO NOT merge into M4 Career Readiness supervised training:** Compatibility scores cannot be substituted for career readiness without violating Road2Hire's core anti-circularity safeguards.
   - **Recommended Utilization:** Use `cv.csv` as an **unlabeled candidate pool** to sample candidates for independent manual readiness annotation; use `job.csv` and `matches.csv` as a **large-scale external benchmark for M2/M3 resume-job compatibility and hybrid retrieval algorithms**.

---

## 2. File Inventory & Dimensions

| File Name | On-Disk Size | Total Records (Rows) | Total Columns | Primary Key / Identifier | Null Count | Duplicate Key Count |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `cv.csv` | 194.0 MB | **9,544** | 11 | `candidate_id` (`cand_00000` – `cand_09543`) | 0 ($0.0\%$) | 0 ($0.0\%$) |
| `job.csv` | 32.9 MB | **1,167** | 10 | `job_id` (numeric 64-bit int) | 0 ($0.0\%$) | 0 ($0.0\%$) |
| `matches.csv` | 19.7 MB | **122,560** | 13 | Composite `(candidate_id, job_id)` | 0 ($0.0\%$) | 0 ($0.0\%$) |

*Note on raw line count:* `cv.csv` contains 183,718 text lines on disk due to multi-line formatting in `resume_text` and `experience_text`, resolving to exactly 9,544 distinct candidate rows.

---

## 3. Schema & Field Inspection

### A. Candidate Resumes (`cv.csv`)
| Column Name | Data Type | Null Count | Description & Value Distribution |
|---|:---:|:---:|---|
| `candidate_id` | `str` | 0 | Unique identifier, format `cand_XXXXX` (9,544 unique). |
| `source_row` | `int64` | 0 | Row index from origin dataset ($0$ to $9,543$). |
| `target_position` | `str` | 0 | Exactly 28 balanced target titles (340–342 candidates each). |
| `resume_text` | `str` | 0 | Full unparsed resume text (objective, experience, skills, education). |
| `clean_skills` | `str` | 0 | JSON string representation of extracted skill list. |
| `clean_skills_json` | `str` | 0 | Identical copy of `clean_skills` ($100\%$ identity). |
| `education_text` | `str` | 0 | Structured/semi-structured degree, field, and institution strings. |
| `experience_text` | `str` | 0 | Multi-line employment summary and responsibilities text. |
| `years_experience` | `float64` | 0 | Numeric experience years: Mean 5.55, Min 0.0, Median 5.0, Max 31.0. |
| `inferred_category` | `str` | 0 | Broad sector: `INFORMATION-TECHNOLOGY` (8,140), `FINANCE` (1,010), `SALES` (215), `BUSINESS-DEVELOPMENT` (83), `HR` (80), `UNKNOWN` (16). |
| `embedding` | `str` | 0 | 768-dimensional float vector stored as JSON array. |

### B. Job Postings (`job.csv`)
| Column Name | Data Type | Null Count | Description & Value Distribution |
|---|:---:|:---:|---|
| `job_id` | `int64` | 0 | Unique 64-bit integer job identifier (1,167 unique). |
| `job_title` | `str` | 0 | 720 distinct job titles. Top titles: Business Development Manager (53), HR Generalist (34), BDR (33). |
| `category` | `str` | 0 | Exactly 5 balanced categories: IT (240), Business Dev (239), Finance (236), Sales (232), HR (220). |
| `job_description` | `str` | 0 | Full original job posting text, including overview and responsibilities. |
| `job_text` | `str` | 0 | Structured concatenated representation: `Job title: ... Category: ... Skills: ...`. |
| `clean_skills` | `str` | 0 | JSON string list of required job competencies. |
| `clean_skills_json` | `str` | 0 | Identical copy of `clean_skills` ($100\%$ identity). |
| `education_text` | `str` | 0 | Academic requirement specifications. |
| `years_required` | `float64` | 0 | Stated experience threshold: Mean 14.30, Min 0.0, Median 10.0, Max 40.0. |
| `embedding` | `str` | 0 | 768-dimensional float vector stored as JSON array. |

### C. Matching Relationships (`matches.csv`)
| Column Name | Data Type | Null Count | Distribution & Summary Statistics |
|---|:---:|:---:|---|
| `candidate_id` | `str` | 0 | Foreign key mapping to `cv.csv` (9,532 unique matched). |
| `job_id` | `int64` | 0 | Foreign key mapping to `job.csv` (1,164 unique matched). |
| `final_score` | `float64` | 0 | Overall compatibility score: Mean $0.5857 \pm 0.0360$, Range $[0.4300, 0.7561]$. |
| `raw_score` | `float64` | 0 | Uncalibrated compatibility score: Mean $0.4359 \pm 0.0371$, Range $[0.3060, 0.6516]$. |
| `label_strength` | `str` | 0 | Three positive tiers: `medium_positive` (70,636; 57.6%), `weak_positive` (51,150; 41.7%), `strong_positive` (774; 0.6%). |
| `semantic_score` | `float64` | 0 | Text embedding cosine similarity: Mean $0.803 \pm 0.045$, Range $[0.547, 0.942]$. |
| `skill_score` | `float64` | 0 | Direct skill list overlap score: Mean $0.165 \pm 0.089$, Range $[0.000, 0.783]$. |
| `position_score` | `float64` | 0 | Title string/semantic overlap score: Mean $0.569 \pm 0.165$, Range $[0.000, 1.000]$. |
| `category_score` | `float64` | 0 | Category match indicator: Mean $0.692$, Values $\{0.0, 1.0\}$. |
| `experience_score` | `float64` | 0 | Experience seniority alignment score: Mean $0.676 \pm 0.350$, Range $[0.000, 1.000]$. |
| `education_score` | `float64` | 0 | Degree requirement alignment score: Mean $0.897 \pm 0.210$, Range $[0.300, 1.000]$. |
| `candidate_rank` | `int64` | 0 | 1-based rank of this job for the candidate ($1$ to $122$). |
| `candidate_rank_pct` | `float64` | 0 | Relative percentile ranking for candidate ($0.0$ to $1.0$). |

---

## 4. Matching Bipartite Graph & Referential Integrity

```
[Candidate Pool: 9,544]
      │ (9,532 matched candidates; 12 unmatched)
      ▼
┌────────────────────────────────────────────────────────┐
│             BIPARTITE MATCHING RELATIONSHIP            │
│                 122,560 Evaluated Pairs                │
│                                                        │
│  - Candidate Degree: Min 1, Max 122, Mean 12.86 matches│
│  - Job Posting Degree: Min 1, Max 725, Mean 105.3 pairs│
└────────────────────────────────────────────────────────┘
      ▲
      │ (1,164 matched jobs; 3 unmatched)
[Job Pool: 1,167]
```

### Referential Integrity Audit:
- **Foreign Key Validity:** $100\%$ valid. Every `candidate_id` in `matches.csv` exists in `cv.csv`. Every `job_id` exists in `job.csv`.
- **Unmatched Entities:**
  - 12 candidates in `cv.csv` have zero matches in `matches.csv` ($0.12\%$). These candidates hold specific niche roles (e.g. `cand_00865` Mechanical Engineer, `cand_01171` Executive - VAT, `cand_02860` Data Science Engineer).
  - 3 jobs in `job.csv` have zero matches in `matches.csv` ($0.26\%$: jobs `3901364174`, `3902693086`, `3902830704`).
- **Pair Uniqueness:** Zero duplicate `(candidate_id, job_id)` pairs exist across all 122,560 rows.

---

## 5. Match Labels & Compatibility Score Distributions

### Mathematical Analysis of `label_strength`:
Cross-tabulation of `label_strength` against `final_score` proves that `label_strength` is a synthetic discretization of `final_score`:

| Label Strength | Record Count | Percentage | Min Final Score | Mean Final Score | Max Final Score |
|---|:---:|:---:|:---:|:---:|:---:|
| `strong_positive` | 774 | 0.63% | **0.6800** | 0.6963 | 0.7561 |
| `medium_positive` | 70,636 | 57.64% | **0.5800** | 0.6081 | 0.6799 |
| `weak_positive` | 51,150 | 41.73% | **0.4300** | 0.5532 | 0.5799 |

### Critical Observations:
1. **Truncated Positive-Only Retrieval Pool:** The dataset is a filtered top-k retrieval result. There are **zero negative matches** (no `rejected`, `irrelevant`, or `poor_match` records).
2. **Dense Score Distribution:** `final_score` has a very narrow standard deviation ($\sigma = 0.0360$). The difference between a "weak" match ($0.579$) and a "medium" match ($0.580$) is an arbitrary boundary cut-off.

---

## 6. Mapping to Road2Hire Core Schemas

### A. Mapping to Candidate Profile Schema (`v1.1.0`)
| Road2Hire `CandidateProfile` Field | Source Column in `cv.csv` | Conversion Strategy |
|---|---|---|
| `candidate.name` | *None* | Set to `"Not provided"` (preserve privacy integrity). |
| `candidate.summary` | `resume_text` | Extract objective/intro sentence block. |
| `skills` | `clean_skills_json` | Map JSON skill strings through `ESCOTaxonomy` Trie mapper into canonical ESCO concepts. |
| `experience` | `experience_text`, `years_experience` | Parse structured `job_title`, company, and dates via `parse_experience_section()`. |
| `education` | `education_text` | Parse structured degree, field, and level via `parse_education_section()`. |
| `metadata.source_file` | `candidate_id` | Record `cv.csv` provenance. |

### B. Mapping to Occupation & Job Schemas (M2 & M3)
| Road2Hire Occupation Target | Source Column in `job.csv` | Conversion Strategy |
|---|---|---|
| Target Occupation Title | `job_title` | Resolve to ESCO canonical titles via `RoleOccupationResolver`. |
| Target Occupation URI | *None* | Lookup canonical ESCO concept URI using taxonomy mapper. |
| Required Skills | `clean_skills_json` | Map skills to canonical ESCO concepts. |
| Job Description Text | `job_description` | Text baseline for hybrid matching. |

### C. Mapping to Unified Dataset Schema (`candidate_occupation_dataset.jsonl`)
| Unified Record Field | Source in `matches.csv` / `cv.csv` / `job.csv` |
|---|---|
| `pair_id` | `f"ext_{candidate_id}_{job_id}"` |
| `candidate_id` | `candidate_id` |
| `candidate_source` | `"external_job_resume_matching"` |
| `target_occupation_title` | `job.csv: job_title` |
| `compatibility_score` | `matches.csv: final_score` |
| `gold_label` | `matches.csv: label_strength` (as retrieval compatibility label, **NOT** readiness) |

---

## 7. Methodological Evaluation: Readiness (M4) vs. Compatibility (M2/M3)

```
┌──────────────────────────────────────────────┐      ┌──────────────────────────────────────────────┐
│           CAREER READINESS (M4)              │      │       RESUME-JOB COMPATIBILITY (M2/M3)       │
├──────────────────────────────────────────────┤      ├──────────────────────────────────────────────┤
│ Focus: Candidate evidence maturity & depth   │      │ Focus: Candidate-Job pairwise overlap        │
│ Rubric: Practical skills, verified projects, │      │ Formula: Direct skill overlap, semantic sim, │
│         work history, production delivery    │      │          title similarity, education reqs    │
│ Target Classes: Not Ready / Developing /     │      │ Target Outputs: Compatibility score (0.0-1.0)│
│                 Job Ready                    │      │                 Retrieval rank (Top 10)      │
│ Ground Truth: Independent human annotation   │      │ Ground Truth: Algorithmic ranking / hiring   │
└──────────────────────────────────────────────┘      └──────────────────────────────────────────────┘
```

### Why this dataset CANNOT directly train M4 Career Readiness:
1. **Definitional Divergence:**
   A candidate may have a `strong_positive` match score for a Junior IT Support job simply because the resume mentions basic troubleshooting. However, that candidate is **not necessarily "Job Ready"** for independent production roles. Conversely, a seasoned Lead Data Engineer evaluated against a DevOps role might receive a `weak_positive` match score, while their intrinsic career readiness is **Job Ready**.
2. **Anti-Circularity Mandate:**
   Road2Hire's M4.3 and M4.4 methodological governance explicitly mandates:
   > *"Avoid circularity: Do not derive readiness labels directly from existing skill-gap coverage scores. Do not use gold-label compatibility scores as readiness labels."*
   Mapping `label_strength` or `final_score` to `readiness_label` would commit direct circularity, training the readiness model on automated retrieval scores rather than verified candidate competency.
3. **Absence of Negative Readiness Classes:**
   `matches.csv` contains only positive matching tiers ($100\%$ positive). M4 requires separating `Not Ready`, `Developing`, and `Job Ready`. A positive-only dataset cannot establish decision boundaries for `Not Ready` candidates.

---

## 8. Summary Recommendations & Actionable Next Steps

| Workstream | Recommended Action | Feasibility | Implementation Path |
|---|---|:---:|---|
| **M2/M3 Compatibility Benchmarking** | **Adopt** `matches.csv` as an external evaluation benchmark for Road2Hire's hybrid matching and ranking algorithms. | High | Ingest `job_id`, `candidate_id`, and `final_score` as an evaluation test set in `AI/Semantic_Matching/`. |
| **M4 Unlabeled Resume Pool** | **Adopt** `cv.csv` as a candidate source pool for future manual annotation rounds (M4.3 Phase 2). | High | Extract 100–200 diverse resumes across underrepresented occupations (e.g. Data Engineer, DevOps) and annotate using the official M4.3 rubric. |
| **M4 Supervised Training Labels** | **REJECT** using `label_strength` or `final_score` as supervised readiness training labels. | **Strictly Prohibited** | Enforce anti-circularity guidelines; do not substitute compatibility scores for readiness labels. |
| **Embedding Re-use** | **Do Not Use** the existing 768-dim embeddings in Road2Hire's pipeline. | Medium | Road2Hire standardizes on 384-dim `all-MiniLM-L6-v2`. Re-embed resume texts when integrating. |

---
*Report certified by Road2Hire Senior AI/ML Research Team.*

