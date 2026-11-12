# Road2Hire — M4.4 Career Readiness Model Training Feasibility Audit

**Audit Date:** 2026-11-05 UTC  
**Target Milestone:** M4.4 (Supervised Career Readiness Model Development)  
**Annotated Workbook:** [`Datasets/Processed/readiness_annotation.xlsx`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Datasets/Processed/readiness_annotation.xlsx)  
**Source Dataset:** [`Datasets/Processed/readiness_annotation_pilot.jsonl`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Datasets/Processed/readiness_annotation_pilot.jsonl)  
**Unified Dataset:** [`Datasets/Processed/candidate_occupation_dataset.jsonl`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Datasets/Processed/candidate_occupation_dataset.jsonl)  
**Annotation Guidelines:** [`AI/Dataset_Preparation/readiness_annotation_guidelines.md`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Dataset_Preparation/readiness_annotation_guidelines.md)  
**Annotation Schema:** [`AI/Dataset_Preparation/readiness_label_schema.json`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Dataset_Preparation/readiness_label_schema.json)  

---

## 1. Executive Summary

This feasibility audit evaluates whether the completed **M4.3 Career Readiness Annotation Pilot** ($N=100$ records) provides a statistically valid and methodologically sound foundation for supervised machine learning model development in **M4.4**.

### Key Findings & Verdict:
1. **Primary Audit Outcome:** **PROCEED WITH RESTRICTIONS (EXPLORATORY BASELINE ONLY)**.  
   The dataset is viable for early baseline prototyping, pipeline verification, and feature engineering validation. However, it **cannot support production deployment or reliable generalization claims** without collecting additional minority class annotations.
2. **Usable Training Size ($N=71$):** Exactly 71 candidate records carry verified ground-truth labels across the three target classes. Exactly 29 records are unlabeled (`null`) and must be strictly excluded from supervised loss computation.
3. **Severe Class Imbalance:** The labeled population is heavily skewed toward **Developing** ($N=52, 73.2\%$) and **Job Ready** ($N=16, 22.5\%$), with only **3 instances of Not Ready (4.2%)**.
4. **Five-Fold Cross-Validation is Infeasible:** Five-fold Stratified K-Fold / StratifiedGroupKFold is mathematically invalid because the minority class ($N=3$) has fewer instances than folds ($k=5$). At least two folds would have zero test instances of `Not Ready`, making class-level metrics undefined. **The maximum mathematically valid fold count is $k=3$**.
5. **Zero Duplicate Leakage in Labeled Pool:** All 27 secondary duplicate instances from the 15 clusters were withheld from labeling. As a result, the 71 labeled records represent **71 completely unique evidence profiles** (zero identical evidence leakage).
6. **Model Feasibility Verdict:**
   - **Logistic Regression:** **HIGH FEASIBILITY** (primary recommended baseline).
   - **Random Forest:** **MODERATE FEASIBILITY** (usable with shallow depth constraints).
   - **XGBoost:** **LOW TO MODERATE FEASIBILITY** (high overfitting risk; extreme regularization required).

---

## 2. Independent Dataset Verification & Label Statistics

