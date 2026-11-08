# Road2Hire — 02: AI/ML Research, Methodology and Taxonomy Strategy

**Document Version:** 1.0.0  
**Status:** Completed & Validated  
**Module:** AI/ML Research Foundation & Taxonomy Infrastructure  
**Primary Source Modules:** [`AI/Knowledge_Graph/`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Knowledge_Graph), [`Datasets/ESCO_ONET/`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Datasets/ESCO_ONET), [`Datasets/Skill_Taxonomy/`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Datasets/Skill_Taxonomy)  

---

## 1. Research Problem & Theoretical Motivation

Current career guidance, applicant tracking, and job recommendation systems overwhelmingly rely on superficial keyword matching between candidate resumes and job postings. While these keyword-based approaches can verify the literal presence of specific technologies, they exhibit fundamental shortcomings:
1. **Inability to Model Skill Gaps:** They treat missing skills as binary non-matches without assessing their severity, essentiality, or pedagogical prerequisites.
2. **Ignorance of Semantic Relatedness:** They fail to capture semantic relationships between related skills (e.g. recognizing that proficiency in PostgreSQL implies deep familiarity with SQL and relational databases).
3. **Absence of Explainable Rationale:** They cannot explain *why* a candidate is deemed ready or unready, leaving candidates and recruiters without actionable insights.
4. **Disconnection from Learning Actions:** They fail to translate identified deficiencies into structured, actionable, and personalized learning trajectories.

Road2Hire resolves these challenges by formulating an applied research framework that synthesizes Natural Language Processing (NLP), dense vector embeddings, knowledge graphs, supervised readiness prediction, local explainability (SHAP), and personalized learning path planning into a unified intelligence engine.

---

## 2. Research Questions

The design and evaluation of Road2Hire are guided by three primary research questions:

### RQ1 — Skill Gap Identification
> *How effectively can NLP, boundary-aware Trie tokenization, and semantic skill matching identify the skill gaps between an unstructured candidate resume and the structured requirements of a target occupation?*

### RQ2 — Career Recommendation & Taxonomic Reasoning
> *How effectively can hierarchical knowledge graphs (ESCO v1.1.1) and supervised readiness classification utilize identified skill gaps to recommend suitable career paths and prioritize missing competencies?*

### RQ3 — Personalized & Explainable Guidance
> *How effectively can explainable AI (SHAP local feature attribution) and personalized curriculum planning provide transparent, trustworthy, and actionable career guidance grounded in candidate competencies?*

---

## 3. Literature Review & Prior Art

Road2Hire builds upon seven distinct areas of research across workforce analytics, talent intelligence, and machine learning:

### 3.1 Skill-Gap Identification Systems

1. **Large-Scale Occupational Skills Normalization for Online Recruitment**  
   - *Authors/Year:* Faizan Javed, Phuong Hoang, Thomas Mahoney, Matt McNair (2017).  
   - *Problem:* Normalizing noisy, freeform occupational skills from resumes and job advertisements.  
   - *Approach:* Developed *SKILL*, a Named Entity Normalization system using semantic word vectors and Markov Chain Monte Carlo (MCMC) sense disambiguation.  
   - *Key Finding:* Achieved 90% precision and 73% recall in skill tagging.  
   - *Limitation & Road2Hire Extension:* Focused strictly on skill extraction/normalization; did not model multi-tier skill gaps, career readiness prediction, or learning roadmaps.

2. **Application of a Skills Taxonomy, Machine Learning and Online Data to Inform Career and Training Decisions**  
   - *Authors/Year:* Claire M. Mason, Haohui Chen, David Evans, Gavin Walker (2023).  
   - *Problem:* Addressing the widening gap between worker skill supply and employer skill demand.  
   - *Approach:* Combined the ESCO skills taxonomy with NLP and online job advertisement data to quantify skill supply/demand dynamics.  
   - *Key Finding:* Proved that standardized taxonomies can identify structural workforce skill gaps to support retraining.  
   - *Limitation & Road2Hire Extension:* Addressed labor-market aggregates rather than candidate-specific resume processing, explainable AI, or candidate knowledge subgraphs.

3. **A Combined Representation Learning Approach for Better Job and Skill Recommendation**  
   - *Authors/Year:* Vachik S. Dave, Baichuan Zhang, Mohammad Al Hasan, Khalifeh AlJadda, Mohammed Korayem (2018).  
   - *Problem:* Recommending suitable jobs and transitional skills during career changes.  
   - *Approach:* Constructed three interconnected networks (job-transition, job-skill, and skill co-occurrence) and trained joint representation embeddings.  
   - *Key Finding:* Graph representation learning significantly improved job transition recommendations.  
   - *Limitation & Road2Hire Extension:* Emphasized latent space recommendations without granular, explainable breakdowns of missing essential vs. optional competencies.

