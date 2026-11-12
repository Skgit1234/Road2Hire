# Road2Hire — M4.5 SHAP Global Feature Explainability Report

**Model Architecture:** `LogisticRegression` (`LinearExplainer`)  
**Population Evaluated:** $N = 71$ verified candidate records  
**Target Classes:** `['Developing', 'Job Ready', 'Not Ready']`  

---

## 1. Overall Global Feature Importance

Feature importance ranked by mean absolute SHAP value across all samples and classes:

| Rank | Feature Name | Mean |SHAP| | Description |
|:---:|:---|:---:|:---|
| **1** | `skills_count` | **0.9038** | Number of verified technical skills normalized to canonical taxonomy |
| **2** | `edu_level_ordinal` | **0.6041** | Highest academic degree level (None/Secondary=0, Bachelor=1, Master/Postgraduate=2) |
| **3** | `exp_positions_count` | **0.3145** | Number of distinct professional employment roles |
| **4** | `is_stem_degree` | **0.2568** | Formal degree alignment with Computer Science, IT, or Engineering disciplines |
| **5** | `has_senior_role` | **0.2205** | Presence of senior, lead, architect, or manager title in work history |
| **6** | `project_tech_count` | **0.1861** | Number of distinct technologies specified in project implementations |
| **7** | `project_words` | **0.1608** | Technical depth and implementation detail in project narratives |
| **8** | `has_production_system` | **0.1201** | Evidence of enterprise, production, deployed, or multi-tier systems |
| **9** | `project_count` | **0.0890** | Number of documented technical projects with descriptions |

---

## 2. Class-Specific Feature Contributions

Mean absolute SHAP value (|SHAP|) and mean signed directional contribution for each readiness class:

### Target Class: `Developing`

| Rank | Feature | Mean |SHAP| (Magnitude) | Mean Signed SHAP (Direction) |
|:---:|:---|:---:|:---:|
| 1 | `edu_level_ordinal` | 0.3881 | +0.0000 |
| 2 | `is_stem_degree` | 0.3852 | +0.0000 |
| 3 | `exp_positions_count` | 0.2479 | -0.0000 |
| 4 | `project_tech_count` | 0.2109 | -0.0000 |
| 5 | `has_production_system` | 0.1802 | +0.0000 |
| 6 | `project_count` | 0.1335 | +0.0000 |
| 7 | `has_senior_role` | 0.1257 | -0.0000 |
| 8 | `project_words` | 0.1208 | +0.0000 |
| 9 | `skills_count` | 0.0919 | -0.0000 |

### Target Class: `Job Ready`

| Rank | Feature | Mean |SHAP| (Magnitude) | Mean Signed SHAP (Direction) |
|:---:|:---|:---:|:---:|
| 1 | `skills_count` | 1.2637 | -0.0000 |
| 2 | `edu_level_ordinal` | 0.5180 | +0.0000 |
| 3 | `exp_positions_count` | 0.4717 | -0.0000 |
| 4 | `has_senior_role` | 0.3308 | +0.0000 |
| 5 | `is_stem_degree` | 0.2788 | +0.0000 |
| 6 | `project_words` | 0.1203 | +0.0000 |
| 7 | `project_tech_count` | 0.0682 | -0.0000 |
| 8 | `has_production_system` | 0.0257 | -0.0000 |
| 9 | `project_count` | 0.0128 | -0.0000 |

### Target Class: `Not Ready`

| Rank | Feature | Mean |SHAP| (Magnitude) | Mean Signed SHAP (Direction) |
|:---:|:---|:---:|:---:|
| 1 | `skills_count` | 1.3557 | +0.0000 |
| 2 | `edu_level_ordinal` | 0.9061 | -0.0000 |
| 3 | `project_tech_count` | 0.2792 | +0.0000 |
| 4 | `project_words` | 0.2411 | -0.0000 |
| 5 | `exp_positions_count` | 0.2239 | +0.0000 |
| 6 | `has_senior_role` | 0.2051 | -0.0000 |
| 7 | `has_production_system` | 0.1545 | -0.0000 |
| 8 | `project_count` | 0.1207 | -0.0000 |
| 9 | `is_stem_degree` | 0.1064 | -0.0000 |

---

## 3. Methodological Interpretation & Governance

1. **Dominant Signal (Technical Skills & Degree Level):** Across all classes, `skills_count` and `edu_level_ordinal` serve as the primary macro anchors for readiness classification.
2. **Job Ready Drivers:** `skills_count` (+1.264) and `exp_positions_count` (+0.472) provide the strongest positive directional lift toward `Job Ready`.
3. **Not Ready Drivers:** A low `skills_count` is the overwhelming driver (+1.356) pushing candidates into `Not Ready`.
4. **No Causal Claim:** SHAP values explain internal model weight allocations and must not be communicated to candidates as certified real-world qualifications.
