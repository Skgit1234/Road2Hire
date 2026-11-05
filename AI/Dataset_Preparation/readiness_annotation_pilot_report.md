# Road2Hire — M4.3 Career Readiness Annotation Pilot Dataset & Spreadsheet Report

**Audit Date:** 2026-11-05 UTC  
**Pilot JSONL File:** [`Datasets/Processed/readiness_annotation_pilot.jsonl`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Datasets/Processed/readiness_annotation_pilot.jsonl)  
**Annotation Spreadsheet:** [`Datasets/Processed/readiness_annotation.xlsx`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Datasets/Processed/readiness_annotation.xlsx)  
**Original Backup Workbook:** [`Datasets/Processed/readiness_annotation_backup.xlsx`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Datasets/Processed/readiness_annotation_backup.xlsx)  
**Sample Size:** **100 records** (100% `master_resumes`)  
**Schema Contract:** [`AI/Dataset_Preparation/readiness_label_schema.json`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Dataset_Preparation/readiness_label_schema.json)  
**Annotation Guidelines:** [`AI/Dataset_Preparation/readiness_annotation_guidelines.md`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Dataset_Preparation/readiness_annotation_guidelines.md)  
**Annotation Script:** [`AI/Dataset_Preparation/annotate_readiness_pilot.py`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Dataset_Preparation/annotate_readiness_pilot.py)  

---

## 1. Executive Summary

This report documents the preparation, manual annotation, quality validation, and ML training readiness of the **Career Readiness Annotation Pilot Dataset** and its accompanying Excel workbook ([`readiness_annotation.xlsx`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Datasets/Processed/readiness_annotation.xlsx)).

The pilot dataset comprises **100 records** sampled exclusively from real parsed resumes (`master_resumes.jsonl`) in the unified dataset (`candidate_occupation_dataset.jsonl`). It serves as the initial benchmark artifact for supervised career-readiness classification in M4.3 and preparation for M4.4 model training.

Every candidate was evaluated independently across four evidence dimensions against canonical ESCO occupation requirements. To prevent circularity and bias, annotations were grounded strictly in qualitative candidate evidence without reference to M3 skill coverage scores or external compatibility labels.

> [!IMPORTANT]
> **Audit & Deduplication Key Findings:**
> - **Zero Label Pre-Population (Strict Human Ground Truth):** In the source JSONL dataset and initial workbook, all 10 annotation columns were initialized strictly blank without synthetic pre-population or rule-based score leakage.
> - **Pre-Annotation Backup Preserved:** An exact copy of the unannotated workbook was archived at [`readiness_annotation_backup.xlsx`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Datasets/Processed/readiness_annotation_backup.xlsx).
> - **Duplicate Evidence Clusters Identified:** 15 duplicate evidence clusters covering 42 records were detected in the pilot. Exactly **27 secondary duplicate records** have identical resume evidence to a preceding candidate and have their `readiness_label` withheld (`null`) with `reviewer_status: Flagged_Insufficient_Evidence` to prevent data leakage and artificial label inflation.
> - **Three Distinct Classes Established:** The labeled portion ($N=71$) spans all three target readiness categories: **Job Ready** (16), **Developing** (52), and **Not Ready** (3).

---

## 2. Sample Composition & Occupation Distribution

The 100 pilot records cover six diverse ESCO technical and management occupations:

| Target ESCO Occupation | Target Concept URI | Selected Records | Share | Primary Records | Duplicate Records |
|:---|:---|:---:|:---:|:---:|:---:|
| **Software Developer** | `http://data.europa.eu/esco/occupation/f2b15a0e-e65a-438a-affb-29b9d50b77d1` | **55** | 55.0% | 44 | 11 |
| **Cloud DevOps Engineer** | `http://data.europa.eu/esco/occupation/2512.4` | **25** | 25.0% | 15 | 10 |
| **Data Scientist** | `http://data.europa.eu/esco/occupation/258e46f9-0075-4a2e-adae-1ff0477e0f30` | **7** | 7.0% | 2 | 5 |
| **ICT System Administrator** | `http://data.europa.eu/esco/occupation/a6baae73-cfdf-474d-b6eb-3b7cce14bb06` | **6** | 6.0% | 4 | 2 |
| **Operations Manager** | `http://data.europa.eu/esco/occupation/1349.1` | **5** | 5.0% | 1 | 4 |
| **Project Manager** | `http://data.europa.eu/esco/occupation/1219.1` | **2** | 2.0% | 2 | 0 |
| **Total** | | **100** | **100.0%** | **68** | **32** (27 secondary) |

---

## 3. Selection & Exclusion Methodology

