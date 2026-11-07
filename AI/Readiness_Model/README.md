# AI Readiness Model Package (M4.4)

## Overview

The `AI/Readiness_Model/` package provides a supervised machine learning pipeline for predicting candidate career readiness against canonical target occupations (ESCO framework).

```
                      ┌──────────────────────────────────────────────┐
                      │    Datasets/Processed/                       │
                      │    readiness_annotation.xlsx (N=100)         │
                      └──────────────────────┬───────────────────────┘
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │     dataset_loader.py     │
                               │  - Exclude 29 unlabeled   │
                               │  - Retain 71 labeled rows │
                               │  - Zero PII / IDs in X    │
                               └─────────────┬─────────────┘
                                             │
                                             ▼
                      ┌──────────────────────────────────────────────┐
                      │    Readiness Pipeline (model_trainer.py)     │
                      │                                              │
                      │  ┌────────────────────────────────────────┐  │
                      │  │ 1. ReadinessFeatureExtractor           │  │
                      │  │    (9 deterministic features)          │  │
                      │  └───────────────────┬────────────────────┘  │
                      │                      ▼                       │
                      │  ┌────────────────────────────────────────┐  │
                      │  │ 2. StandardScaler                      │  │
                      │  └───────────────────┬────────────────────┘  │
                      │                      ▼                       │
                      │  ┌────────────────────────────────────────┐  │
                      │  │ 3. Classifier                          │  │
                      │  │    - LogisticRegression (Primary)      │  │
                      │  │    - RandomForestClassifier            │  │
                      │  │    - DummyClassifier (Baselines)       │  │
                      │  └────────────────────────────────────────┘  │
                      └──────────────────────┬───────────────────────┘
                                             │
                                             ▼
                      ┌──────────────────────────────────────────────┐
                      │    Repeated Stratified 3-Fold CV (15 runs)   │
                      │    - Macro F1, Balanced Acc, Kappa           │
                      │    - Per-class Precision, Recall, F1         │
                      │    - Cumulative Confusion Matrix             │
                      └──────────────────────────────────────────────┘
```

---

## 1. Feature Representation

The 9 features in `ReadinessFeatureExtractor` represent multi-dimensional career readiness extracted directly from candidate resume text:

| Feature Name | Description | Source Field |
|:---|:---|:---|
| `skills_count` | Number of normalized technical skills | `skills` |
| `exp_positions_count` | Number of professional employment positions | `experience_summary` |
| `has_senior_role` | Binary flag for senior/lead/architect title keywords | `experience_summary` |
| `project_count` | Number of documented technical projects | `projects_summary` |
| `project_words` | Word count of project descriptions (detail depth) | `projects_summary` |
| `project_tech_count` | Explicit technologies mentioned in project specifications | `projects_summary` |
| `has_production_system`| Binary indicator for enterprise/production/lifecycle keywords | `projects_summary` |
| `edu_level_ordinal` | Ordinal tier: 0 (None/HSC), 1 (Bachelor/BE/BSc), 2 (Master/ME/MCA/PGP) | `education_summary` |
| `is_stem_degree` | Binary flag for STEM/Computer/IT/Engineering degree | `education_summary` |

---

## 2. Key Safeguards & Anti-Circularity

1. **Strict ID & PII Exclusion:** All candidate identifiers (`candidate_id`, `annotation_id`, `pair_id`), personal contact info, and employer/university names are stripped from $X$.
2. **Annotation Rubric Separation:** Human intermediate ratings (Columns 9–12) and reviewer commentary are completely excluded from features to prevent circular ground-truth leakage.
3. **No M3 Score Proxying:** M3 skill coverage scores and gold compatibility labels are never used as features or targets.
4. **Fold-Enclosed Preprocessing:** All feature scaling and extraction are performed inside each cross-validation training fold using `sklearn.pipeline.Pipeline`.

---

## 3. Evaluation Summary (N=71 Labeled Records)

Repeated Stratified 3-Fold Cross-Validation (3 folds × 5 repeats = 15 iterations):

| Model | Mean Macro F1 | Std Dev | Balanced Acc | Cohen's Kappa (κ) | Train Macro F1 | Overfit Delta |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **dummy** | 0.3452 | ±0.0720 | 0.3531 | 0.0603 | 0.3231 | -0.0221 |
| **dummy_most_frequent** | 0.2818 | ±0.0039 | 0.3333 | 0.0000 | 0.2818 | +0.0000 |
| **logistic_regression** | **0.4814** | ±0.1443 | **0.5259** | **0.3289** | 0.8052 | +0.3238 |
| **random_forest** | **0.6375** | ±0.1415 | **0.6467** | **0.6775** | 0.9654 | +0.3279 |

---

## 4. Persisted Artifacts

