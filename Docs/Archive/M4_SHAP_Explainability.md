# Milestone M4.5 — SHAP Explainability for Career Readiness Prediction

**Target Milestone:** M4.5  
**Module Location:** [`AI/Readiness_Model/shap_explainer.py`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Readiness_Model/shap_explainer.py)  
**Trained Model Pipeline:** [`AI/Readiness_Model/saved_models/readiness_classifier_pipeline.joblib`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Readiness_Model/saved_models/readiness_classifier_pipeline.joblib)  
**Global Importance Artifact:** [`AI/Readiness_Model/saved_models/global_shap_importance.json`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Readiness_Model/saved_models/global_shap_importance.json)  
**Global Markdown Report:** [`AI/Readiness_Model/shap_explainability_report.md`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Readiness_Model/shap_explainability_report.md)  
**Test Suite:** [`Tests/AI/test_readiness_model_explainability.py`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Tests/AI/test_readiness_model_explainability.py)  

---

## 1. Executive Summary

Milestone **M4.5** integrates SHAP (SHapley Additive exPlanations) explainability into the Road2Hire career readiness prediction system. Building directly upon the trained M4.4 supervised pipeline (`LogisticRegression` with `StandardScaler` and `ReadinessFeatureExtractor`), this module provides mathematically exact local and global feature attribution across three readiness classes:
- **`Developing`**
- **`Job Ready`**
- **`Not Ready`**

### Core Methodological Principles:
1. **Mathematical Attribution, Not Causality:** SHAP values measure how specific feature values shift the model's internal log-odds / margin relative to the background reference population. They describe **statistical model behavior**, not causal guarantees or real-world certified qualifications.
2. **Efficiency Axiom Satisfaction:** For the linear model in scaled space, `shap.LinearExplainer` satisfies the local efficiency axiom exactly:
   $$\text{base\_value}_c + \sum_{i=1}^{D} \phi_{i, c} = f_c(x)$$
   where $f_c(x)$ is the linear decision function for class $c$, verified to within machine epsilon ($\le 10^{-15}$).
3. **Class-Relative Directionality:** In a multiclass model, a positive SHAP value ($\phi_{i, c} > 0$) indicates that feature $i$ increases the log-odds of classification for **target class $c$**. For instance, a high positive SHAP value for the `Not Ready` class indicates that the feature strongly pushes the prediction toward `Not Ready`.
4. **Zero Data Leakage:** Explanations operate solely on the 9 vetted candidate features. Candidate identifiers, reviewer sub-scores, and PII are strictly excluded.

---

## 2. Architecture & Pipeline Integration

The explainer integrates with the persisted M4.4 pipeline without retraining or modifying weights:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           M4.5 SHAP EXPLAINABILITY                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [Candidate Input]                                                          │
│  Raw Evidence Dict OR Feature Dict OR (1, 9) Array                          │
│                                                                             │
│  [Pipeline Ingestion]                                                       │
│  ├── ReadinessFeatureExtractor (deterministic 9 features)                   │
│  └── StandardScaler (scaled feature space Z)                                │
│                                                                             │
│  [Inference & Explanation Engine]                                           │
│  ├── LogisticRegression Decision Function & Probabilities                   │
│  └── shap.LinearExplainer(classifier, X_background_scaled)                  │
│                                                                             │
│  [Multiclass SHAP Decomposition]                                            │
│  ├── Matrix Shape: (1, 9, 3) -> [Developing, Job Ready, Not Ready]          │
│  ├── Base Values (Intercepts): [Developing: 1.12, Job Ready: 0.45, Not Ready: -1.57]
│  └── Exact Attribution per Class c: phi_{i, c}                             │
│                                                                             │
│  [Structured Output Contract]                                               │
│  ├── Predicted Class & Class Probabilities                                  │
│  ├── Target Class Explanation (Top Positive & Top Negative Factors)        │
│  ├── Cumulative Waterfall Steps (Base Value -> Step-by-Step Additions)      │
│  ├── Human-Readable Concise Narrative Summary                               │
│  └── Visualizer Payloads & Governance Disclaimers                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Explainer Selection & Mathematical Justification

| Explainer Option | Applicability | Computational Complexity | Exactness | Decision |
|:---|:---|:---|:---|:---|
| **`shap.LinearExplainer`** | Regularized Linear & Logistic Models | $O(D)$ per sample | **Exact** ($\epsilon \le 10^{-15}$) | **Selected** |
| `shap.TreeExplainer` | Tree Ensembles (RandomForest, XGBoost) | $O(T L D^2)$ | Exact on trees | Fallback for tree models |
| `shap.KernelExplainer` | Model-Agnostic Sampling | $O(N \cdot M \cdot \text{samples})$ | Approximate | Not needed (linear pipeline) |

Because the deployed classifier is a multinomial `LogisticRegression` with scaled features, `shap.LinearExplainer` provides exact game-theoretic Shapley values without sampling variance.

---

## 4. Global Feature Importance Findings

Evaluated over the verified annotated training population ($N = 71$):

