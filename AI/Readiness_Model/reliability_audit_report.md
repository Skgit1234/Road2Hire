# Road2Hire — M4 Career Readiness Model Reliability Audit Report

**Audit Date:** November 2026  
**Auditor:** Road2Hire AI/ML Research & Engineering Team  
**Scope:** M4 Supervised Career Readiness Classifier, Dataset Distribution, Feature Consistency, and Evaluation Integrity  
**Key Artifacts Inspected:**
- `AI/Readiness_Model/dataset_loader.py`
- `AI/Readiness_Model/feature_extractor.py`
- `AI/Readiness_Model/model_trainer.py`
- `AI/Readiness_Model/model_evaluator.py`
- `AI/Readiness_Model/shap_explainer.py`
- `AI/Readiness_Model/saved_models/readiness_classifier_pipeline.joblib`
- `AI/Readiness_Model/saved_models/model_metadata.json`
- `Datasets/Processed/readiness_annotation.xlsx`
- `AI/Dataset_Preparation/readiness_annotation_guidelines.md`

---

## 1. Executive Summary

A comprehensive reliability audit of the M4 Career Readiness Prediction Model and its training/inference infrastructure was conducted to diagnose prediction instability, evaluate statistical validity, and identify data leakage risks prior to backend integration.

### Primary Audit Conclusions:
1. **Feature Consistency is Maintained, but Extrapolates on Unseen Ranges:**
   The feature definitions, extraction regular expressions, and ordering between training (`dataset_loader.py` + `feature_extractor.py`) and inference (`pipeline.py` + `feature_extractor.py`) are strictly aligned. However, the training set features have narrow empirical bounds (e.g., `skills_count` max is 14.0). Real resumes presenting 15–25 skills heavily extrapolate into high positive log-odds for `Job Ready`.
2. **Architectural Root Cause of High Predictions with Low Skill Coverage:**
   The M4 classifier features (`skills_count`, `exp_positions_count`, `edu_level_ordinal`, `is_stem_degree`, etc.) capture **general candidate profile seniority and breadth**, rather than **occupation-specific skill coverage**. Because M3 skill coverage scores were intentionally excluded from M4 features to prevent circularity and leakage from human sub-ratings, a senior candidate with many skills in an unrelated domain receives high profile scores, resulting in high `Job Ready` probability despite low coverage for the target occupation.
3. **Severe Minority Class Bottleneck ($N=3$ for `Not Ready`):**
   The labeled dataset ($N=71$) contains only 3 instances of `Not Ready` (4.2%), 16 instances of `Job Ready` (22.5%), and 52 instances of `Developing` (73.2%). Evaluating the `Not Ready` class in cross-validation is statistically fragile: in 3-fold CV, exactly one test example exists per fold; in 5-fold CV, evaluation is mathematically invalid.
4. **Grouped Cross-Validation by Occupation is Infeasible:**
   All three `Not Ready` records belong to the `software developer` occupation. Grouping by occupation causes 100% of minority class instances to fall into a single fold, leaving other folds with zero test instances. Candidate-grouped validation is equivalent to standard K-Fold because all 71 labeled records already represent unique candidates.

---

## 2. Feature Extraction & Preprocessing Audit

### A. Feature Definition & Pipeline Alignment
The canonical feature vector consists of nine engineered features:
1. `skills_count`: Number of verified technical skills normalized to canonical taxonomy.
2. `exp_positions_count`: Count of distinct employment positions.
3. `has_senior_role`: Binary indicator for senior/lead/architect title in experience text.
4. `project_count`: Count of distinct project entries.
5. `project_words`: Word count across project descriptions.
6. `project_tech_count`: Count of distinct technologies mentioned in project `(Tech: ...)` tags.
7. `has_production_system`: Binary indicator for enterprise/production/billing systems.
8. `edu_level_ordinal`: Ordinal degree level ($0=\text{None/Secondary}, 1=\text{Bachelor}, 2=\text{Master/Postgraduate}$).
9. `is_stem_degree`: Binary indicator for formal CS, IT, or engineering degree.

### B. Preprocessing & Leakage Safeguards
- Preprocessing (`StandardScaler`) is encapsulated inside the `sklearn.pipeline.Pipeline`.
- When cross-validation is performed in `model_evaluator.py`, `StandardScaler` is fitted strictly on `X_train` within each fold and applied to `X_test`, preventing data leakage from global scaling statistics.

### C. Training Set Empirical Feature Bounds ($N=71$):

| Feature Name | Min | Mean | Std | Median | Max | Impact on Inference |
|---|:---:|:---:|:---:|:---:|:---:|---|
| `skills_count` | 0.0 | 6.94 | 4.06 | 6.0 | **14.0** | Candidates with 16–25 skills exceed max training value. |
| `exp_positions_count` | 1.0 | 1.37 | 0.57 | 1.0 | **3.0** | Candidates with 4+ positions exceed max training value. |
| `has_senior_role` | 0.0 | 0.10 | 0.30 | 0.0 | 1.0 | Binary domain $\{0, 1\}$. |
| `project_count` | 0.0 | 1.58 | 1.20 | 1.0 | **3.0** | Candidates with 4+ projects exceed max training value. |
| `project_words` | 0.0 | 34.38 | 28.19 | 32.0 | **88.0** | Detailed resumes easily exceed 88 project words. |
| `project_tech_count` | 0.0 | 4.21 | 4.72 | 2.0 | **15.0** | Rich tech stacks exceed 15 tech tags. |
| `has_production_system` | 0.0 | 0.24 | 0.43 | 0.0 | 1.0 | Binary domain $\{0, 1\}$. |
| `edu_level_ordinal` | 1.0 | 1.44 | 0.50 | 1.0 | 2.0 | Level 0 (no degree/secondary) never seen in training! |
| `is_stem_degree` | 0.0 | 0.82 | 0.39 | 1.0 | 1.0 | Binary domain $\{0, 1\}$. |