Direct programmatic audit of [`readiness_annotation.xlsx`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Datasets/Processed/readiness_annotation.xlsx) yields the following structural counts:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       DATASET VERIFICATION SUMMARY                          │
├────────────────────────────┬─────────┬──────────┬───────────────────────────┤
│ Metric                     │ Count   │ Share    │ ML Training Function      │
├────────────────────────────┼─────────┼──────────┼───────────────────────────┤
│ Total Workbook Rows        │   100   │  100.0%  │ Total pilot batch         │
│ Labeled Supervised Pool    │    71   │   71.0%  │ Valid for Supervised Loss │
│ Unlabeled Withheld Pool    │    29   │   29.0%  │ Strictly Excluded from y  │
├────────────────────────────┴─────────┴──────────┴───────────────────────────┤
│ CLASS BREAKDOWN (LABELED POOL N=71)                                         │
├────────────────────────────┬─────────┬──────────┬───────────────────────────┤
│ Developing                 │    52   │   73.2%  │ Majority class (junior)   │
│ Job Ready                  │    16   │   22.5%  │ Mid-to-senior competence  │
│ Not Ready                  │     3   │    4.2%  │ Severe minority bottleneck│
├────────────────────────────┴─────────┴──────────┴───────────────────────────┤
│ OCCUPATIONAL REPRESENTATION (LABELED POOL N=71)                             │
├────────────────────────────┬─────────┬──────────┬───────────────────────────┤
│ Software Developer         │    43   │   60.6%  │ 25 Dev, 15 Job, 3 Not     │
│ Cloud DevOps Engineer      │    20   │   28.2%  │ 20 Dev, 0 Job, 0 Not      │
│ ICT System Administrator   │     4   │    5.6%  │ 4 Dev, 0 Job, 0 Not       │
│ Data Scientist             │     2   │    2.8%  │ 1 Dev, 1 Job, 0 Not       │
│ Operations Manager         │     1   │    1.4%  │ 1 Dev, 0 Job, 0 Not       │
│ Project Manager            │     1   │    1.4%  │ 1 Dev, 0 Job, 0 Not       │
└────────────────────────────┴─────────┴──────────┴───────────────────────────┘
```

### Confirmation of Unlabeled Data Exclusion:
All 29 unlabeled records in Column M (`readiness_label`) contain explicit `None` / `null` values and have their reviewer status set to `Flagged_Insufficient_Evidence`.
- **Mandate:** Supervised learning requires ground-truth target pairs $(x_i, y_i)$. These 29 records must be programmatically filtered prior to any feature extraction or matrix construction ($X, y$).
- **No Pseudo-Labeling:** Under no circumstances should these 29 records be assigned pseudo-labels or filled with synthetic labels for model training.

---

## 3. Deduplication Audit & Independent Evidence Groups

An independent hash analysis of the evidence tuples `(skills, experience_summary, projects_summary, education_summary)` across the 100 rows reveals:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      EVIDENCE CLUSTERING & DEDUPLICATION                    │
├──────────────────────────────────────────────────────┬──────────────────────┤
│ Total Pilot Records                                  │ 100                  │
│ Distinct Evidence Clusters in Total Batch            │ 73                   │
│ Duplicate Evidence Clusters                          │ 15 clusters (42 rows)│
│ Secondary Duplicate Instances Withheld               │ 27 records           │
│ Primary Records Withheld (Unstated / Blank Evidence) │ 2 records (mr_40, 112│
├──────────────────────────────────────────────────────┼──────────────────────┤
│ Independent Evidence Profiles in Labeled Pool ($N=71$)│ 71 unique profiles   │
│ Duplicate Evidence Profiles in Labeled Pool          │ 0 (Zero duplication) │
└──────────────────────────────────────────────────────┴──────────────────────┘
```

### Statistical Meaning for Machine Learning:
Because all 27 duplicate instances were withheld during the M4.3 annotation phase:
1. **Zero Data Leakage from Duplication:** There is zero risk of an identical candidate resume appearing in both the training fold and the test fold.
2. **True Effective Sample Size:** The effective independent sample size of the labeled dataset is exactly **$N_{\text{eff}} = 71$**.

---

## 4. Class Distribution & Minority Class Bottleneck

The three-class distribution exhibits severe imbalance:

$$N_{\text{Developing}} = 52 \quad (73.2\%), \quad N_{\text{Job Ready}} = 16 \quad (22.5\%), \quad N_{\text{Not Ready}} = 3 \quad (4.2\%)$$

### Critical Bottleneck Analysis:
1. **The `Not Ready` Bottleneck ($N=3$):**  
   Only three candidates (`mr_56`, `mr_72`, `mr_168`) are annotated as `Not Ready`.
   - `mr_56`: Network Security Engineer (Checkpoint/Cisco) with zero programming background.
   - `mr_72`: RPA Business Analyst (MS Visio, Bizagi) with no software implementation.
   - `mr_168`: Network Security Engineer (Firewalls) with embedded IoT hardware cooling demos.
2. **Occupational Confounding of `Not Ready`:**  
   All three `Not Ready` candidates are targeted to `software developer`. There are **zero** `Not Ready` examples for Cloud DevOps, Data Science, ICT Administration, Operations Management, or Project Management.
3. **Occupational Monoculture in Secondary Roles:**  
   - For `cloud DevOps engineer` ($N=20$), 100% of labeled candidates are `Developing`.
   - For `ICT system administrator` ($N=4$), 100% are `Developing`.
   - For `operations manager` ($N=1$) and `project manager` ($N=1$), 100% are `Developing`.

> [!WARNING]
> **Confounding Risk:** If target occupation is provided as a feature, models will learn a degenerate shortcut rule:  
> `if occupation == 'cloud DevOps engineer' then Developing (100% train accuracy)`  
> This shortcut prevents the model from learning actual qualification signals.

---

