# Road2Hire — M4.2: Gold-Label Dataset Quality Audit Report

**Date of Audit**: 2026-11-05  
**Auditor**: Senior AI/ML Data Engineer  
**Dataset Evaluated**: `Datasets/gold_labels.json` (108 records)  
**Cross-Referenced Datasets**:
- `Datasets/synthetic_profiles.json` (640 synthetic candidate profiles)
- `Datasets/scraped_jobs.json` (2,500 real scraped job postings)
- `Datasets/master_resumes.jsonl` (4,817 parsed resume records)

---

## 1. Executive Summary & Status Breakdown

An exhaustive quality audit of all 108 records in `Datasets/gold_labels.json` was conducted to determine readiness for machine learning research, evaluate referential integrity, verify score consistency, and assess dataset task alignment.

### Status Classification Counts

| Status Category | Count | Percentage | Definition & Criteria |
|-----------------|------:|-----------:|------------------------|
| **Verified** | **0** | **0.0%** | Zero records carry an explicit `status: "verified"` or `review_status: "verified"` sign-off from human annotators. In accordance with strict auditing standards, no unconfirmed record is assumed verified. |
| **Pending** | **58** | **53.7%** | Records carrying an explicit `review_status: "pending"` tag, valid referential integrity, but lacking human reasoning text (`reasoning: ""`). |
| **Missing Status** | **48** | **44.4%** | Records with valid references, bounded scores, and complete human reasoning text, but **lacking an explicit verification or review status attribute**. |
| **Invalid** | **2** | **1.9%** | Records with broken referential integrity: job reference IDs do not exist in the referenced `scraped_jobs.json` dataset. |
| **Total** | **108** | **100.0%** | Complete population of `Datasets/gold_labels.json`. |

> [!IMPORTANT]
> **Schema Inconsistency Finding**: `Datasets/gold_labels.json` is not homogeneous. It consists of two distinct sub-cohorts:
> 1. **Cohort A (Records 0–47, 48 records)**: Schema `('composite', 'domain', 'location', 'overqualified', 'pair_id', 'reasoning', 'seniority', 'skills')`. Contains detailed reasoning text but has **no status field**.
> 2. **Cohort B (Records 48–107, 60 records)**: Schema `('composite', 'domain', 'gaps', 'job_family', 'location', 'matches', 'overqualified', 'pair_id', 'review_status', 'seniority', 'skills', 'strategy')`. Contains `matches` and `gaps` lists and explicitly has `review_status: "pending"`, but **completely lacks reasoning text** (`reasoning: ""`), and includes 2 broken job references.

---

## 2. Invalid Records & Referential Integrity Findings

### A. Candidate Reference Validation
- **Total Candidate IDs Checked**: 108
- **Valid Candidate References**: 108 / 108 (**100.0%**)
- **Candidate Source**: 100% of candidate IDs correspond to `profile_id` in `Datasets/synthetic_profiles.json` (79 unique profiles).
- **Critical Finding**: **Zero gold-label records evaluate real resumes from `Datasets/master_resumes.jsonl`**. All 108 records are strictly synthetic profile evaluations.

### B. Job Reference Validation
- **Total Job IDs Checked**: 108
- **Valid Job References**: 106 / 108 (**98.1%**)
- **Broken Job References**: 2 / 108 (**1.9%**)

#### Invalid Records Breakdown:
| Index | Pair ID | Extracted Job ID | Candidate ID | Failure Reason | Impact |
|:-----:|:-------:|:----------------:|:------------:|----------------|--------|
| **78** | `21_job_20` | `job_20` | `21` | Job ID `job_20` does not exist in `Datasets/scraped_jobs.json` (all scraped jobs use `linkedin_{digits}` format). | Unresolvable job metadata; cannot be matched to job title, company, or requirements. |
| **90** | `111_job_14` | `job_14` | `111` | Job ID `job_14` does not exist in `Datasets/scraped_jobs.json`. | Unresolvable job metadata; broken foreign key. |

---

## 3. Score Validation, Consistency & Distribution

### A. Score Bounding & Data Types
All score fields (`skills`, `seniority`, `domain`, `location`, `composite`) were verified:
- **Null values**: 0 across all records.
- **Non-numeric values**: 0 across all records.
- **Out-of-bounds scores (<0 or >100)**: 0 across all records.
- **Overqualified boolean**: Exactly 95 `False` and 13 `True` values.

| Score Dimension | Minimum | Maximum | Mean | Median | Range Check |
|-----------------|--------:|--------:|-----:|-------:|:-----------:|
| `skills` | 50.0 | 98.0 | 79.4 | 82.0 | Pass [0, 100] |
| `seniority` | 62.0 | 95.0 | 85.8 | 88.0 | Pass [0, 100] |
| `domain` | 62.0 | 90.0 | 77.9 | 78.0 | Pass [0, 100] |
| `location` | 60.0 | 97.0 | 74.2 | 70.0 | Pass [0, 100] |
| `composite` | 58.0 | 96.0 | 78.4 | 81.0 | Pass [0, 100] |

### B. Mathematical Composite Score Formula
Mathematical regression and exact formula testing revealed that the `composite` score is **strictly deterministic**:
$$\text{composite} = \text{round}\Big(0.50 \times \text{skills} + 0.15 \times \text{seniority} + 0.10 \times \text{domain} + 0.25 \times \text{location}\Big)$$

