# Milestone M4 — Supervised Career Readiness Model Architecture & Pipeline

**Target Milestones:** M4.1 – M4.4  
**Pipeline Location:** [`AI/Readiness_Model/`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Readiness_Model)  
**Annotated Workbook:** [`Datasets/Processed/readiness_annotation.xlsx`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Datasets/Processed/readiness_annotation.xlsx)  
**Trained Artifact:** [`AI/Readiness_Model/saved_models/readiness_classifier_pipeline.joblib`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Readiness_Model/saved_models/readiness_classifier_pipeline.joblib)  
**Metadata:** [`AI/Readiness_Model/saved_models/model_metadata.json`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Readiness_Model/saved_models/model_metadata.json)  

---

## 1. Architectural Overview

Milestone M4 establishes the supervised career readiness classification capability for Road2Hire:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            MILESTONE M4 PIPELINE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [M4.1 & M4.2] Unified Candidate-Occupation Dataset                         │
│  ├── candidate_occupation_dataset.jsonl (1,140 records)                     │
│  └── Rich multi-modal resume evidence grounded in ESCO occupations          │
│                                                                             │
│  [M4.3] Career Readiness Label Strategy & Annotation Workbook               │
│  ├── Official Rubric (readiness_annotation_guidelines.md)                   │
│  ├── JSON Schema Contract (readiness_label_schema.json)                     │
│  ├── 100-Record Pilot Dataset (readiness_annotation_pilot.jsonl)            │
│  └── Completed Formatted Workbook (readiness_annotation.xlsx)               │
│                                                                             │
│  [M4.4] Model Training, Cross-Validation & Evaluation                       │
│  ├── Strict Data Leakage Prevention (dataset_loader.py)                     │
│  │   - Exclude 29 unlabeled / withheld records                              │
│  │   - Exclude PII, candidate IDs, pair IDs, and human rubric sub-ratings   │
│  ├── Deterministic Feature Engineering (feature_extractor.py)               │
│  │   - 9 multi-dimensional profile signals (skills, tenure, projects, edu)  │
│  ├── Repeated Stratified 3-Fold Cross-Validation (model_evaluator.py)       │
│  │   - Macro F1, Balanced Accuracy, Cohen's Kappa, Confusion Matrices       │
│  └── Model Serialization & Metadata Persistence (model_trainer.py)          │
│      - Serialized Pipeline & Metadata without candidate PII                 │
│      - Clean interface prepared for M4.5 SHAP explainability                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Methodological Disambiguation

Road2Hire strictly enforces three non-overlapping concepts across its machine learning pipelines:

| Dimension | Career Readiness (M4) | Candidate-Job Compatibility (`gold_labels`) | Skill Coverage Feature (M3) |
|:---|:---|:---|:---|
| **Question** | Is this individual qualified and ready to execute the core responsibilities of this occupation in industry? | Does this candidate match the specific requisition of employer X's job post? | What percentage of canonical taxonomy skills match resume strings? |
| **Target Label ($y$)** | $y \in \{\text{Not Ready}, \text{Developing}, \text{Job Ready}\}$ | $y \in [0.0, 1.0]$ compatibility score | N/A (Input feature $X$) |
| **Pipeline Role** | Supervised Target Label ($y$) | External Filter / Matcher | Numerical Input Feature ($X$) |

---

## 3. Dataset Composition & Deduplication

- **Total Pilot Batch:** 100 candidate–occupation records from `master_resumes.jsonl`.
- **Deduplication Audit:** 15 duplicate evidence clusters identified. Exactly **27 secondary duplicate instances** were withheld from labeling (`readiness_label: null`) to prevent data leakage across train/test splits.
- **Labeled Training Pool ($N=71$):** Exactly 71 candidate records carry verified ground-truth labels.
  - **Developing:** 52 (73.2%)
  - **Job Ready:** 16 (22.5%)
  - **Not Ready:** 3 (4.2%)
  - **Unlabeled Withheld:** 29 (excluded from training)

---

## 4. Evaluated Models & Benchmark Comparison

Evaluated using **Repeated Stratified 3-Fold Cross-Validation** (3 folds × 5 repeats = 15 iterations):

| Model | Mean Macro F1 | Std Dev | Balanced Acc | Cohen's Kappa (κ) | Train Macro F1 | Overfit Delta |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **dummy (Stratified)** | 0.3452 | ±0.0720 | 0.3531 | 0.0603 | 0.3231 | -0.0221 |
| **dummy (Most Frequent)** | 0.2818 | ±0.0039 | 0.3333 | 0.0000 | 0.2818 | +0.0000 |
| **logistic_regression** | **0.4814** | ±0.1443 | **0.5259** | **0.3289** | 0.8052 | +0.3238 |
| **random_forest** | **0.6375** | ±0.1415 | **0.6467** | **0.6775** | 0.9654 | +0.3279 |

---

## 5. M4.5 Explainability Readiness

The serialized pipeline in `AI/Readiness_Model/saved_models/readiness_classifier_pipeline.joblib` exposes a clean interface for SHAP feature attribution in M4.5:
```python
from AI.Readiness_Model.model_trainer import load_persisted_model, get_model_for_explainability

pipeline, metadata = load_persisted_model()
exp = get_model_for_explainability(pipeline)
classifier = exp["classifier"]
scaler = exp["scaler"]
feature_names = exp["feature_names"]
```
This isolates the model coefficients and tree splits without exposing candidate identifiers or PII.
