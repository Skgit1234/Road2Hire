# Road2Hire — 04: AI/ML Model Evaluation, Benchmarks and Scientific Limitations

**Document Version:** 1.0.0  
**Pipeline Engine Version:** 3.0.0  
**Status:** Completed & Validated  
**Module:** Model Evaluation, External Benchmarks & Risk Governance  
**Primary Source Modules:** [`AI/Readiness_Model/`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Readiness_Model), [`AI/Dataset_Preparation/`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Dataset_Preparation), [`Tests/AI/`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Tests/AI)  

---

## 1. Evaluation Methodology & Experimental Objectives

The Road2Hire evaluation framework evaluates the accuracy, robustness, relevance, explainability, and computational latency of every individual AI/ML component as well as the integrated end-to-end pipeline:

1. **Extraction Fidelity:** Assessing precision, recall, and F1-score of resume text parsing, section detection, and skill normalization against human-annotated ground truth.
2. **Matching Effectiveness:** Evaluating whether semantic vector embeddings (`all-MiniLM-L6-v2`) and knowledge graph traversals correctly identify true skill matches and eliminate false positives.
3. **Supervised Classification Stability:** Benchmarking career readiness tier classifiers across cross-validation folds, measuring Macro F1, Balanced Accuracy, and Cohen's Kappa.
4. **Explainability Axiomatic Verification:** Ensuring local feature attributions satisfy the game-theoretic Efficiency Axiom without numerical drift.
5. **Cross-Dataset Benchmark Alignment:** Validating compatibility ranking against external large-scale resume-job matching datasets ($N = 122,560$ pairs).
6. **Scientific Boundary Identification:** Rigorously documenting structural, statistical, and algorithmic limitations to govern ethical deployment.

---

## 2. Evaluation Metrics Definition

The system uses standard information retrieval, statistical learning, and game-theoretic evaluation metrics:

### 2.1 Extraction & Matching Metrics
- **Precision ($P$):** Proportion of extracted/matched skills that are verified correct:
  $$P = \frac{\text{True Positives (TP)}}{\text{TP} + \text{False Positives (FP)}}$$
- **Recall ($R$):** Proportion of verified ground-truth skills successfully extracted:
  $$R = \frac{\text{TP}}{\text{TP} + \text{False Negatives (FN)}}$$
- **F1-Score:** Harmonic mean of precision and recall:
  $$F_1 = 2 \cdot \frac{P \cdot R}{P + R}$$

### 2.2 Supervised Classification Metrics
- **Macro F1:** Unweighted mean of F1 scores across all classes, ensuring minority classes are evaluated equitably:
  $$\text{Macro } F_1 = \frac{1}{C} \sum_{c=1}^{C} F_{1, c}$$
- **Balanced Accuracy:** Average recall obtained across each individual class:
  $$\text{Balanced Acc} = \frac{1}{C} \sum_{c=1}^{C} \frac{\text{TP}_c}{\text{TP}_c + \text{FN}_c}$$
- **Cohen's Kappa ($\kappa$):** Inter-rater agreement metric taking chance agreement into account:
  $$\kappa = \frac{p_o - p_e}{1 - p_e}$$
  where $p_o$ is observed agreement and $p_e$ is hypothetical chance agreement.

### 2.3 Ranking & Retrieval Metrics
- **Top-K Accuracy ($\text{Acc}@K$):** Whether a relevant occupation or skill appears in the top $K$ recommendations.
- **Pearson ($r$) & Spearman ($\rho$) Correlation:** Measuring linear and monotonic rank alignment between model compatibility scores and benchmark scores.

---

## 3. Supervised Career Readiness Evaluation (M4)

The career readiness classifier was evaluated over the annotated candidate cohort ($N = 71$ verified profiles) using **Repeated Stratified 3-Fold Cross-Validation** (3 folds $\times$ 5 repeats = 15 iterations):

### 3.1 Model Benchmark Comparison

| Model | Mean Macro F1 | Std Dev | Balanced Acc | Cohen's Kappa ($\kappa$) | Train Macro F1 | Overfit Delta |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Dummy (Most Frequent)** | 0.2818 | $\pm 0.0039$ | 0.3333 | 0.0000 | 0.2818 | $+0.0000$ |
| **Dummy (Stratified)** | 0.3452 | $\pm 0.0720$ | 0.3531 | 0.0603 | 0.3231 | $-0.0221$ |
| **Logistic Regression (L2)** | **0.4814** | $\pm 0.1443$ | **0.5259** | **0.3289** | 0.8052 | $+0.3238$ |
| **Random Forest (100 Trees)** | **0.6375** | $\pm 0.1415$ | **0.6467** | **0.6775** | 0.9654 | $+0.3279$ |