## 5. Feasibility of K-Fold Stratification

### 5.1 Mathematical Proof: 5-Fold Stratification is Invalid

In $k$-fold cross-validation with stratification (`StratifiedKFold` or `StratifiedGroupKFold`), the dataset is partitioned into $k$ disjoint subsets such that each fold contains an approximately equal proportion of each class label.

Let $N_c$ denote the number of instances in class $c$. The expected number of test instances for class $c$ in each fold is:

$$\mathbb{E}[N_{c,\text{test}}] = \frac{N_c}{k}$$

For the minority class $c = \text{Not Ready}$:

$$N_{\text{Not Ready}} = 3, \quad k = 5 \implies \frac{3}{5} = 0.6$$

Because instance counts are discrete integers:
- At most 3 folds can contain $\lfloor 3/5 \rfloor + 1 = 1$ instance of `Not Ready`.
- At least $5 - 3 = \mathbf{2 \text{ folds}}$ **must contain exactly 0 instances of `Not Ready`**.

### Empirical Verification with Scikit-Learn:
Executing `StratifiedKFold(n_splits=5)` or `StratifiedGroupKFold(n_splits=5)` on the labeled pool generates the following system warning:
```text
UserWarning: The least populated class in y has only 3 members, which is less than n_splits=5.
Fold 0: test size=15, classes in test: Developing (11), Job Ready (3), Not Ready (1)
Fold 1: test size=14, classes in test: Developing (11), Job Ready (3)  <-- ZERO Not Ready
Fold 2: test size=14, classes in test: Developing (10), Job Ready (4)  <-- ZERO Not Ready
Fold 3: test size=14, classes in test: Developing (10), Job Ready (3), Not Ready (1)
Fold 4: test size=14, classes in test: Developing (10), Job Ready (3), Not Ready (1)
```

### Consequences of 5-Fold Stratification:
1. **Undefined Class Metrics:** In Folds 1 and 2, test precision, recall, and F1-score for `Not Ready` have zero denominator ($\frac{0}{0}$), forcing artificial zero-division imputation (`zero_division=0`).
2. **Extreme Metric Variance:** In Folds 0, 3, and 4, there is exactly one test instance. A single model prediction swings class recall between $0\%$ and $100\%$, producing standard deviations exceeding $\pm 45\%$.
3. **Verdict:** **Five-fold cross-validation must NOT be used.**

---

### 5.2 Maximum Feasible Fold Count: 3-Fold Stratified K-Fold

Setting $k=3$ is the **exact mathematical limit** for stratification on this dataset:

$$\mathbb{E}[N_{\text{Not Ready},\text{test}}] = \frac{3}{3} = 1.0$$

Testing `StratifiedKFold(n_splits=3)` yields:
- **Fold 0:** 18 Developing, 5 Job Ready, 1 Not Ready (Total: 24)
- **Fold 1:** 17 Developing, 6 Job Ready, 1 Not Ready (Total: 24)
- **Fold 2:** 17 Developing, 5 Job Ready, 1 Not Ready (Total: 23)

Zero warnings are produced, and every fold contains all three target classes in both training and test partitions.

---

## 6. Comprehensive Data Leakage Audit

