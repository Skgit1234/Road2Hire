# Road2Hire — M4.5 SHAP Global Feature Explainability Report

**Model Architecture:** `LogisticRegression` (`LinearExplainer`)
**SHAP Background Population:** $N = 19$ Reviewed/Verified labeled records
**Target Classes:** `['Developing', 'Job Ready', 'Not Ready']`

---

## 1. Overall Global Feature Importance

Feature importance ranked by mean absolute SHAP value across all samples and classes:

| Rank | Feature Name | Mean |SHAP| | Description |
|:---:|:---|:---:|:---|
| **1** | `skills_count` | **0.9286** | Number of verified technical skills normalized to canonical taxonomy |
| **2** | `edu_level_ordinal` | **0.6122** | Highest academic degree level (None/Secondary=0, Bachelor=1, Master/Postgraduate=2) |
| **3** | `exp_positions_count` | **0.3378** | Number of distinct professional employment roles |
| **4** | `has_production_system` | **0.1535** | Evidence of enterprise, production, deployed, or multi-tier systems |
| **5** | `project_tech_count` | **0.1411** | Number of distinct technologies specified in project implementations |
| **6** | `has_senior_role` | **0.1237** | Presence of senior, lead, architect, or manager title in work history |
| **7** | `is_stem_degree` | **0.0856** | Formal degree alignment with Computer Science, IT, or Engineering disciplines |
| **8** | `project_words` | **0.0799** | Technical depth and implementation detail in project narratives |
| **9** | `project_count` | **0.0519** | Number of documented technical projects with descriptions |

---

## 2. Class-Specific Feature Contributions

Mean absolute SHAP value (|SHAP|) and mean signed directional contribution for each readiness class:

### Target Class: `Developing`

| Rank | Feature | Mean |SHAP| (Magnitude) | Mean Signed SHAP (Direction) |
|:---:|:---|:---:|:---:|
| 1 | `edu_level_ordinal` | 0.3934 | +0.0000 |
| 2 | `exp_positions_count` | 0.2662 | -0.0000 |
| 3 | `has_production_system` | 0.2302 | -0.0000 |
| 4 | `project_tech_count` | 0.1599 | +0.0000 |
| 5 | `is_stem_degree` | 0.1284 | -0.0000 |
| 6 | `skills_count` | 0.0945 | -0.0000 |
| 7 | `project_count` | 0.0778 | +0.0000 |
| 8 | `has_senior_role` | 0.0705 | -0.0000 |
| 9 | `project_words` | 0.0600 | -0.0000 |

### Target Class: `Job Ready`

| Rank | Feature | Mean |SHAP| (Magnitude) | Mean Signed SHAP (Direction) |
|:---:|:---|:---:|:---:|
| 1 | `skills_count` | 1.2985 | -0.0000 |
| 2 | `edu_level_ordinal` | 0.5250 | +0.0000 |
| 3 | `exp_positions_count` | 0.5067 | +0.0000 |
| 4 | `has_senior_role` | 0.1856 | +0.0000 |
| 5 | `is_stem_degree` | 0.0929 | +0.0000 |
| 6 | `project_words` | 0.0598 | -0.0000 |
| 7 | `project_tech_count` | 0.0517 | +0.0000 |
| 8 | `has_production_system` | 0.0328 | +0.0000 |
| 9 | `project_count` | 0.0075 | -0.0000 |

### Target Class: `Not Ready`

| Rank | Feature | Mean |SHAP| (Magnitude) | Mean Signed SHAP (Direction) |
|:---:|:---|:---:|:---:|
| 1 | `skills_count` | 1.3930 | -0.0000 |
| 2 | `edu_level_ordinal` | 0.9184 | +0.0000 |
| 3 | `exp_positions_count` | 0.2405 | -0.0000 |
| 4 | `project_tech_count` | 0.2116 | -0.0000 |
| 5 | `has_production_system` | 0.1974 | +0.0000 |
| 6 | `project_words` | 0.1198 | +0.0000 |
| 7 | `has_senior_role` | 0.1151 | -0.0000 |
| 8 | `project_count` | 0.0704 | -0.0000 |
| 9 | `is_stem_degree` | 0.0355 | +0.0000 |

---

## 3. Methodological Interpretation & Governance

1. **Eligible reference population:** Global values use only records marked Reviewed or Verified with a valid readiness label. Draft, disputed, flagged, and unlabeled records are excluded.
2. **Exploratory model provenance:** The persisted model was trained on 71 labeled pilot records without reviewer-status filtering. These explanations describe that existing model and do not validate its training labels.
3. **No Causal Claim:** SHAP values explain internal model weight allocations and must not be communicated to candidates as certified real-world qualifications.