### 3.2 Model Selection Rationale
While Random Forest achieved higher cross-validation Macro F1 ($0.6375$ vs. $0.4814$), **regularized Logistic Regression was selected as the deployed inference engine**:
1. **Mathematical Explainability:** Logistic Regression allows exact, closed-form Shapley value computation via `shap.LinearExplainer` without sampling approximation.
2. **Monotonicity & Auditing:** Linear coefficients guarantee predictable directional behavior, preventing non-monotonic decision surface artifacts in high-stakes candidate evaluations.
3. **Overfitting Control:** On a pilot dataset ($N=71$), linear models exhibit lower epistemic variance when subjected to covariate shifts.

---

## 4. Keyword Baseline Comparison

To demonstrate the necessity of the hybrid 3-tier approach, a pure keyword matching baseline was evaluated on representative candidate profiles:

$$\text{Baseline Match Score} = \frac{\text{Count of Present Required Skills}}{\text{Total Required Skills}}$$

### 4.1 Sample Comparison Results

| Evaluation Pair | Keyword Baseline Score | Hybrid 3-Tier Match Score | Observed Improvement |
| :--- | :---: | :---: | :--- |
| **EVAL-001 (Data Engineer)** | 0.5000 | **0.7850** | Captured `PostgreSQL` $\to$ `SQL` and `Scikit-Learn` semantic match. |
| **EVAL-002 (Software Dev)** | 0.4200 | **0.7125** | Awarded taxonomic credit for specialized frameworks (`Django` $\to$ `Python`). |
| **EVAL-003 (Backend Eng)** | 0.3333 | **0.6500** | Handled acronyms (`JS` $\to$ `JavaScript`, `K8s` $\to$ `Kubernetes`). |

### 4.2 Baseline Failure Modes Solved by Road2Hire
- **Zero Synonym Handling:** Keyword baseline treated "PostgreSQL" and "Postgres" as distinct missing skills.
- **Taxonomic Blindness:** Failed to credit specialized skills that satisfy general requirements (e.g. "FastAPI" satisfying "web framework").
- **Binary Non-Matches:** Could not distinguish between completely missing knowledge versus partially related capabilities.

---

## 5. External Resume–Job Benchmark Integration

To validate cross-dataset compatibility and ensure models generalize beyond local training samples, the external **Job–Resume Matching Benchmark** was integrated via `AI/Dataset_Preparation/`:

### 5.1 Dataset Profile
- **`cv.csv` (194.0 MB):** 9,544 candidate resumes across 28 balanced target positions.
- **`job.csv` (32.9 MB):** 1,167 job postings across 5 industry sectors.
- **`matches.csv` (19.7 MB):** 122,560 candidate–job matching pairs evaluated across 10 retrieval score dimensions.

### 5.2 Methodological Safeguards & Non-Contamination
> [!CAUTION]
> **Anti-Circularity and Anti-Contamination Rules:**
> 1. **Do NOT Treat Benchmark Scores as Career Readiness:** The external dataset's `final_score` represents top-k pairwise search compatibility; it does **not** reflect human ground-truth career readiness.
> 2. **Prohibition Against Supervised Training:** `matches.csv` scores are strictly prohibited from being used as target labels for training or tuning the M4 readiness model.
> 3. **Permitted Use Cases:**
>    - Sampling unlabeled resumes for independent, rubric-governed manual annotation.
>    - Benchmarking candidate-job semantic retrieval and ranking correlation against external baselines.

---

## 6. Twelve Scientific & Engineering Limitations

In accordance with rigorous academic and engineering standards, twelve structural limitations of the current implementation are documented below:

### 1. Resume Text Extraction & OCR Limitations
- **Scanned Resumes:** The pipeline uses `pypdf`/PyMuPDF text stream parsing. Resumes consisting of rasterized images or flattened vector scans yield empty text streams, triggering `RESUME_PARSE_FAILED`.
- **Multi-Column Layouts:** Two-column formats and infographic resumes can suffer from reading-order interleaving, corrupting section boundary extraction.
- **No Native OCR Engine:** To maintain lightweight dependencies ($< 500\text{ MB}$), Tesseract or cloud OCR engines are not bundled.

