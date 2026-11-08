# Road2Hire AI/ML Engine: Scientific Limitations & Future Work

**Document Version:** 1.0.0  
**Status:** Completed & Validated  
**Module:** AI/ML Core (M1–M4 + End-to-End Pipeline)  
**Target Audience:** AI/ML Researchers, Data Scientists, Backend Engineers, Product Leadership  

---

## Executive Summary

The Road2Hire AI/ML module delivers an automated, explainable talent intelligence pipeline that extracts candidate competencies from unstructured PDF resumes, maps them to canonical ESCO v1.1.1 and O*NET taxonomies, identifies skill gaps, predicts career readiness tiers using regularized multinomial logistic regression, generates local SHAP feature attributions, and constructs personalized 4-phase learning roadmaps.

While the system is robust, validated across 369 automated tests, and adheres to strict JSON Schema contracts, scientific integrity requires documenting the structural, empirical, and architectural limitations of the current implementation. This document outlines twelve key limitations and establishes a roadmap for future research and engineering enhancements.

---

## 1. Resume Text Extraction & OCR Limitations

### Current Implementation
- Resume text extraction is executed via `pypdf` and fallback text stream parsers in `AI/Resume_Extraction/extractor.py`.
- The pipeline assumes digitally authored, text-layer PDFs (e.g., generated via Microsoft Word, Google Docs, LaTeX, or ATS exporters).

### Known Limitations
- **Scanned Resumes & Image Layers:** Resumes consisting of rasterized images, scanned paper documents, or flattened vector layers without embedded text streams yield empty or truncated text, failing early at pipeline ingestion.
- **Multi-Column & Non-Standard Layouts:** Two-column formats, sidebars, graphic callout boxes, and infographic resumes may experience reading-order corruption (interleaving text across columns), degrading section extraction (`experience`, `education`, `skills`).
- **Absence of Optical Character Recognition (OCR):** The current pipeline does not bundle a heavy OCR engine (e.g., Tesseract, AWS Textract, or PaddleOCR) to minimize installation footprint and dependency bloat.

### Recommended Future Work
- Integrate a conditional OCR fallback pipeline (e.g., using `pytesseract` or cloud document AI endpoints) triggered when extracted character count falls below a minimum threshold ($< 100$ characters).
- Adopt layout-aware document visual models (e.g., LayoutLMv3 or Donut) to preserve structural semantics and multi-column visual hierarchy.

---

## 2. Skill Extraction & Entity Normalization Boundaries

### Current Implementation
- Hybrid skill extraction combining rule-based phrase matching, dictionary tokenization, and semantic embedding similarity (`all-MiniLM-L6-v2`) against curated ESCO and O*NET skill catalogs in `AI/Skill_Extraction/skill_extractor.py`.

### Known Limitations
- **Acronym & Boundary Ambiguities:** Polysemous acronyms (e.g., "R" for the R programming language vs. educational grade "R", "Go" language vs. English verb, "CAT" for computer-aided translation vs. exam) can trigger contextual false positives.
- **Emerging Technical Stacks:** Newly emergent frameworks, proprietary enterprise tools, or domain-specific libraries (e.g., specialized LLM orchestration frameworks released post-2023) not present in the reference dictionary require fallback to semantic similarity, which may map them to generic umbrella concepts.
- **Experience Attribution Heuristics:** Inferred skill recency and years of experience rely on proximity heuristics within work history sections, which can be misattributed if candidate formatting deviates from standard date patterns.

### Recommended Future Work
- Fine-tune a domain-adapted token classification model (e.g., SpanBERT or RoBERTa for NER) trained on resume-specific skill boundaries.
- Introduce context-aware disambiguation rules that leverage surrounding tokens (e.g., verifying that "Go" co-occurs with "backend", "concurrency", or "Docker").

---

## 3. ESCO v1.1.1 & O*NET Taxonomy Coverage & Recency

### Current Implementation
- Knowledge graph grounded in European Skills, Competences, Qualifications and Occupations (ESCO v1.1.1) and mapped crosswalks to US O*NET in `AI/Knowledge_Graph/`.

### Known Limitations
- **Static Taxonomy Snapshot:** ESCO v1.1.1 was finalized in 2022. While foundational occupation structures remain stable, cutting-edge roles (e.g., Prompt Engineer, MLOps Specialist, AI Governance Officer) are either absent or represented through proximate traditional titles (e.g., "Software Developer", "Data Scientist").
- **Regional Terminology Discrepancies:** ESCO predominantly utilizes European institutional phrasing, which occasionally diverges from colloquial North American or Asian job titles, requiring ongoing maintenance of synonym mappings.
- **Graph Pruning:** To maintain lightweight in-memory graphs ($< 50\text{ MB}$), transitive skill-to-skill relations and non-essential pedagogical branches were trimmed, limiting multi-hop inferencing depth.