4. **Skill-driven Recommendations for Job Transition Pathways**  
   - *Authors/Year:* Alexandra Dawson, Marian-Andrei Rizoiu, et al. (2021).  
   - *Problem:* Estimating occupational skill distances to guide worker career transitions.  
   - *Approach:* Formulated a *Skills Space* methodology measuring geometric distances between occupational skill sets over 8 million job postings.  
   - *Key Finding:* Recommender achieved 76% accuracy in predicting viable occupational transitions.  
   - *Limitation & Road2Hire Extension:* Evaluated macro-level occupational transitions rather than individual resume parsing, student candidate profiles, or local SHAP explanations.

### 3.2 Resume NLP & Skill Extraction

1. **Skill Extraction from Resumes and Job Offers across Six Languages**  
   - *Authors/Year:* Laura Vásquez-Rodríguez, Bertrand Audrin, Samuel Michel, et al. (2026).  
   - *Problem:* Evaluating extraction across multilingual and highly variable resume formats versus standardized job offers.  
   - *Approach:* Compared rule-based taxonomy matching (ESCO), Sentence-BERT embeddings, and fine-tuned multilingual BERT (mBERT) for Named Entity Recognition.  
   - *Key Finding:* Supervised models achieved F1 $\approx 0.60$ on skills; occupation detection was more tractable (F1 $\approx 0.80$). Showed that resumes exhibit substantially greater layout variability than job postings.  
   - *Road2Hire Relevance:* Informed Road2Hire's hybrid architecture: leveraging exact Trie parsing for known taxonomy entities and dense transformer embeddings for semantic similarity.

2. **Implicit Skills Extraction Using Document Embedding and Its Use in Job Recommendation**  
   - *Authors/Year:* Akshay Gugnani, Hemant Misra (2020).  
   - *Problem:* Extracting unstated, implicit competencies from unstructured candidate documents.  
   - *Approach:* Ensemble system combining Watson NLU, PoS tagging rules, a 53k-term dictionary, and Doc2Vec trained on 1.1 million job descriptions to infer implicit skills.  
   - *Key Finding:* Ensemble achieved F1 = 0.83; adding implicit skills boosted Top-1 recommendation accuracy from 0.68 to 0.88 (+29.4%).  
   - *Road2Hire Relevance:* Supported Road2Hire's design choice to utilize hierarchical graph relations (`is_narrower_than`, `is_related_to`) to credit latent competencies.

### 3.3 Semantic Skill Matching

1. **SkillMatch: Evaluating Self-supervised Learning of Skill Relatedness**  
   - *Authors/Year:* Jens-Joris Decorte, Jeroen Van Hautte, Thomas Demeester, Chris Develder (2024).  
   - *Problem:* Lack of standardized benchmarks evaluating whether language models capture professional skill relatedness.  
   - *Approach:* Adapted Sentence-BERT via self-supervised contrastive learning on skill co-occurrences extracted from millions of job postings.  
   - *Key Finding:* Domain-adapted Sentence-BERT achieved AUC-PR of 0.969 on skill relatedness.  
   - *Road2Hire Relevance:* Validated the use of Sentence Transformers (`all-MiniLM-L6-v2`) for computing semantic similarity between resume skills and occupation requirements.

2. **Automatic Skills Standardization Method Based on Subject Expert Knowledge Extraction and Semantic Matching**  
   - *Authors/Year:* Juan Bernabé-Moreno, Álvaro Tejeda-Lorente, et al. (2019).  
   - *Problem:* High semantic variation and synonymy in job descriptions for identical roles.  
   - *Approach:* Combined GloVe embeddings, t-SNE, DBSCAN clustering, and Wikipedia knowledge expansion to standardize technical terms.  
   - *Key Finding:* Semantic clustering effectively identified skill neighborhoods (e.g. associating Python with SQL, R, Scala, and MATLAB).  
   - *Road2Hire Relevance:* Reinforced the need for curated alias mapping dictionaries to eliminate lexical duplicates before vector comparison.

### 3.4 Knowledge Graphs for Career Guidance