### 2. Skill Extraction & Entity Normalization Ambiguities
- **Acronym Polysemy:** Ambiguous short acronyms (e.g. "R" language vs. educational grade "R", "Go" language vs. verb, "CAT" translation tool vs. test) can produce contextual false positives.
- **Emerging Technical Stacks:** Frameworks released after 2023 missing from the ESCO catalog fall back to semantic vector similarity, which may map them to generic umbrella concepts.
- **Experience Recency:** Years of experience are derived from section proximity heuristics rather than full temporal parse graphs.

### 3. ESCO v1.1.1 & O*NET Taxonomy Snapshot Bounds
- **Static Taxonomy:** ESCO v1.1.1 was finalized in 2022. Novel emerging roles (e.g. Prompt Engineer, AI Safety Officer) are missing or mapped to traditional titles (Software Developer).
- **Regional Phrasing:** ESCO uses European institutional phrasing, which occasionally differs from colloquial North American or Asian job postings.
- **Graph Pruning:** To maintain in-memory graphs ($< 100\text{ MB}$), non-essential pedagogical branches were trimmed, limiting multi-hop reasoning.

### 4. Knowledge Graph Occupation Ranking Limitations
- **Centrality vs. Real Labor Demand:** Match scores reflect graph topology overlap rather than real-time hiring demand, local market liquidity, or compensation.
- **Skill Density Bias:** Candidates who exhaustively list every minor tool achieve higher overlap scores than senior candidates who concisely summarize core competencies.
- **Top-K Truncation:** Automatic target occupation selector operates on top graph matches; unconventional career pivots across distant domains may be omitted.

### 5. Heuristic Nature of M3 Skill Gap Scoring
- **Heuristic Weighting:** The $75/25$ weighting formula ($0.75 \times \text{Essential} + 0.25 \times \text{Optional}$) is an expert heuristic, not an empirically fitted regression coefficient.
- **Binary Absence Assumption:** Skills not detected on the resume receive credit $0.0$. The model cannot verify implicit or unstated competencies.
- **Non-Compensatory Dynamics:** In industry, extraordinary mastery of an advanced skill can compensate for an absent basic tool; the linear formula cannot model non-compensatory dynamics.

### 6. M4 Training Dataset Scale & Class Imbalance
- **Small Sample Size ($N = 71$):** While sufficient for a regularized linear baseline with cross-validation, $N = 71$ restricts statistical power and deep interaction modeling.
- **Class Imbalance:**
  - `Developing`: $52$ ($73.2\%$)
  - `Job Ready`: $16$ ($22.5\%$)
  - `Not Ready`: $3$ ($4.2\%$)
  Due to the rarity of `Not Ready` ($n=3$), candidate-grouped cross-validation was not feasible, requiring stratified cross-validation and oversampling.
- **Domain Concentration:** Annotations are concentrated in technical and engineering vocations, limiting empirical validity in non-technical domains.

### 7. Uncalibrated Softmax Probabilities
- **Model Heuristic, Not Confidence:** Softmax probabilities reflect normalized log-odds under training priors. **They do not represent calibrated real-world hiring probabilities** (an estimate of $0.85$ does not mean an $85\%$ likelihood of employment).
- **Covariate Shift Extrapolation:** Linear models output extreme probability values when feature vectors approach or exceed training boundaries.
- **Contract Mandate:** Contracts explicitly designate outputs as uncalibrated model estimates; backend and frontend presentations must never describe them as hiring guarantees.

### 8. Local SHAP Attribution vs. Real-World Causality
- **Attribution $\neq$ Causality:** SHAP values quantify mathematical feature credit relative to training base rates; they do not establish real-world causal mechanisms (e.g. acquiring 1 more year of experience will not causally guarantee a job offer).
- **Multicollinearity Confounding:** Correlated features (e.g. `skills_count` and `project_tech_count`) split Shapley credit, which can obscure the dominant intuitive driver for human reviewers.
- **Class Relativity:** SHAP explanations are calculated relative to predicted class log-odds; cross-class comparisons are mathematically invalid.

### 9. Empirical Out-of-Distribution (OOD) Bounding Bounds
- **Axis-Aligned Univariate Limits:** The OOD detector tracks univariate minimum and maximum bounds independently; it cannot detect joint multivariate anomalies (e.g. 20 years of experience with 0 verified skills).
- **Senior Candidate False Alarms:** Senior candidates with 20+ years of experience trigger OOD flags simply because training samples maxed out at 18.
- **Non-Blocking Operation:** OOD flags are advisory; they do not adjust probabilities or abort execution.