### Recommended Future Work
- Implement automated dynamic taxonomy expansion by scraping verified job boards and clustering novel skill terms around existing ESCO nodes.
- Upgrade to ESCO v1.2.0 when released and incorporate bilingual cross-lingual embeddings for international candidate cohorts.

---

## 4. Knowledge Graph Occupation Recommendation Ranking

### Current Implementation
- Target occupation scoring in `AI/Pipeline/target_occupation_selector.py` evaluates candidate skills against occupation skill requirement profiles using Jaccard overlap, weighted essential/optional skill coverage, and semantic vector similarity.

### Known Limitations
- **Static Graph Centrality vs. Dynamic Market Demand:** Recommendations reflect theoretical overlap in the ESCO graph rather than real-time labor market liquidity, regional hiring demand, or employer salary benchmarks.
- **Sensitivity to Resume Skill Density:** Candidates who exhaustively enumerate minor technologies can achieve artificially inflated match scores over highly qualified candidates who concisely list core competencies.
- **Top-K Truncation:** Automatic target occupation selector operates on a pre-filtered candidate pool of top graph matches; edge-case career transition paths across disparate domains may be excluded from the top-5 ranking.

### Recommended Future Work
- Augment graph matching scores with real-time labor market telemetry (e.g., regional job opening density, wage percentiles).
- Implement TF-IDF or BM25-style inverse document frequency penalties for ubiquitous, low-discriminative skills (e.g., "Communication", "Microsoft Office").

---

## 5. Heuristic Nature of M3 Skill Gap Scoring

### Current Implementation
- M3 Hybrid Skill Gap Detection evaluates compatibility using a deterministic scoring formula:
  $$\text{Match Score} = 0.75 \times \text{Essential Coverage} + 0.25 \times \text{Optional Coverage}$$
  Skills are partitioned into three distinct tiers: Missing, Matched, and Partially Matched.

### Known Limitations
- **Heuristic Weighting:** The $75/25$ weighting ratio between essential and optional skills is an expert-defined heuristic rather than an empirically fitted regression coefficient tied to hiring outcomes.
- **Binary Absence Assumption:** Skills not explicitly identified in the candidate profile are categorized as "missing" (score $= 0$). The model does not infer latent or implicit competence that could be derived from related skills (e.g., assuming proficiency in SQL might imply familiarity with relational database concepts).
- **Non-Compensatory Gaps:** In actual hiring scenarios, exceptional mastery of an advanced optional skill may compensate for an absent basic skill; the linear heuristic formula cannot model non-linear compensatory dynamics.

### Recommended Future Work
- Transition from linear weighting to a learned non-linear ranking model (e.g., LambdaMART or pairwise neural ranker) trained on recruiter shortlisting decisions.
- Incorporate skill-to-skill graph distance to award partial credit for adjacent competencies (e.g., awarding $60\%$ credit for PostgreSQL when MySQL is required).

---

## 6. M4 Readiness Dataset Scale & Class Imbalance

### Current Implementation
- Career readiness tier prediction is governed by an L2-regularized multinomial logistic regression classifier trained on an expert-annotated dataset of $N = 71$ candidate profiles across 5 engineered features.

### Known Limitations
- **Small Sample Size ($N = 71$):** While $N = 71$ was sufficient to train a baseline model with low variance through cross-validation, the sample size restricts statistical power and limits the model's ability to capture subtle edge-case interactions.
- **Pronounced Class Imbalance:** The training distribution contains:
  - `Developing`: $52$ candidates ($73.2\%$)
  - `Job Ready`: $16$ candidates ($22.5\%$)
  - `Not Ready`: $3$ candidates ($4.2\%$)
  Due to the extreme rarity of the `Not Ready` class ($n=3$), candidate-grouped or stratified 5-fold cross-validation could not allocate sufficient test instances per fold, requiring Leave-One-Out (LOOCV) and synthetic oversampling for stability.
- **Domain Specialization Bias:** The training dataset is primarily concentrated in technical and engineering occupations (Data Science, Software Engineering, Cloud Architecture), limiting empirical validity when applied to non-technical vocations (e.g., Healthcare, Legal, Creative Arts).

### Recommended Future Work
- Expand the annotated training cohort to $N \ge 1,000$ profiles across diverse occupational clusters.
- Apply Cost-Sensitive Learning or focal loss formulations to counteract minority class penalty imbalances.

---

## 7. Uncalibrated Readiness Softmax Probabilities

### Current Implementation
- The model outputs class probability estimates derived from the standard Softmax transformation of linear log-odds:
  $$P(Y = c \mid \mathbf{x}) = \frac{\exp(\mathbf{w}_c^T \mathbf{x} + b_c)}{\sum_{k} \exp(\mathbf{w}_k^T \mathbf{x} + b_k)}$$