Saved in `AI/Readiness_Model/saved_models/`:
- `readiness_classifier_pipeline.joblib`: Trained scikit-learn Pipeline on all 71 labeled records.
- `model_metadata.json`: Machine-readable metadata (version, target classes, feature names, empirical feature distribution statistics, cross-validation metrics, timestamp, seed, known limitations). Zero candidate PII.

---

## 5. Out-of-Distribution (OOD) Detection

Candidate profiles derived from unconstrained resumes may present feature values significantly outside the range observed in the $N=71$ training cohort. To protect against unmonitored model extrapolation, the `ReadinessOODDetector` flags anomalies based on empirical bounds and standard deviations ($|z| > 3.0$):

```python
from AI.Readiness_Model import ReadinessOODDetector, load_persisted_model

pipeline, metadata = load_persisted_model()
detector = ReadinessOODDetector.from_metadata(metadata)

# Evaluate candidate features
result = detector.detect_from_features(candidate_features_dict)
if result.is_ood:
    print(f"OOD Warnings: {result.warnings}")
    print(f"Feature-level diagnostics: {result.feature_diagnostics}")
```

### Empirical Feature Distribution ($N=71$)

| Feature | Min | Max | Mean | Std | P25 | Median | P75 | IQR | Bounds |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| `skills_count` | 0.0 | 14.0 | 6.94 | 3.32 | 5.0 | 7.0 | 9.0 | 4.0 | $[0.0, 14.0]$ |
| `exp_positions_count` | 0.0 | 4.0 | 1.34 | 1.08 | 1.0 | 1.0 | 2.0 | 1.0 | $[0.0, 4.0]$ |
| `has_senior_role` | 0.0 | 1.0 | 0.17 | 0.38 | 0.0 | 0.0 | 0.0 | 0.0 | $\{0, 1\}$ |
| `project_count` | 0.0 | 5.0 | 2.37 | 1.09 | 2.0 | 2.0 | 3.0 | 1.0 | $[0.0, 5.0]$ |
| `project_words` | 0.0 | 258.0 | 94.32 | 48.74 | 60.0 | 88.0 | 125.0 | 65.0 | $[0.0, 258.0]$ |
| `project_tech_count` | 0.0 | 16.0 | 5.66 | 3.44 | 3.0 | 5.0 | 8.0 | 5.0 | $[0.0, 16.0]$ |
| `has_production_system`| 0.0 | 1.0 | 0.44 | 0.50 | 0.0 | 0.0 | 1.0 | 1.0 | $\{0, 1\}$ |
| `edu_level_ordinal` | 1.0 | 2.0 | 1.25 | 0.44 | 1.0 | 1.0 | 1.5 | 0.5 | $[1.0, 2.0]$ |
| `is_stem_degree` | 0.0 | 1.0 | 0.86 | 0.35 | 1.0 | 1.0 | 1.0 | 0.0 | $\{0, 1\}$ |

---

## 6. M4.5 SHAP Explainability Interface

Milestone M4.5 introduces native SHAP-based local and global model explainability via `ReadinessModelExplainer`.

### Key Capabilities
- **Exact Mathematical Attribution:** Uses `shap.LinearExplainer` on scaled feature inputs with the trained `LogisticRegression` pipeline, satisfying efficiency axioms ($\text{base\_value} + \sum \phi_i = f(x)$).
- **Multiclass Support:** Decomposes signed SHAP contributions across all 3 readiness classes (`Developing`, `Job Ready`, `Not Ready`).
- **Standardized Structured Output:** Returns class probabilities, top positive/negative factors, cumulative waterfall steps, and frontend-ready visualization data.
- **Strict Governance:** SHAP values explain statistical model behavior and do NOT imply causal qualification or certification.

### Usage Example
```python
from AI.Readiness_Model import ReadinessModelExplainer

# Initialize explainer with persisted pipeline and background dataset
explainer = ReadinessModelExplainer()

# Explain an unseen candidate instance (raw evidence dict)
candidate_evidence = {
    "skills_text": "Python, Django, PostgreSQL, Docker, AWS, Git",
    "experience_text": "Senior Backend Developer at Acme Corp (4 years); Software Engineer at Globex (2 years)",
    "projects_text": "Scalable REST microservice deployed to production handling 10k requests/sec",
    "education_text": "B.Tech in Computer Science and Engineering",
}

explanation = explainer.explain_instance(candidate_evidence)

print(f"Predicted Class: {explanation['predicted_class']}")
print(f"Probabilities: {explanation['class_probabilities']}")
print(f"Summary: {explanation['explanation']['human_readable_summary']}")
print(f"Top Positive Factors: {explanation['explanation']['top_positive_factors']}")
```

### Persisted Explainability Artifacts
- `AI/Readiness_Model/saved_models/global_shap_importance.json`: Machine-readable global feature importance and class-specific signed contributions.
- `AI/Readiness_Model/shap_explainability_report.md`: Markdown summary of global feature rankings, directional dynamics, and governance guidelines.