### 10. Static 4-Phase Learning Roadmap Curriculum
- **Rule-Based Allocation:** Phases follow heuristic skill categorizations rather than a formal topological sort over a prerequisite Directed Acyclic Graph (DAG).
- **Uniform Pacing Assumption:** The roadmap assumes uniform learner pacing; it cannot adapt to weekly time availability or previous adjacent skills.
- **Static Catalogs:** Learning resource URLs are stored in static CSV files, risking link deprecation over time.

### 11. External Benchmark Compatibility Limits
- **Scraped / Synthetic Distribution:** The external dataset consists of scraped online postings and synthetic job descriptions that may not match enterprise ATS workflows.
- **Absence of Longitudinal Tracking:** The benchmark measures text matching alignment, not long-term employee retention or on-the-job success.

### 12. Enterprise Production & Scalability Bounds
- **Cold-Start Latency:** Initial singleton pre-warming takes $14\text{s}$ to $18\text{s}$ (loading ESCO graph, embeddings, and classifiers). Serverless cold starts would be unacceptable without pre-warmed containers.
- **Memory Footprint:** In-memory graph structures and transformer models require $\approx 1.5\text{ GB}$ of resident RAM per worker process.
- **Single-Node Execution:** The AI package operates as a local Python process; distributed queues, redis caching, and horizontal autoscaling must be managed by the host application.

---

## 7. Limitations & Engineering Roadmap Matrix

| Dimension | Current Implementation | Major Limitation | Target Resolution | Complexity |
| :--- | :--- | :--- | :--- | :---: |
| **Ingestion** | `pypdf` text parsing | Scanned/image PDFs fail | Tesseract / Document AI OCR fallback | Medium |
| **Extraction** | Trie + MiniLM embeddings | Polysemous acronym ambiguity | Fine-tuned SpanBERT NER | High |
| **Taxonomy** | ESCO v1.1.1 static snapshot | Missing post-2022 tech roles | Dynamic automated web taxonomy expansion| High |
| **Matching** | Heuristic 75/25 linear formula | Uncalibrated, non-compensatory | Learned non-linear ranker (LambdaMART) | High |
| **Readiness** | L2 Logistic Regression ($N=71$) | Small sample, minority class ($n=3$) | Expand to $N \ge 1,000$; Cost-sensitive loss| Medium |
| **Calibration** | Raw Softmax outputs | Probabilities are uncalibrated | Platt Scaling / Isotonic Calibration | Low |
| **Explainability**| SHAP `LinearExplainer` | Local attribution $\neq$ real causality | Counterfactual Explanations (DiCE) | Medium |
| **OOD** | Univariate bounding boxes | Misses joint manifold anomalies | Mahalanobis Distance / Isolation Forest | Medium |
| **Roadmap** | Static 4-phase allocation | No prerequisite DAG or pacing | Dynamic DAG curriculum planner | High |
| **Infrastructure**| In-memory Python singleton | 15s cold start, single-node | Pre-warmed containerized worker pool | Medium |

---

## 8. Ethical AI Governance & Responsible Deployment

1. **Advisory Decision Support:** Road2Hire is an assistive decision-support tool for students, recruiters, and career mentors. **It must never be utilized as an autonomous gatekeeper for employment, screening, or admissions.**
2. **Mandatory Human-in-the-Loop:** Recruiters and academic advisors must review candidate profiles holistically, considering qualitative indicators, portfolio evidence, and personal context that natural language processing cannot capture.
3. **No Commercial Placement Guarantee:** Generating a learning roadmap does not guarantee employment or job offers.

---

## 9. Related Documentation

- For overall architecture and pipeline stages, see [01: Architecture & Pipeline](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Docs/01_AI_ML_Architecture_and_Pipeline.md).
- For research questions, literature review, and taxonomy design, see [02: Research & Taxonomy](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Docs/02_AI_ML_Research_and_Taxonomy.md).
- For algorithmic formulas, matching tiers, and SHAP math, see [03: Algorithms & Methodology](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Docs/03_AI_ML_Algorithms_and_Methodology.md).
- For JSON contracts, schemas, and public API interfaces, see [05: Output & Integration Contract](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Docs/05_AI_ML_Output_and_Integration_Contract.md).
- For database architecture and PostgreSQL mappings, see [06: Database Storage Specification](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Docs/06_AI_ML_Database_Storage_Specification.md).
- For engineering handover and checklists, see [07: Final Handover Document](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Docs/07_AI_ML_Final_Handover.md).