### Known Limitations
- **Lack of Empirical Calibration:** Softmax probabilities reflect normalized model confidence given the training distribution; they **do not represent calibrated real-world probabilities** (e.g., an estimated score of $0.85$ does not imply that $85\%$ of candidates with this score secure employment).
- **Overconfidence Under Covariate Shift:** Linear Softmax models are susceptible to extreme probability outputs when evaluated near decision boundaries, especially when feature values approach the edge of the training range.
- **Scientific Contract Enforcement:** The pipeline contract explicitly labels these outputs as uncalibrated model estimates (`model_estimate`), and backend/frontend presentations must never display them as calibrated hiring probabilities or guarantees.

### Recommended Future Work
- Implement post-hoc probability calibration techniques, such as Platt Scaling or Isotonic Regression, evaluated via Brier Score and Expected Calibration Error (ECE) on a held-out test cohort.
- Provide Bayesian credible intervals alongside point estimates to communicate epistemic uncertainty.

---

## 8. SHAP Local Attribution vs. Real-World Causal Explanations

### Current Implementation
- Explainability is provided via `shap.LinearExplainer`, computing local Shapley values ($\phi_i$) that decompose the model's predicted log-odds into additive contributions per feature relative to the expected dataset value ($\phi_0$).

### Known Limitations
- **Attribution $\neq$ Causality:** SHAP values explain *how the model reached its mathematical prediction* relative to its training distribution; they **do not establish real-world causal mechanisms** (e.g., a high positive attribution for `years_experience` does not prove that acquiring one more year will causally trigger a hiring offer).
- **Feature Correlation Confounding:** When input features exhibit multicollinearity (e.g., `skill_overlap_ratio` and `experience_years`), Shapley attribution divides credit across correlated dimensions, which can obscure the dominant intuitive driver for human reviewers.
- **Target-Specific Relativity:** SHAP explanations are computed for the predicted class log-odds; comparing attributions across different target occupations directly is mathematically invalid.

### Recommended Future Work
- Pair SHAP attributions with Counterfactual Explanations (e.g., via the DiCE framework), answering: *"What minimal changes to skills or experience would transition this candidate from Developing to Job Ready?"*
- Provide human-readable contrastive explanations suitable for non-technical candidates and career advisors.

---

## 9. Empirical Out-of-Distribution (OOD) Detection Boundaries

### Current Implementation
- The OOD detector (`OODDetector`) monitors feature vectors against empirical bounding boxes (univariate minimum and maximum ranges) established on the $N = 71$ training cohort.
- If any feature exceeds these bounds, an `is_ood: true` flag and descriptive warning messages are emitted, but inference continues gracefully.

### Known Limitations
- **Axis-Aligned Bounding Box Simplification:** The current detector evaluates univariate thresholds independently; it cannot detect multivariate anomalies that fall within univariate bounds but violate joint feature correlation structures (e.g., a candidate with $20$ years of experience but $0.0$ skill match).
- **False Alarm Sensitivity:** Exceptional, highly qualified senior candidates (e.g., 25 years of experience when training max was 18) trigger OOD warnings despite being valid candidates.
- **Non-Blocking Operation:** OOD detection is informational only; it does not abort inference or adjust probability outputs.

### Recommended Future Work
- Implement multivariate density estimation or distance-based OOD detection, such as Mahalanobis Distance thresholding, Isolation Forests, or Deep One-Class SVMs.
- Provide tiered OOD severity levels (`informational`, `warning`, `critical_drift`) to inform downstream business logic.

---

## 10. Static 4-Phase Learning Roadmap Curriculum Limitations

### Current Implementation
- The roadmap generator (`AI/Pipeline/roadmap_generator.py`) maps missing skills identified in M3 to pre-compiled learning resources in `Datasets/Learning_Resources/Processed/Learning_Resources.csv`.
- Missing skills are organized into four sequential pedagogical phases:
  - Phase 1: Foundational Core Skills
  - Phase 2: Domain Competencies & Frameworks
  - Phase 3: Advanced Tools & Cloud Infrastructure
  - Phase 4: Capstone Projects & Practical Portfolio

### Known Limitations
- **Static Curriculum Structure:** Phase allocation relies on heuristic skill categorizations rather than a dynamic topological sort over formal skill dependency graphs (DAGs).
- **Absence of Adaptive Pacing:** The roadmap assumes uniform learner velocity; it does not adjust milestone durations based on candidate background, weekly time commitments, or preexisting adjacent skills.
- **Resource Stagnation:** Course URLs, platform providers, and instructional media are pulled from static CSV catalogs, risking link rot or deprecated course content over time.