To ensure scientific validity, six potential vectors of data leakage were inspected:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DATA LEAKAGE RISK AUDIT                            │
├─────────────────────┬──────────────┬────────────────────────────────────────┤
│ Leakage Vector      │ Risk Level   │ Required Mitigation Protocol           │
├─────────────────────┼──────────────┼────────────────────────────────────────┤
│ 1. Identifiers      │ CRITICAL     │ Drop candidate_id, annotation_id, and  │
│    (IDs, Pair Keys) │              │ pair_id from feature matrix X.         │
├─────────────────────┼──────────────┼────────────────────────────────────────┤
│ 2. Institution / PII│ HIGH         │ Strip company names (Honeywell, AT&T)  │
│    Names in Text    │              │ and university names from raw text.    │
├─────────────────────┼──────────────┼────────────────────────────────────────┤
│ 3. Duplicate Records│ CRITICAL     │ Keep 27 secondary duplicate records    │
│    in Train vs Test │              │ strictly excluded from training/test.  │
├─────────────────────┼──────────────┼────────────────────────────────────────┤
│ 4. Occupation Target│ HIGH         │ Do not use target_occupation as a raw  │
│    Confounding      │              │ one-hot feature (causes 100% shortcut).│
├─────────────────────┼──────────────┼────────────────────────────────────────┤
│ 5. Rubric Dimension │ FATAL        │ Columns 9–12 (proficiency, relevance)  │
│    Ratings Leakage  │              │ are human sub-labels. Exclude from X.  │
├─────────────────────┼──────────────┼────────────────────────────────────────┤
│ 6. M3 Skill Coverage│ HIGH         │ Do not use M3 coverage score as proxy  │
│    Circularity      │              │ or single feature for readiness.       │
└─────────────────────┴──────────────┴────────────────────────────────────────┘
```

### Detailed Analysis of Vector 5 (Rubric Dimension Leakage):
Columns 9–12 (`essential_skill_proficiency`, `work_experience_relevance`, `practical_application_evidence`, `education_relevance`) were generated during manual annotation.  
If an ML engineer includes these columns as features in $X$:
- The model is not evaluating candidate readiness from resume signals; it is merely learning the hardcoded decision matrix of the human annotator.
- In production, these four columns will not exist when an unseen candidate uploads a raw PDF resume.
- **Protocol Mandate:** Columns 9–12, Column 15 (`key_evidence_summary`), and Column 18 (`annotation_notes`) must be strictly stripped from $X$.

---

## 7. Feature Representation & Engineering Recommendations

### 7.1 Empirical Evidence: M3 Skill Coverage Does Not Equal Readiness

To demonstrate why M3 skill coverage cannot serve as the sole feature or proxy, empirical mean coverage scores were computed across the 71 labeled candidates:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 M3 SKILL COVERAGE VS HUMAN READINESS LABEL                  │
├─────────────────┬──────────┬──────────────────────┬─────────────────────────┤
│ Readiness Class │ Sample N │ Mean Overall Coverage│ Mean Essential Coverage │
├─────────────────┼──────────┼──────────────────────┼─────────────────────────┤
│ Developing      │    52    │       0.0096         │         0.0083          │
│ Job Ready       │    16    │       0.0106         │         0.0053          │
│ Not Ready       │     3    │       0.0010         │         0.0000          │
└─────────────────┴──────────┴──────────────────────┴─────────────────────────┘
```

> [!IMPORTANT]
> **Non-Monotonic Anomaly:**  
> Candidates annotated as `Developing` exhibit a **higher mean essential skill coverage** ($0.0083$) than candidates annotated as `Job Ready` ($0.0053$).  
> - **Explanation:** A mid-level Java engineer (`Job Ready`) lists 6–8 concise technologies (Java, Spring, Hibernate, Oracle) matching only 1 or 2 canonical ESCO strings directly, but possesses enterprise production systems and an ME degree. In contrast, junior candidates (`Developing`) frequently list broad academic keyword strings matching more ESCO leaf nodes on paper.  
> - **Conclusion:** A model relying solely on lexical skill matching will fail to separate Job Ready candidates from Developing trainees.

### 7.2 Recommended Feature Set ($X$)

Features must represent multi-dimensional occupational readiness derived directly from parsed candidate profiles:

1. **Academic Foundation Features:**
   - `degree_level_ordinal`: Encoded credential tier (0 = None/High School, 1 = Bachelor, 2 = Master/PGP, 3 = Doctorate).
   - `degree_alignment_stem`: Binary flag indicating computer science, software engineering, mathematics, or electronics engineering degree.
2. **Work Experience & Tenure Features:**
   - `experience_positions_count`: Total number of verified employment positions.
   - `estimated_tenure_years`: Numeric duration extracted from employment dates (imputed with 0.5 for unspecified junior roles, 2.0 for senior titles).
   - `has_senior_lead_title`: Binary flag indicating keywords `Senior`, `Lead`, `Architect`, `Manager`.
3. **Practical Application & Project Depth Features:**
   - `project_count`: Total documented technical projects.
   - `project_description_word_count`: Total length of project technical descriptions (proxy for implementation depth).
   - `project_tech_stack_diversity`: Number of distinct technologies explicitly mentioned within project blocks.
   - `has_production_keywords`: Binary indicator for terms `deployment`, `production`, `enterprise`, `CI/CD`, `pipeline`, `microservices`.
4. **Independent Skill Alignment Features:**
   - `normalized_skills_count`: Total unique normalized skills extracted.
   - `semantic_skill_similarity_max`: Maximum cosine embedding similarity between candidate skills and target ESCO occupation essential skills.
   - `graph_provenance_ratio`: Ratio of candidate skills directly grounded in canonical taxonomy graph nodes.

---

## 8. Candidate Model Feasibility Assessment