- **Mismatches across all 108 records**: **0**
- The composite score is not an independent holistic human judgment; it is a direct linear combination of the sub-dimension scores.

### C. Severe Score Truncation & Selection Bias
- **No Negative/Low Match Samples**: The minimum composite score in the entire dataset is **58.0**, and the minimum skill score is **50.0**.
- There are **zero negative samples** (e.g. cross-domain mismatches such as a dental surgeon applied to a software engineer role with 5% compatibility).
- Models evaluated or trained on this dataset would suffer from severe truncated-range bias and inability to discriminate poor fits.

---

## 4. Duplicate Detection & Reasoning Evidence

### A. Pair ID Duplication
- **Total Pair IDs**: 108
- **Unique Pair IDs**: 108
- **Duplicate Pairs**: **0**
- **Candidate Diversity**: 79 unique synthetic candidates (most evaluated candidate appears 4 times: profile `177`).
- **Job Diversity**: 86 unique job postings (most evaluated job appears 6 times: `linkedin_4387283659`).

### B. Human Reasoning Evidence Audit
- **Records with Detailed Human Reasoning (Cohort A)**: 48 records (100% of records 0–47). Average length: 82 characters. Provides explicit justification (e.g., `"Staff HR Dir × Sr Software Dev HR @Vernovis. Zero dev skills. Mumbai × Cincinnati."`).
- **Records with Missing Reasoning (Cohort B)**: 60 records (100% of records 48–107). Carry `reasoning: ""` (empty string).

---

## 5. Critical Task Alignment: Candidate-Job Compatibility vs. Career Readiness

> [!CAUTION]
> **Methodology Warning: Do NOT Treat These Labels as Career Readiness.**

The annotations in `Datasets/gold_labels.json` represent **Candidate-Job Compatibility (Job Recommendation / Hiring Fit)**, **NOT Career Readiness**. Treating them as interchangeable would invalidate research evaluation.

### Comparative Distinction:

| Dimension | `gold_labels.json` (Compatibility) | Career Readiness (Road2Hire Core Mission) |
|-----------|-------------------------------------|--------------------------------------------|
| **Target Object** | A specific employer's job opening at a specific company (e.g. Fullstack @ PwC, HR @ Vernovis). | A standardized occupation family defined by ESCO or O*NET (e.g. Software Developer, Data Scientist). |
| **Geographic Location** | **25% of composite score** is driven by geographic alignment (`location` field: Mumbai vs Cincinnati vs Bangalore). | **0% geographic dependence**. A student's occupational competence is independent of where a company happens to be headquartered. |
| **Seniority Level** | **15% of composite score** is driven by whether candidate's years of experience fit a specific requisition level ("Senior 8yr fits Mid-Senior"). | Evaluates whether a student / fresher possesses the essential skills to enter an occupation. |
| **Employer Idiosyncrasies** | Evaluates specific proprietary tech stacks, domain preferences (FinTech vs Retail), and `overqualified` flags. | Evaluates core competencies, knowledge groups, and transversal skills from standard taxonomy. |
| **Pedagogical Gap Actionability** | Answers: *"Should recruiter hire this candidate for this requisition today?"* | Answers: *"What missing essential skills must this student learn to become employable in this career?"* |

### Audit Determination:
`gold_labels.json` must be restricted to benchmarking candidate-job matching and recommendation models. It **must not** be used as ground-truth for career readiness classification.

---

## 6. Records Suitable for Research Evaluation

| Subset | Count | Research Usability | Rationale |
|--------|------:|:------------------:|-----------|
| **Cohort A (Records 0–47)** | **48** | **Conditionally Usable** *(Compatibility Only)* | Complete scores, valid foreign keys, human reasoning text, no broken references. Can benchmark candidate-job matching, but requires note that explicit review status was omitted. |
| **Cohort B (Valid Pending, Records 48–107)** | **58** | **Unusable without Review** | Lacks human reasoning text; explicitly marked `pending`. Cannot serve as gold test benchmark without human sign-off. |
| **Cohort B (Invalid References, #78 & #90)** | **2** | **Quarantined / Rejected** | Broken job foreign keys (`job_20`, `job_14`). Cannot be linked to job metadata. |
| **Total Suitable for Career Readiness** | **0** | **Unusable** | Incompatible task formulation (evaluates location/seniority fit for specific employer, not occupational competence). |

---

## 7. Recommended Next Steps

1. **Quarantine Records #78 and #90**: Remove or correct the invalid job references `21_job_20` and `111_job_14` before using Cohort B.
2. **Complete Pending Reviews**: Have domain annotators review the 58 pending records in Cohort B and supply reasoning justification before promoting them to gold standard.
3. **Harmonize Schema**: Add an explicit `review_status: "verified"` field to Cohort A once verified, standardizing the schema to 12 fields across all records.
4. **Construct Real-World Resume Benchmark**: Because 100% of current gold pairs use synthetic profiles, construct an annotated benchmark pairing real resumes from `master_resumes.jsonl` with ESCO target occupations.
5. **Separate Readiness Evaluation**: Design a distinct ground-truth dataset for Career Readiness based on ESCO essential skill mastery, independent of employer location or requisition seniority constraints.