### Recommended Future Work
- Transition to a directed acyclic graph (DAG) curriculum planner that models strict prerequisite dependencies (e.g., "Python Basics" $\to$ "Pandas Data Analysis" $\to$ "Scikit-Learn Machine Learning").
- Connect to live learning platform APIs (e.g., Coursera, edX, LinkedIn Learning) for real-time course availability, ratings, and pricing.

---

## 11. External Dataset Compatibility Benchmark Limitations

### Current Implementation
- External dataset validation utilizes the Job-Resume Matching dataset ($N = 100$ candidate pairs) in `Datasets/Processed/External_Job_Resume_Matching/` to evaluate cross-dataset extraction fidelity and compatibility ranking.

### Known Limitations
- **Synthetic/Scraped Distribution:** External datasets consist of publicly scraped resumes and synthetic job descriptions that may not mirror the proprietary applicant tracking distribution of enterprise partners.
- **Absence of Longitudinal Ground Truth:** The benchmark validates extraction alignment and semantic similarity; it does not possess longitudinal employment outcomes (whether candidates were interviewed, hired, or succeeded on the job).
- **Static Match Pairs:** Benchmark pairs are static and do not simulate interactive multi-stage recruitment funnels.

### Recommended Future Work
- Establish empirical research partnerships to benchmark Road2Hire predictions against anonymized, longitudinal hiring cohort outcomes.
- Measure inter-annotator agreement (Fleiss' Kappa) between model readiness predictions and senior technical recruiter evaluations.

---

## 12. Enterprise Generalization & Production Readiness Boundaries

### Current Implementation
- Thread-safe Python integration interface (`process_resume`, `get_pipeline`) protected by `threading.RLock`.
- Synchronous local CPU execution designed for single-node development and API gateway integration.

### Known Limitations
- **Cold-Start Latency:** Initial singleton pre-warming (`get_pipeline()`, `get_road2hire_model()`) requires $14\text{s}$ to $18\text{s}$ to load taxonomy graphs, word vectors, and scikit-learn models into memory. While subsequent warm calls execute in $1.5\text{s}$ to $2.5\text{s}$, serverless cold starts would be unacceptable.
- **Memory Footprint:** In-memory graph structures, embedding models, and caches require approximately $1.2\text{ GB}$ to $1.8\text{ GB}$ of resident RAM per worker process.
- **Single-Node Execution:** The AI/ML package does not implement distributed task orchestration, distributed caching, or horizontal worker pools; these must be managed by the host application (e.g., Celery, Redis, Kubernetes).

### Recommended Future Work
- Package model artifacts into optimized ONNX or TensorRT runtimes for accelerated inference and reduced memory footprint.
- Establish decoupled model microservices with Triton Inference Server or TorchServe for independent horizontal autoscaling.

---

## Limitations Matrix & Engineering Roadmap

| Domain | Current Implementation | Major Limitation | Target Resolution | Complexity |
| :--- | :--- | :--- | :--- | :---: |
| **Ingestion** | `pypdf` text stream parsing | Scanned/image PDFs fail | Tesseract/Document AI OCR fallback | Medium |
| **Extraction** | Dictionary + MiniLM embeddings | Contextual acronym ambiguity | Fine-tuned SpanBERT NER | High |
| **Taxonomy** | ESCO v1.1.1 static graph | 2022 snapshot; missing novel AI titles | Automated web-scale taxonomy expansion | High |
| **Matching** | Heuristic 75/25 linear formula | Uncalibrated, non-compensatory | Learned non-linear ranker (LambdaMART) | High |
| **Readiness** | L2 Logistic Regression ($N=71$) | Small dataset, minority class ($n=3$) | Expand to $N \ge 1,000$; Cost-sensitive loss | Medium |
| **Calibration** | Raw Softmax outputs | Probabilities are uncalibrated | Platt Scaling / Isotonic Calibration | Low |
| **Explainability**| SHAP `LinearExplainer` | Local attribution $\neq$ real causation | Counterfactual Explanations (DiCE) | Medium |
| **OOD** | Univariate bounding boxes | Misses joint manifold anomalies | Mahalanobis Distance / Isolation Forest | Medium |
| **Roadmap** | Static 4-phase rule-based allocation| No prerequisite DAG or pacing | Dynamic DAG curriculum planner | High |
| **Infrastructure**| In-memory Python singleton | 15s cold start, single-node only | Containerized pre-warmed worker pool | Medium |

---

## Conclusion & Ethical AI Governance

The Road2Hire AI/ML pipeline delivers a defensible, deterministic, and explainable decision-support engine. However, in accordance with responsible AI standards, **the pipeline must strictly function as an assistive advisory tool for human recruiters and career counselors, not as an autonomous automated hiring gatekeeper.**

Recruiters, hiring managers, and career mentors must review candidate profiles alongside model outputs, taking into account qualitative indicators, socio-economic context, and holistic portfolio evidence that automated natural language processing cannot capture.