### 4.1 Overall Feature Importance Ranking
Ranked by mean absolute SHAP value across all samples and classes ($\frac{1}{N \cdot C} \sum_{n, c} |\phi_{n, i, c}|$):

| Rank | Feature Name | Mean \|SHAP\| | Feature Interpretation |
|:---:|:---|:---:|:---|
| **1** | `skills_count` | **0.9038** | Primary driver: canonical technical skill breadth |
| **2** | `edu_level_ordinal` | **0.6041** | Highest academic attainment (None/Secondary, Bachelor, Master) |
| **3** | `exp_positions_count` | **0.3145** | Professional career positions / demonstrated employment tenure |
| **4** | `is_stem_degree` | **0.2568** | Alignment with CS, IT, or Engineering degrees |
| **5** | `has_senior_role` | **0.2205** | Senior, lead, architect, or manager title flag |
| **6** | `project_tech_count` | **0.1861** | Distinct technologies specified in project implementations |
| **7** | `project_words` | **0.1608** | Narrative depth and detail in technical project descriptions |
| **8** | `has_production_system`| **0.1201** | Production, enterprise, and deployment keywords in projects |
| **9** | `project_count` | **0.0890** | Total documented projects |

### 4.2 Class-Specific Feature Dynamics

- **`Job Ready` Class:**
  - Positive contributors: high `skills_count` (mean signed $+1.264$), extensive work experience `exp_positions_count` ($+0.472$), and advanced education `edu_level_ordinal` ($+0.518$).
  - Negative pull: candidates with 0 documented employment positions or minimal technical skills receive strong negative SHAP penalties.
- **`Not Ready` Class:**
  - Overwhelming driver: absence of verified technical skills (`skills_count = 0` contributes up to $+2.76$ toward `Not Ready`).
  - Secondary driver: lack of prior employment history (`exp_positions_count = 0`).
- **`Developing` Class:**
  - Moderate skill counts paired with formal degree credentials (`edu_level_ordinal`, `is_stem_degree`) stabilize candidates in `Developing` while work experience accumulates.

---

## 5. Structured Local Explanation Contract

Calling `ReadinessModelExplainer.explain_instance()` produces a JSON-serializable dictionary with the following schema:

```json
{
  "predicted_class": "Job Ready",
  "class_probabilities": {
    "Developing": 0.0821,
    "Job Ready": 0.8914,
    "Not Ready": 0.0265
  },
  "explanation": {
    "target_class_explained": "Job Ready",
    "base_value": 0.4497,
    "top_positive_factors": [
      {
        "feature": "skills_count",
        "display_name": "Skills Count",
        "feature_value": 14.0,
        "contribution": 1.4821,
        "direction_relative_to_target": "positive",
        "description": "Number of verified technical skills normalized to canonical taxonomy"
      }
    ],
    "top_negative_factors": [],
    "feature_contributions": [ ... ],
    "multiclass_contributions": {
      "Developing": [ ... ],
      "Job Ready": [ ... ],
      "Not Ready": [ ... ]
    },
    "human_readable_summary": "The model predicted 'Job Ready' with 89.1% confidence. The primary factors increasing probability for 'Job Ready' were: Skills Count, Exp Positions Count, Edu Level Ordinal."
  },
  "visualization_data": {
    "feature_importance_ranking": ["skills_count", "edu_level_ordinal", "exp_positions_count", ...],
    "waterfall_steps": [
      {"step": "base_value", "feature": "Expected Log-Odds (Intercept)", "contribution": 0.4497, "cumulative": 0.4497},
      {"step": "skills_count", "feature": "skills_count", "contribution": 1.4821, "cumulative": 1.9318}
    ],
    "class_probability_breakdown": {
      "Developing": 0.0821,
      "Job Ready": 0.8914,
      "Not Ready": 0.0265
    }
  },
  "model_version": "0.1.0-exploratory",
  "limitations": [
    "Exploratory model trained on an annotated pilot dataset (N=71).",
    "SHAP values describe statistical model behavior, not causal reasons for actual candidate competence.",
    "Contribution directions are relative to the specific target class being evaluated."
  ]
}
```

---

## 6. Verification & Test Coverage

The test suite in [`Tests/AI/test_readiness_model_explainability.py`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Tests/AI/test_readiness_model_explainability.py) guarantees:
1. **Mathematical Additivity (Efficiency Axiom):** $\max |\text{decision\_function} - (\text{base\_value} + \sum \phi_i)| < 10^{-6}$.
2. **Dimension Consistency:** Output array matches $(N, 9, 3)$ with 9 named features and 3 classes.
3. **Multiclass Attribution:** Explanations can be generated targeting any of the 3 classes.
4. **Input Flexibility:** Accepts raw text evidence dictionaries, pre-extracted feature dictionaries, or numpy arrays.
5. **Robust Edge Cases:** Missing, null, empty strings, and zero-value instances are handled gracefully without exceptions.
6. **Determinism:** Repeated calls on identical input yield identical numeric values.
7. **Model Invariance:** Calling the explainer does not mutate model weights, pipeline state, or decision boundaries.
8. **PII and Data Hygiene:** Global artifacts contain no candidate IDs or sensitive personal data.