1. **Job Posting-Enriched Knowledge Graph for Skills-based Matching**  
   - *Authors/Year:* Maurits de Groot, Jelle Schutte, David Graus (2021).  
   - *Problem:* Keeping occupational skill requirements updated under rapid technological change.  
   - *Approach:* Constructed a knowledge graph joining ISCO occupations and ESCO skills with 600,000 job postings, using Node2Vec and Dijkstra pathfinding for career navigation.  
   - *Key Finding:* Graph representation effectively captured dynamic skill-occupation associations and enabled logical career path traversal.  
   - *Road2Hire Relevance:* Directly influenced Road2Hire's M1/M3 knowledge graph design, connecting candidate profiles to canonical ESCO concepts in a NetworkX directed subgraph.

### 3.5 Career Prediction & Recommendation

1. **Demand-Aware Career Path Recommendations: A Reinforcement Learning Approach**  
   - *Authors/Year:* Marios Kokkodis, Panagiotis G. Ipeirotis (2021).  
   - *Problem:* Recommending career transitions that maximize long-term earning potential and account for worker learning capacity.  
   - *Approach:* Formulated a Markov Decision Process (MDP) solved via Q-learning, combined with Bayesian learning estimation, Word2Vec, and XGBoost wage predictors over 1.73M applications.  
   - *Key Finding:* Recommended pathways yielded average wage improvements of 22% and increased skill acquisition diversity by 47%.  
   - *Road2Hire Relevance:* Provided empirical justification for structuring learning recommendations into progressive, multi-phase developmental milestones.

### 3.6 Explainable AI for Career Recommendation

1. **Explainable Person–Job Recommendations: Challenges, Approaches, and Comparative Analysis**  
   - *Authors/Year:* Fang Tang, Renqi Zhu, Feng Yao, Junzhi Wang, Lailong Luo, Bo Li (2025).  
   - *Problem:* Black-box deep learning recommendation systems create lack of trust among jobseekers and hiring managers.  
   - *Approach:* Systematic review of 85 studies categorizing explainability across feature importance, attention mechanisms, knowledge graph paths, and post-hoc attribution (SHAP, LIME).  
   - *Key Finding:* Counterfactual and additive feature attribution methods achieved the highest Explainability-Performance (E-P) scores (0.95).  
   - *Road2Hire Relevance:* Guided the adoption of `shap.LinearExplainer` to provide mathematically exact, additive feature attributions for readiness predictions.

### 3.7 Personalized Retrieval-Augmented Generation (RAG)

1. **RAG-Rec: Retrieval Augmented Generation for Robust Personalized Recommendation Systems**  
   - *Authors/Year:* Ahmed Aly, Ahmed Ibrahim, Rasha Kashef (2026).  
   - *Problem:* Mitigating LLM hallucinations and high fine-tuning costs in personalized recommendation.  
   - *Approach:* Combined MiniLM-L6-v2 vector retrieval with GPT-4o contextual generation over user preference histories.  
   - *Key Finding:* Vector retriever achieved Hit Rate@40 of 0.9942, successfully grounding LLM recommendations in verified user contexts.  
   - *Road2Hire Relevance:* Grounded Road2Hire's roadmap synthesis in retrieved, verified learning resources rather than ungrounded generative LLM hallucinations.

---

## 4. Research Methodology

Road2Hire employs an applied engineering and empirical research methodology consisting of five interconnected stages:

```mermaid
flowchart LR
    S1["1. Data Ingestion & Preprocessing"] --> S2["2. Skill Extraction & Normalization"]
    S2 --> S3["3. Hybrid Gap Detection & Graph Grounding"]
    S3 --> S4["4. Supervised Readiness & Explainability"]
    S4 --> S5["5. Pedagogical Roadmap Synthesis"]
```

1. **Applied System Development:** Constructing modular, independently testable pipeline components that communicate via typed data contracts.
2. **Deterministic Preprocessing:** Applying strict regex patterns, PyMuPDF stream decoders, and deterministic section parsers to avoid stochastic parsing failures.
3. **Hybrid Taxonomic Alignment:** Layering exact concept URI equality, graph traversal relations, and Hungarian bipartite semantic matching to ensure high precision while capturing semantic nuance.
4. **Supervised Empirical Classification:** Training an L2-regularized multinomial classifier on verified expert annotations, guarded by strict anti-leakage filters and empirical bounding box OOD checks.
5. **Axiomatic Explainability:** Guaranteeing mathematical additivity via Shapley values, providing transparent insight into model decision margins.

---

## 5. Skill Taxonomy Strategy & Categorization