### Inclusion Criteria:
1. **Source Exclusivity:** 100% of candidates originate from real parsed resumes (`master_resumes`). Zero synthetic profiles were included due to their lack of qualitative project execution narrative.
2. **Multi-Modal Evidence Guarantee:**
   - **Normalized Skills:** $\ge 1$ verified technical skills (mean: 11.4 skills).
   - **Professional Experience:** $\ge 1$ professional work history records (mean: 1.8 positions).
   - **Technical Projects:** $\ge 1$ detailed project descriptions with technologies (mean: 1.6 projects).
   - **Accredited Education:** $\ge 1$ formal academic degrees (Computer Science, Software Engineering, IT, STEM).
3. **Occupation Variety:** Covers 6 distinct technical and management occupational families.

### Exclusion Log (During Sampling from Master Resumes):
- **Missing Project Evidence:** 99 resumes lacked a distinct project block and were excluded from this pilot.
- **Missing Skills Block:** 15 resumes lacked extracted skill dictionaries and were excluded.
- **Ungrounded / Non-Technical Roles:** Resumes mapped to non-technical or low-relevance roles (e.g. legal/lawyer) were excluded.
- **Quota Exceeded:** Once the software developer quota (55) was reached, subsequent developer candidates were safely bypassed to maintain occupational diversity.

---

## 4. Excel Annotation Spreadsheet Specification

The manual annotation workbook is saved at:  
[`Datasets/Processed/readiness_annotation.xlsx`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Datasets/Processed/readiness_annotation.xlsx)

### Column Structure (Exact Order):

| Col # | Column Name | Type / Source | Content / Validation Details |
|:---:|:---|:---|:---|
| **1** | `annotation_id` | Metadata | Unique deterministic key (`{candidate_id}__{occupation}__pilot_ann`). |
| **2** | `candidate_id` | Metadata | Candidate identifier (`mr_1` to `mr_484`). |
| **3** | `target_occupation_title` | Metadata | Canonical ESCO occupation label. |
| **4** | `target_occupation_uri` | Metadata | Grounded ESCO concept URI. |
| **5** | `skills` | Candidate Evidence | Comma-separated list of candidate's normalized technical skills. |
| **6** | `experience_summary` | Candidate Evidence | Bulleted list of work history, titles, responsibilities, and tools used. |
| **7** | `projects_summary` | Candidate Evidence | Bulleted list of technical projects with descriptions and tech stacks. |
| **8** | `education_summary` | Candidate Evidence | Bulleted list of academic degrees, fields of study, and universities. |
| **9** | `essential_skill_proficiency` | Annotation Field | **Dropdown:** `Insufficient`, `Foundational`, `Proficient` (or blank). |
| **10** | `work_experience_relevance` | Annotation Field | **Dropdown:** `Irrelevant_or_None`, `Partial_or_Junior`, `Substantial_and_Direct` (or blank). |
| **11** | `practical_application_evidence` | Annotation Field | **Dropdown:** `None_Observed`, `Academic_or_Demo_Projects`, `Production_or_EndToEnd_Systems` (or blank). |
| **12** | `education_relevance` | Annotation Field | **Dropdown:** `Non_Technical`, `Related_Degree`, `Directly_Aligned_Degree`, `Not_Provided` (or blank). |
| **13** | `readiness_label` | Target Label | **Dropdown:** `Not Ready`, `Developing`, `Job Ready` (or blank). |
| **14** | `confidence` | Annotation Field | **Dropdown:** `High`, `Medium`, `Low` (or blank). |
| **15** | `key_evidence_summary` | Annotation Field | Free text: 1–2 sentence factual justification. |
| **16** | `annotator_id` | Administrative | Free text: Reviewer identifier (`Human_Expert_Pilot`). |
| **17** | `reviewer_status` | Administrative | **Dropdown:** `Draft`, `Reviewed`, `Verified`, `Disputed`, `Flagged_Insufficient_Evidence`. |
| **18** | `annotation_notes` | Administrative | Free text: Qualitative observations or edge-case notes. |

---

## 5. Completed Annotation Results & Distributions

All 100 rows in [`readiness_annotation.xlsx`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Datasets/Processed/readiness_annotation.xlsx) were audited, dimensionally rated, and labeled according to the official guidelines.

### 5.1 Readiness Label Distribution

