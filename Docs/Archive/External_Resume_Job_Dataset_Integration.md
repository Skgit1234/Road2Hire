# Road2Hire — External Resume–Job Dataset Integration

**Author:** Road2Hire AI/ML Research & Engineering Team  
**Date:** November 2026  
**Status:** Completed & Validated  
**Target Output Directory:** `Datasets/Processed/External_Job_Resume_Matching/`  

---

## 1. Overview & Background

The external Resume–Job Matching benchmark dataset located in `Datasets/External/Job_Resume_Matching/` has been integrated into Road2Hire as a standardized, reusable candidate/job dataset and compatibility evaluation benchmark.

The source dataset is a large-scale curated benchmark containing:
- **`cv.csv` (194.0 MB):** 9,544 candidate resumes across 28 balanced target positions.
- **`job.csv` (32.9 MB):** 1,167 job postings across 5 balanced sectors.
- **`matches.csv` (19.7 MB):** 122,560 candidate–job matching pairs evaluated across 10 retrieval dimensions.

All source archives are treated as read-only. Standardized, validated artifacts are emitted into `Datasets/Processed/External_Job_Resume_Matching/` with zero modification to origin data.

---

## 2. Architectural Components

The integration is built upon six modular, maintainable components located in `AI/Dataset_Preparation/`:

```
AI/Dataset_Preparation/
├── external_dataset_loader.py          # Memory-efficient chunked streaming generators
├── external_candidate_adapter.py       # CandidateProfile v1.1.0 adapter with privacy safeguards
├── external_occupation_adapter.py      # Job requirement adapter with canonical ESCO grounding
├── external_dataset_validator.py       # Referential integrity, uniqueness, and score validator
├── external_compatibility_benchmark.py # Correlation and retrieval rank benchmark suite
├── integrate_external_dataset.py       # End-to-end integration CLI and pipeline orchestrator
└── __init__.py                         # Clean API exports
```

### Module Descriptions:

1. **`external_dataset_loader.py`**:
   Provides streaming generators (`stream_external_cvs`, `stream_external_jobs`, `stream_external_matches`) and batch loaders. Uses pandas chunking to parse multi-line resume/job text fields without memory bloat. Includes `safe_parse_json_list` to parse JSON lists, list objects, and comma-separated skill strings.

2. **`external_candidate_adapter.py`**:
   Adapts raw candidate rows into Road2Hire `CandidateProfile` (schema version `1.1.0`).
   - **Candidate Privacy:** Sets `candidate["name"] = "Not provided"`. Zero hallucination of personal contact information (email/phone = `None`).
   - **Taxonomy Normalization:** Normalizes `clean_skills_json` against ESCO concepts using `ESCOTaxonomy.find_skill()`. Mapped skills receive canonical preferred labels and concept URIs; unmapped skills are preserved with category `"unmapped"`.
   - **Structured Records:** Leverages deterministic section parsers for education and experience.
   - **Provenance:** Preserves `original_candidate_id`, `target_position`, `years_experience`, and raw text length in `metadata`.

3. **`external_occupation_adapter.py`**:
   Adapts job postings from `job.csv` into structured requirements conforming to `OccupationRequirementSummary`.
   - **ESCO Grounding:** Uses `RoleOccupationResolver` to resolve job titles against canonical ESCO occupations (`(esco_uri, esco_preferred_label)`).
   - **Preservation of Unmapped Roles:** Roles that do not resolve cleanly to ESCO are preserved with `esco_uri = None` and `is_esco_grounded = False` rather than forcing inaccurate mappings.
   - **Requirement Normalization:** Required skills are normalized against ESCO taxonomy.

4. **`external_dataset_validator.py`**:
   Rigorous two-stage validator:
   - *Stage 1 (Raw Validation):* Verifies file existence, row counts, 100% referential integrity (zero dangling `candidate_id` or `job_id` references), uniqueness of composite pairs, score bounds ($[0.0, 1.0]$), and label categories (`strong_positive`, `medium_positive`, `weak_positive`).
   - *Stage 2 (Output Validation):* Verifies line-by-line JSON formatting, schema compliance, and foreign-key alignment between processed `.jsonl` files.

5. **`external_compatibility_benchmark.py`**:
   Statistical alignment suite evaluating compatibility models against benchmark rankings.
   - Metrics: Pearson correlation $r$, Spearman rank correlation $\rho$, Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), and coefficient of determination $R^2$.
   - Segmented evaluation: Grouped by job category and benchmark `label_strength`.

6. **`integrate_external_dataset.py`**:
   CLI pipeline orchestrating input validation, transformation, streaming writing, output validation, and report generation.

---

## 3. Generated Processed Files

All processed outputs reside in `Datasets/Processed/External_Job_Resume_Matching/`:

| File Name | Format | Primary Identifier | Description |
|---|:---:|:---:|---|
| `external_candidates.jsonl` | JSON Lines | `metadata.original_candidate_id` | 9,544 standardized CandidateProfiles conforming to schema v1.1.0. |
| `external_jobs.jsonl` | JSON Lines | `job_id` | 1,167 structured job requirement records with ESCO grounding where available. |
| `external_compatibility_pairs.jsonl` | JSON Lines | `pair_id` (`ext_{cand}_{job}`) | 122,560 lightweight candidate-job pairs with 10 retrieval score dimensions. No duplicate raw text bodies. |
| `external_dataset_summary.json` | JSON | N/A | Machine-readable audit metrics, distributional statistics, and execution metadata. |
| `integration_report.md` | Markdown | N/A | Human-readable audit report summarizing dataset statistics and governance policy. |

---

## 4. CLI Usage Guide

### Full Integration Run:
```bash
.venv/Scripts/python -m AI.Dataset_Preparation.integrate_external_dataset
```

### Dry Run with Limits (Fast Testing):
```bash
.venv/Scripts/python -m AI.Dataset_Preparation.integrate_external_dataset --limit-candidates 50 --limit-jobs 20 --limit-matches 100
```

### Options:
- `--raw-dir <PATH>`: Path to raw CSV files (default: `Datasets/External/Job_Resume_Matching`).
- `--output-dir <PATH>`: Destination for processed artifacts (default: `Datasets/Processed/External_Job_Resume_Matching`).
- `--limit-candidates <N>`: Maximum candidate rows to process.
- `--limit-jobs <N>`: Maximum job rows to process.
- `--limit-matches <N>`: Maximum match rows to process.
- `--skip-validation`: Skip input and output integrity checks.
- `--verbose`: Enable debug logs.

---

## 5. Methodological Safeguards & Governance

> [!CAUTION]
> **Anti-Circularity and Anti-Contamination Mandate:**
> 1. **Do NOT Treat Compatibility as Career Readiness:**
>    The external dataset's `final_score` and `label_strength` represent pairwise retrieval compatibility (top-k search ranking). They do **NOT** reflect human ground-truth career readiness.
> 2. **Prohibition Against Supervised M4 Training:**
>    Under no circumstances should `matches.csv` scores be used as supervised ground truth for training or evaluating the M4 Career Readiness Classifier. Doing so would violate Road2Hire's non-circularity safeguards and introduce synthetic leakage.
> 3. **Approved Use Cases:**
>    - **Unlabeled Candidate Pool:** Candidate resumes may be sampled for independent, manual career-readiness annotation under official M4 guidelines.
>    - **M2/M3 Retrieval Benchmark:** Use `matches.csv` pairs to benchmark candidate-job matching algorithms, embedding similarity, and skill gap coverage against external ranking baselines.