To support consistent normalization, Road2Hire defines a comprehensive master taxonomy grounded in ESCO and O*NET:

### 5.1 Skill Categories & Domains

| Category | Domain Scope | Exemplar Competencies |
| :--- | :--- | :--- |
| **1. Programming Languages** | General-purpose, compiled & interpreted languages | Python, Java, C++, C, JavaScript, TypeScript, Go, Rust |
| **2. Frontend Development** | Client-side frameworks, styling, and markup | React, Angular, Next.js, Vue.js, HTML5, CSS3, Tailwind CSS |
| **3. Backend Development** | Server runtimes, REST frameworks, and architectures | Node.js, FastAPI, Django, Flask, Spring Boot, Express.js |
| **4. Databases & Storage** | Relational, document, key-value, and caching stores | PostgreSQL, MySQL, MongoDB, Redis, Cassandra, SQLite |
| **5. AI & Machine Learning** | Deep learning, statistical learning, and NLP libraries | TensorFlow, PyTorch, Scikit-learn, HuggingFace, spaCy |
| **6. Data Analytics & Engineering**| Data pipelines, distributed processing, and BI tools | Pandas, NumPy, Apache Spark, SQL, Power BI, Tableau, Airflow |
| **7. Cloud Computing** | Infrastructure-as-a-Service and serverless clouds | AWS (EC2, S3, Lambda), Microsoft Azure, Google Cloud (GCP) |
| **8. DevOps & Orchestration** | Containers, CI/CD pipelines, and infrastructure as code| Docker, Kubernetes, GitHub Actions, Jenkins, Terraform |
| **9. Developer Tools** | Version control, IDEs, debugging, and testing suites | Git, Linux CLI, Postman, VS Code, Pytest, JIRA |
| **10. Soft & Transferable Skills**| Professional competencies and collaboration skills | Communication, Problem Solving, Leadership, Teamwork, Agile |

### 5.2 Taxonomy Schemas & Identifiers
The master processed taxonomy in `Datasets/Skill_Taxonomy/Processed/Skill_Taxonomy.csv` conforms to:
- `Skill_Id`: Unique internal Road2Hire integer identifier.
- `Skill_Name`: Standardized canonical name.
- `Category`: High-level domain cluster.
- `Sub_Category`: Granular technical sub-discipline.
- `ESCO_Id`: Official European Commission concept URI.
- `ONET_Id`: US Department of Labor 8-digit occupational/element code.
- `Aliases`: Comma-separated alternative strings and acronyms.

---

## 6. ESCO & O*NET Mapping Strategy

### 6.1 Complementary Taxonomic Roles
Road2Hire combines the complementary strengths of the two leading global labor taxonomies:
- **ESCO v1.1.1 (European Commission):** Primary structural backbone. Provides 2,942 occupations, 13,890 skills, rich multilingual labels, and formal directed relationships (`requires_essential_skill`, `requires_optional_skill`, `broader_skill`, `narrower_skill`, `related`).
- **O*NET 28.0 (US Department of Labor):** Provides quantitative importance scales (1–5) and level ratings across knowledge, abilities, and technology tools, used to calibrate skill criticality.

### 6.2 Lexical Normalization & Alias Crosswalks
Raw extracted mentions are normalized before comparison through curated equivalence rules:

| Raw Resume Mention | Canonical Normalized Skill | ESCO Concept URI |
| :--- | :--- | :--- |
| `JS`, `js`, `Javascript` | `JavaScript` | `http://data.europa.eu/esco/skill/9c670a49-411a-4712-9a00-fa06ff3df8e2` |
| `ReactJS`, `React.js` | `React` | `http://data.europa.eu/esco/skill/60bb5444-42f0-4966-bd91-f92e597ab418` |
| `Postgres`, `psql` | `PostgreSQL` | `http://data.europa.eu/esco/skill/44e05b53-0663-441d-91b5-3129844c8c76` |
| `Py`, `python3` | `Python (computer programming)`| `http://data.europa.eu/esco/skill/4c5b2a62-5a76-4d99-a7a8-cbf04e9e8d1e` |
| `TF`, `Tensor Flow` | `TensorFlow` | `http://data.europa.eu/esco/skill/d2208a0d-5b3a-4286-a700-14e300ce4cbb` |
| `k8s`, `kube` | `Kubernetes` | `http://data.europa.eu/esco/skill/b1397dc8-c179-4a94-8255-e7f1d4ea8bc5` |