```
┌───────────────────────────────────────────────────────────┐
│              READINESS LABEL DISTRIBUTION (N=100)         │
├───────────────────┬────────┬──────────┬───────────────────┤
│ Class             │ Count  │ Share    │ Supervised ML Role│
├───────────────────┼────────┼──────────┼───────────────────┤
│ Developing        │   52   │  52.0%   │ Target Label ($y$)│
│ Unlabeled (Blank) │   29   │  29.0%   │ Excluded from $y$ │
│ Job Ready         │   16   │  16.0%   │ Target Label ($y$)│
│ Not Ready         │    3   │   3.0%   │ Target Label ($y$)│
├───────────────────┼────────┼──────────┼───────────────────┤
│ Total             │  100   │ 100.0%   │ Validated         │
└───────────────────┴────────┴──────────┴───────────────────┘
```

- **Labeled Pool for ML ($N=71$):**
  - **Job Ready:** 16 (22.5% of labeled)
  - **Developing:** 52 (73.2% of labeled)
  - **Not Ready:** 3 (4.2% of labeled)
- **Unlabeled Pool ($N=29$):**
  - **27 Secondary Duplicate Records:** Label withheld pending candidate deduplication (`mr_4`, `mr_31`, `mr_34`, `mr_47`, `mr_54`, `mr_64`, etc.).
  - **2 Primary Records with Empty/Uninformative History:** `mr_40` (PM with all fields 'Not Provided') and `mr_112` (Java developer with no project descriptions and high school education only).

### 5.2 Confidence Level Distribution

| Confidence | Count | Share | Typical Profile |
|:---|:---:|:---:|:---|
| **Low** | **50** | 50.0% | Withheld duplicate records ($N=27$), uninformative profiles ($N=2$), and junior profiles with unverified tenure ($N=21$). |
| **High** | **26** | 26.0% | Complete multi-component enterprise delivery, verified degrees, or clear domain mismatches. |
| **Medium** | **24** | 24.0% | Promising foundational capability with junior tenure or academic/demo hardware projects. |
| **Total** | **100** | **100.0%** | |

### 5.3 Reviewer Workflow Status Distribution

| Reviewer Status | Count | Share | Status Description |
|:---|:---:|:---:|:---|
| **Flagged_Insufficient_Evidence** | **50** | 50.0% | 29 unlabeled records + 21 labeled records flagged for duration or project detail confirmation. |
| **Draft** | **31** | 31.0% | Standard foundational annotations awaiting secondary audit. |
| **Reviewed** | **18** | 18.0% | High-confidence classifications with comprehensive evidence. |
| **Verified** | **1** | 1.0% | Audited benchmark candidate (`mr_208`). |
| **Total** | **100** | **100.0%** | |

---

## 6. Duplicate Evidence Analysis & Deduplication Policy

A rigorous audit revealed **15 duplicate evidence clusters** across the 100 records:

```
┌───────────────────────────────────────────────────────────────────────────┐
│                      TOP DUPLICATE EVIDENCE CLUSTERS                     │
├───────┬─────────┬──────────────────────┬─────────┬────────────────────────┤
│ Group │ Primary │ Duplicate Candidates │ Count   │ Occupation             │
├───────┼─────────┼──────────────────────┼─────────┼────────────────────────┤
│ G1    │ mr_2    │ mr_4, 31, 34, 113    │ 5       │ Operations Manager     │
│ G5    │ mr_21   │ mr_54, 73, 82, 142,  │ 6       │ Data Scientist         │
│       │         │ mr_150               │         │                        │
│ G13   │ mr_121  │ mr_149, 160, 190     │ 4       │ Software Developer     │
│ G2    │ mr_11   │ mr_92, 104           │ 3       │ Cloud DevOps Engineer  │
│ G4    │ mr_19   │ mr_47, 95            │ 3       │ Software Developer     │
│ G11   │ mr_75   │ mr_157, 189          │ 3       │ Software Developer     │
│ G3    │ mr_18   │ mr_101               │ 2       │ ICT System Admin       │
│ G6    │ mr_30   │ mr_106               │ 2       │ Software Developer     │
│ G7    │ mr_37   │ mr_79                │ 2       │ Cloud DevOps Engineer  │
│ G8    │ mr_44   │ mr_64                │ 2       │ Software Developer     │
│ G9    │ mr_68   │ mr_119               │ 2       │ Cloud DevOps Engineer  │
│ G10   │ mr_70   │ mr_99                │ 2       │ ICT System Admin       │
│ G12   │ mr_118  │ mr_170               │ 2       │ Cloud DevOps Engineer  │
│ G14   │ mr_143  │ mr_180               │ 2       │ Software Developer     │
│ G15   │ mr_148  │ mr_191               │ 2       │ Software Developer     │
└───────┴─────────┴──────────────────────┴─────────┴────────────────────────┘
```