---

## 3. Persisted Model & Parameter Inspection

The persisted inference model is a regularized Multinomial Logistic Regression (`class_weight='balanced'`, $C=0.5$, `solver='lbfgs'`).

### Model Coefficients by Target Class:

| Feature Name | Developing | Job Ready | Not Ready | Interpretive Observation |
|---|:---:|:---:|:---:|---|
| `skills_count` | +0.109 | **+1.496** | **-1.605** | Dominant driver separating Job Ready from Not Ready. |
| `exp_positions_count` | -0.282 | **+0.536** | -0.254 | Strong positive contributor to Job Ready. |
| `has_senior_role` | +0.211 | -0.555 | +0.344 | Moderate influence; penalizes Job Ready if unsupported by depth. |
| `project_count` | +0.146 | -0.014 | -0.132 | Minor negative influence on Not Ready. |
| `project_words` | -0.137 | -0.136 | +0.273 | Weak regularization factor. |
| `project_tech_count` | +0.267 | +0.086 | **-0.354** | Protective against Not Ready. |
| `has_production_system` | -0.211 | +0.030 | +0.181 | Minor factor. |
| `edu_level_ordinal` | +0.391 | **+0.522** | **-0.913** | Higher degree strongly reduces Not Ready probability. |
| `is_stem_degree` | -0.498 | +0.360 | +0.138 | Positive contributor to Job Ready. |
| **Intercept** | **+1.120** | **+0.450** | **-1.570** | Baseline favors Developing prior to feature evidence. |

> [!IMPORTANT]
> **Mechanics of High Readiness on Low Skill Coverage:**
> When an inference candidate possesses 16 skills (standardized $z = (16 - 6.94) / 4.04 = +2.24$), the term $2.24 \times 1.496 = +3.35$ adds directly to the log-odds of `Job Ready`. Combined with an engineering degree ($+0.36$) and a bachelor level ($+0.52$), the model predicts `Job Ready` with near certainty, unaware that the candidate's skills do not align with the specific target role.

---

## 4. Dataset Distribution & Leakage Audit

### A. Population Breakdown
- Total pilot records: 100
- Labeled records: **71** (100% independent candidates)
- Unlabeled records: **29** (27 duplicate candidate instances + 2 blank/unstated evidence profiles)
- Overlap between labeled and unlabeled candidate IDs: **0** ($0.0\%$)

### B. Occupational Skew
- `software developer`: 43 records (25 Developing, 15 Job Ready, 3 Not Ready)
- `cloud DevOps engineer`: 20 records (20 Developing, 0 Job Ready, 0 Not Ready)
- `ICT system administrator`: 4 records (4 Developing, 0 Job Ready, 0 Not Ready)
- `data scientist`: 2 records (1 Developing, 1 Job Ready, 0 Not Ready)
- `operations manager`: 1 record (1 Developing, 0 Job Ready, 0 Not Ready)
- `project manager`: 1 record (1 Developing, 0 Job Ready, 0 Not Ready)

---

## 5. Confirmed Problems vs. Potential Risks

### A. Confirmed Problems
1. **Unbounded Extrapolation for Rich Resumes:**
   The model does not check whether incoming feature values exceed training boundaries. A candidate with 25 skills or 6 positions causes runaway probability estimation without warning.
2. **Missing Out-of-Distribution (OOD) Signaling:**
   The pipeline previously had no mechanism to inform users or downstream systems that a candidate's features lay outside the training distribution.
3. **Misleading Probability Interpretation:**
   Model probabilities were previously labeled as "confidence", which can be misinterpreted by users as certified real-world readiness.
4. **Unrepresented Low-Education Range:**
   Zero candidates in the training set have `edu_level_ordinal == 0.0`. Evaluating candidates without secondary/tertiary qualifications is an unverified extrapolation.

### B. Potential Risks
1. **Statistical Instability of `Not Ready` Metrics:**
   Because $N=3$, cross-validation precision/recall for `Not Ready` has high variance ($\text{std} = 0.34$). One misclassified sample swings class accuracy by 33.3%.
2. **General Profile vs. Occupation Alignment Disconnect:**
   Because M4 features are profile-level summaries, readiness predictions reflect profile strength rather than job-specific fit. Job-specific fit is captured by M3 (Hybrid Skill Gap), but the two are not explicitly unified in the readiness classifier's loss function.
3. **Overconfidence in Random Forest:**
   While Random Forest achieved higher CV F1 (0.61 vs 0.48) in feasibility testing, it memorizes tree paths with $N=71$ and is prone to hard leaf-node probabilities (0.0 or 1.0) on out-of-distribution inputs.

---

## 6. Actionable Recommendations for Phase 2 Implementation

1. **Implement Explicit OOD Detection (Phase 4):**
   Calculate and store training distribution statistics (min, max, mean, std, percentiles) in model metadata. Compare inference feature vectors against these bounds and emit structured warnings.
2. **Retain Logistic Regression with Transparent Uncertainty (Phase 3 & 5):**
   Keep regularized Logistic Regression as the inference pipeline due to its smooth sigmoid probabilities, well-conditioned gradients, and linear SHAP decomposability. Clearly label probabilities as *model-estimated heuristic probabilities*.
3. **Refrain from Automated Label Fabrication (Phase 2):**
   Preserve the 29 unlabeled records as unannotated. Do NOT convert compatibility scores or M3 coverage into pseudo-labels.
4. **Preserve SHAP Consistency (Phase 6):**
   Ensure SHAP explanations decompose the exact decision margins of the persisted model and provide non-causal factor summaries.