### 6.3 Occupation-to-Skill Requirement Partitioning
Every ESCO occupation strictly partitions associated competencies into two tiers:
1. **Essential Skills ($E$):** Mandatory competencies without which core occupational duties cannot be discharged.
2. **Optional Skills ($O$):** Specialized, domain-specific, or advanced tools that broaden candidate versatility.

### 6.4 O*NET Importance Scale Conversion
When weighting missing skills in curriculum prioritization:

| Importance Label | O*NET Score | Weight in Prioritization |
| :--- | :---: | :---: |
| **Essential** | 5 | 1.00 (Critical prerequisite) |
| **High** | 4 | 0.80 (Core competency) |
| **Medium** | 3 | 0.60 (Standard requirement) |
| **Low** | 2 | 0.40 (Supporting skill) |
| **Nice to Have** | 1 | 0.20 (Elective/optional) |

---

## 7. Data Annotation Strategy & Rubric Guidelines

Supervised modeling and evaluation rely on formal labeling standards across resumes, job postings, and readiness tiers:

### 7.1 Entity Extraction Labels (NER)
- `SKILL`: Technical competency or language (e.g. "Python").
- `TOOL`: Developer tool or software package (e.g. "Git", "Docker").
- `FRAMEWORK`: Software library or framework (e.g. "React", "FastAPI").
- `DATABASE`: Database management engine (e.g. "PostgreSQL").
- `EDUCATION`: Degree, credential, or discipline (e.g. "B.Tech Computer Science").
- `CERTIFICATION`: Professional certification (e.g. "AWS Solutions Architect").
- `EXPERIENCE`: Professional title or duration (e.g. "2 Years Software Engineer").
- `PROJECT`: Technical project title (e.g. "Road2Hire").

### 7.2 Skill Gap Evaluation Labels
- `PRESENT`: Concept explicitly evidenced in candidate profile.
- `MISSING`: Concept required by occupation but absent from profile.
- `PARTIAL`: Adjacent or broader concept present (taxonomic or semantic partial credit).
- `EXTRA`: Candidate skill present on resume but not required by target occupation.

### 7.3 Career Readiness Classification Rubric
Governs the M4 supervised training dataset ($N=71$ labeled records):

| Readiness Class | Operational Definition | Empirical Profile Characteristics |
| :--- | :--- | :--- |
| **`Job Ready`** | Candidate possesses comprehensive essential skills and demonstrated hands-on execution maturity to perform role independently. | $\ge 2$ professional positions, $> 10$ verified skills, STEM degree, production project implementation. |
| **`Developing`** | Candidate possesses fundamental technical competencies and degree foundation, but requires targeted skill acquisition and practical project depth. | 0–1 professional positions (entry-level/student), 4–9 verified skills, academic degrees, prototype projects. |
| **`Not Ready`** | Candidate exhibits severe skill deficiencies across essential occupation requirements and lacks foundational software/technical background. | $< 3$ verified skills, non-STEM background, 0 documented projects or relevant coursework. |

### 7.4 Annotation Governance Rules
1. **Source Text Grounding:** Annotators must label only information explicitly evidenced in source documents; skills must never be hallucinated based on assumed job titles.
2. **Span Preservation:** Exact character offsets (`start`, `end`) must align with raw text strings.
3. **Data Leakage Prohibition:** Candidate IDs, pair IDs, and human rubric sub-ratings are strictly isolated and excluded from training feature vectors.
4. **Deduplication Safeguards:** Duplicate or highly repetitive candidate profiles are identified via evidence clustering and withheld from training splits (`readiness_label: null`) to prevent train-test contamination.

---

## 8. Related Documentation

- For overall architecture and pipeline stages, see [01: Architecture & Pipeline](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Docs/01_AI_ML_Architecture_and_Pipeline.md).
- For algorithmic formulas, Hungarian matching, and SHAP math, see [03: Algorithms & Methodology](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Docs/03_AI_ML_Algorithms_and_Methodology.md).
- For empirical validation, benchmarks, and known limitations, see [04: Model Evaluation & Limitations](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Docs/04_AI_ML_Model_Evaluation_and_Limitations.md).
- For public APIs, JSON Schemas, and integration guidelines, see [05: Output & Integration Contract](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Docs/05_AI_ML_Output_and_Integration_Contract.md).
- For database architecture and PostgreSQL mappings, see [06: Database Storage Specification](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Docs/06_AI_ML_Database_Storage_Specification.md).
- For engineering handover and checklists, see [07: Final Handover Document](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Docs/07_AI_ML_Final_Handover.md).