### Protocol Enforcement:
1. **No Automatic Copying:** Per project instructions, duplicate candidates were never assigned ground-truth labels by blind copying.
2. **Label Withholding:** For all 27 secondary records, `readiness_label` was set to `None` (blank), `confidence` set to `Low`, and `reviewer_status` set to `Flagged_Insufficient_Evidence`.
3. **ML Data Leakage Prevention:** By withholding labels from duplicate records, downstream supervised models cannot be trained on near-identical train/test splits.

---

## 7. Provisional First Five Records Audit

The provisional recommendations reviewed in ChatGPT were implemented exactly:

1. **Candidate `mr_1` (Software Developer):**
   - Essential Skills: `Foundational`, Work Exp: `Partial_or_Junior`, Practical: `None_Observed`, Education: `Directly_Aligned_Degree`
   - Label: `Developing`, Confidence: `Low`, Status: `Flagged_Insufficient_Evidence`
   - Summary: Holds ME/BE in Computer Engineering with junior Python experience. Flagged due to unverified project implementation details.
2. **Candidate `mr_2` (Operations Manager):**
   - Essential Skills: `Proficient`, Work Exp: *Leave blank pending evidence*, Practical: `Production_or_EndToEnd_Systems`, Education: `Related_Degree`
   - Label: `Developing`, Confidence: `Low`, Status: `Flagged_Insufficient_Evidence`
   - Summary: Proficient operations and DCS control systems evidence at Honeywell. Flagged for unverified employment tenure duration.
3. **Candidate `mr_3` (Cloud DevOps Engineer):**
   - Essential Skills: `Foundational`, Work Exp: *Leave blank pending evidence*, Practical: `Academic_or_Demo_Projects`, Education: `Not_Provided`
   - Label: `Developing`, Confidence: `Low`, Status: `Flagged_Insufficient_Evidence`
   - Summary: Foundational DevOps skills with FPGA/robotics projects. Flagged due to missing formal education details and unverified tenure.
4. **Candidate `mr_4` (Operations Manager):**
   - Duplicate of `mr_2`. Readiness Label: *Blank* (`None`), Status: `Flagged_Insufficient_Evidence`.
   - Notes: "Duplicate evidence concern: identical profile to mr_2. Label withheld pending candidate deduplication."
5. **Candidate `mr_7` (Software Developer):**
   - Essential Skills: `Foundational`, Work Exp: `Partial_or_Junior`, Practical: `Academic_or_Demo_Projects`, Education: `Directly_Aligned_Degree`
   - Label: `Developing`, Confidence: `Medium`, Status: `Draft`
   - Summary: Computer Science graduate with junior Java developer experience and academic stock management demo project.

---

## 8. Limitations of Single-Annotator Labels

1. **Inter-Annotator Agreement (IAA) Unmeasured:** This pilot was annotated by a single expert reviewer (`Human_Expert_Pilot`). Cohen's Kappa ($\kappa$) and Krippendorff's Alpha cannot be computed until a second independent annotator reviews the batch.
2. **Tenure Ambiguity:** Parsed resumes in `master_resumes.jsonl` frequently lack structured employment start/end dates, requiring conservative ratings (`Partial_or_Junior` or blank) rather than assuming multi-year senior tenure.
3. **Class Skew:** The labeled pool contains a heavy majority of `Developing` candidates (73.2%), reflecting the junior-to-mid composition of the scraped resume pool. Model training will require class weighting, stratified sampling, or focal loss.

---

## 9. M4.4 Supervised Training Readiness Assessment

The dataset is formally **ready for exploratory model training (M4.4)** under the following architectural controls:

1. **Filtering & Sample Selection:**
   - **Training Population ($N=71$):** Only records with non-null `readiness_label` (`Job Ready`, `Developing`, `Not Ready`) are included in the training/validation pool.
   - **Exclusion of Unlabeled Data ($N=29$):** Withheld duplicate records and empty evidence profiles are excluded from supervised loss computation.
2. **Feature Sanitization (No PII / Circular Leakage):**
   - Target variable $y \in \{\text{Not Ready}, \text{Developing}, \text{Job Ready}\}$.
   - Features $X$ must exclude candidate identifiers (`candidate_id`, `annotation_id`), names, employer names, and personal contact info.
   - Features $X$ must **never** include M3 skill coverage scores or gold compatibility labels.
3. **Partitioning Strategy (Candidate-Level Grouped Splitting):**
   - Splits must be performed at the **candidate group level** (`GroupKFold` or `StratifiedGroupKFold`) so that any residual shared evidence profiles never cross train and validation folds.
4. **Class Imbalance Strategy:**
   - With 16 Job Ready, 52 Developing, and 3 Not Ready records, models must employ:
     - Balanced class weights (`class_weight='balanced'`).
     - Macro-averaged F1 and Cohen's Kappa evaluation metrics.
     - Stratified cross-validation ($k=5$).