Three models specified in the evaluation protocol were assessed for statistical viability on $N=71$ tabular samples:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      CANDIDATE MODEL FEASIBILITY MATRIX                     │
├────────────────────┬─────────────┬──────────────┬───────────────────────────┤
│ Model Architecture │ Feasibility │ Overfit Risk │ Architectural Suitability │
├────────────────────┼─────────────┼──────────────┼───────────────────────────┤
│ 1. Logistic        │ HIGH        │ LOW          │ RECOMMENDED PRIMARY. Low  │
│    Regression      │             │              │ sample complexity; stable │
│    (ElasticNet/L2) │             │              │ with balanced weights.    │
├────────────────────┼─────────────┼──────────────┼───────────────────────────┤
│ 2. Random Forest   │ MODERATE    │ MEDIUM       │ VIABLE BENCHMARK. Non-    │
│    Classifier      │             │              │ linear interactions; needs│
│    (Balanced Sub.) │             │              │ shallow depth (max_depth≤3│
├────────────────────┼─────────────┼──────────────┼───────────────────────────┤
│ 3. XGBoost         │ LOW-MODERATE│ HIGH         │ EXPERIMENTAL ONLY. High   │
│    Classifier      │             │              │ risk of leaf memorization;│
│    (Extreme Reg.)  │             │              │ requires heavy shrinkage. │
└────────────────────┴─────────────┴──────────────┴───────────────────────────┘
```

### Detailed Assessment by Architecture:

#### 1. Multinomial Logistic Regression (`L2 / ElasticNet` Regularized)
- **Mathematical Form:**
  $$P(y = c \mid \mathbf{x}) = \frac{e^{\mathbf{w}_c^T \mathbf{x} + b_c}}{\sum_{j=1}^K e^{\mathbf{w}_j^T \mathbf{x} + b_j}}$$
- **Strengths for $N=71$:**
  - Sample complexity scales linearly $\mathcal{O}(d)$ with feature dimension ($d \le 10$).
  - Convex optimization guarantees global convergence without local minimum instability.
  - Highly interpretable weight vectors $\mathbf{w}_c$ allow direct auditing of which features drive `Job Ready` vs `Developing`.
  - Native support for balanced class weighting ($w_c = \frac{N}{K \cdot N_c}$), multiplying minority loss by $7.88\times$ for `Not Ready`.
- **Hyperparameter Recommendation:** `solver='lbfgs'`, `multi_class='multinomial'`, `C=0.5` (strong regularization), `class_weight='balanced'`.

#### 2. Random Forest Classifier
- **Strengths for $N=71$:**
  - Captures non-linear thresholds (e.g. `degree_level >= 2` AND `project_tech_stack_diversity >= 3`).
  - Invariant to monotonic feature scaling; handles mixed discrete and continuous features cleanly.
- **Weaknesses & Bottlenecks:**
  - Bootstrap sampling draws $N=71$ with replacement, leaving $\approx 36.8\%$ out-of-bag per tree. With only 3 `Not Ready` instances, each tree will observe on average only $3 \times (1 - e^{-1}) \approx 1.9$ instances of `Not Ready`, risking individual trees that fail to split on the minority class.
- **Hyperparameter Recommendation:** `n_estimators=50`, `max_depth=3`, `min_samples_split=4`, `min_samples_leaf=2`, `class_weight='balanced_subsample'`.

#### 3. XGBoost Classifier (Gradient Boosted Trees)
- **Strengths:** High capacity for complex tabular interactions.
- **Weaknesses & Overfitting Hazards:**
  - Gradient boosting sequentially minimizes pseudo-residuals. The 3 `Not Ready` instances will generate large loss gradients in early boosting rounds, causing later trees to construct isolated leaves that memorize individual candidate noise.
  - On tabular datasets with $N < 100$, gradient boosting typically underperforms regularized linear models and shallow forests due to variance explosion.
- **Hyperparameter Recommendation:** `max_depth=2`, `learning_rate=0.03`, `n_estimators=35`, `subsample=0.7`, `colsample_bytree=0.7`, `reg_lambda=3.0`, `reg_alpha=1.0`.

---

## 9. Recommended Evaluation Strategy

### 9.1 Cross-Validation Configuration
- **Protocol:** **Repeated Stratified 3-Fold Cross-Validation** (5 repeats $\times$ 3 folds = 15 evaluation iterations).
- **Justification:** Single-split evaluation (e.g. 80/20 train/test) leaves only 14 test instances with at most 0 or 1 `Not Ready` sample. Repeating a 3-fold stratified split with distinct random seeds stabilizes metric estimates and produces meaningful confidence intervals ($\pm \sigma$).

### 9.2 Metric Selection
Because accuracy is completely misleading under a $73.2\%$ majority class (a dummy classifier predicting `Developing` achieves $73.2\%$ accuracy while having $0\%$ recall on Job Ready and Not Ready):
1. **Primary Metric:** **Macro-Averaged F1-Score**
   $$\text{Macro } F_1 = \frac{1}{3} \left( F_{1,\text{Developing}} + F_{1,\text{Job Ready}} + F_{1,\text{Not Ready}} \right)$$
   Equal weighting penalizes models that ignore minority classes.
2. **Secondary Metric:** **Balanced Accuracy (Macro Recall)**
   $$\text{Balanced Acc} = \frac{1}{3} \left( \text{Recall}_{\text{Developing}} + \text{Recall}_{\text{Job Ready}} + \text{Recall}_{\text{Not Ready}} \right)$$
3. **Diagnostic Metric:** **Cohen's Kappa ($\kappa$)**  
   Measures inter-rater agreement between model predictions and human ground truth corrected for chance ($\kappa > 0.40$ indicates moderate agreement).
4. **Confusion Matrix Inspection:** Obligatory for every fold to verify that predictions are distributed across all three classes.

---

## 10. Scientific Scope: Exploratory vs Generalization Claims

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SCIENTIFIC READINESS ASSESSMENT                      │
├───────────────────────────────────┬────────────┬────────────────────────────┤
│ Scientific Question               │ Supported? │ Detailed Evidence / Reason │
├───────────────────────────────────┼────────────┼────────────────────────────┤
│ 1. Exploratory Model Training     │ YES        │ Code pipelines, baseline   │
│    & Pipeline Prototyping         │            │ benchmarks, and feature    │
│                                   │            │ separability can be tested.│
├───────────────────────────────────┼────────────┼────────────────────────────┤
│ 2. Meaningful Cross-Validation    │ LIMITED    │ Supported only with k=3    │
│    Across All Three Classes       │ (k = 3)    │ Repeated Stratified CV;    │
│                                   │            │ high variance on Not Ready.│
├───────────────────────────────────┼────────────┼────────────────────────────┤
│ 3. Statistically Reliable         │ NO         │ N=71 is too small; 3 Not   │
│    Generalization Claims          │            │ Ready samples cannot bound │
│                                   │            │ true generalization error. │
├───────────────────────────────────┼────────────┼────────────────────────────┤
│ 4. Deployment Readiness           │ NO         │ Model would overfit to     │
│    for Real Candidates            │            │ scrape distribution.       │
└───────────────────────────────────┴────────────┴────────────────────────────┘
```

---

## 11. Final Actionable Recommendation & Roadmap

### Final Verdict:
**PROCEED WITH RESTRICTIONS (PHASED EXECUTION)**

### Phased Action Plan:

#### Phase 1: Exploratory Baseline Model (Immediate M4.4 Kickoff)
1. Implement the feature extraction pipeline on the 71 labeled records, extracting the 9 independent features defined in Section 7.2.
2. Implement **Repeated Stratified 3-Fold Cross-Validation** ($k=3$, 5 repeats).
3. Train and compare:
   - Dummy Stratified Baseline
   - Regularized Multinomial Logistic Regression (`class_weight='balanced'`)
   - Constrained Random Forest (`max_depth=3`)
   - Regularized XGBoost (`max_depth=2`)
4. Benchmark models using **Macro F1** and **Cohen's Kappa ($\kappa$)**.
5. Establish baseline performance and log all metric variances without making generalized claims.

#### Phase 2: Targeted Human Annotation Batch 2 (Prerequisite for Production)
To transition from an exploratory prototype to a defensible production model:
1. Sample an additional **150 candidate resumes** from `Datasets/master_resumes.jsonl`.
2. Intentionally oversample candidates likely to represent `Not Ready` (e.g. candidates with non-technical degrees applying for software engineering, resumes without programming languages) and diverse occupations (`data scientist`, `cloud DevOps engineer`).
3. Annotate using the existing workbook and guidelines to reach:
   - Target $N_{\text{total}} \ge 200$ labeled records.
   - Target $N_{\text{Not Ready}} \ge 25$ records.
   - Target $N_{\text{Job Ready}} \ge 45$ records.
4. Once Batch 2 is complete, 5-fold StratifiedGroupKFold will become mathematically valid, enabling rigorous multi-class generalization.

