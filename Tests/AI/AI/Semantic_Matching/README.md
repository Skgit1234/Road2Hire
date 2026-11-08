# Semantic Skill Matching — Sentence Transformers (Issue #17)

Documentation for the Sentence Transformer semantic skill matching engine, threshold calibration, and evaluation pipeline in Road2Hire ([M3][AI-ML] Issue #17).

---

## 1. Purpose and Scope

While keyword matching (Issue #16 baseline) relies on exact string equality and taxonomy matching relies on curated synonym dictionaries, many candidate skills:
1. Differ in naming or phrasing (e.g., `Golang` vs `Go`, `Postgres` vs `PostgreSQL`).
2. Are modern technologies not yet present in the curated taxonomy or ESCO/O*NET mappings (e.g., `Rust`, `Go`, `FastAPI`, `Terraform`).
3. Are conceptually related but distinct capabilities that must **not** be conflated as equivalent (e.g., `Docker` vs `Kubernetes`, `Java` vs `JavaScript`, `C` vs `C++`).

The semantic skill matching subsystem provides:
- **Vector Embedding**: Dense 384-dimensional semantic representations via `sentence-transformers/all-MiniLM-L6-v2`.
- **Unknown Skill Preservation**: Extracted skills absent from curated vocabularies are preserved in full fidelity without forcing erroneous taxonomy classifications.
- **Maximum-Weight Bipartite Assignment**: One-to-one global optimal alignment between candidate skills and required skills via the Hungarian algorithm.
- **Multi-Tier Classification**: Clear separation between Confirmed Matches, Related Skills, Uncertain Matches, and Non-Matches.
- **Empirical Threshold Calibration**: Systematic threshold sweeping and error analysis across benchmark cases.

---

## 2. Architecture and Module Structure

```
AI/Semantic_Matching/
├── __init__.py                     # Public API exports
├── semantic_matcher.py             # Matching engine, bipartite assignment, multi-tier classifier
├── threshold_analysis.py           # Empirical threshold sweep & error analysis (0.60 - 0.95)
├── evaluate_semantic.py            # Comparative evaluation (Keyword vs Taxonomy vs Semantic)
├── semantic_evaluation_data.json   # 13 annotated benchmark scenarios (positive, negative, related, edge cases)
├── semantic_matching_results.json  # Machine-readable evaluation results & metrics
└── README.md                       # Subsystem documentation (this file)
```

---

## 3. Model Selection & Execution Requirements

- **Model**: `sentence-transformers/all-MiniLM-L6-v2`
  - Dimensions: 384
  - Embeddings: L2-normalized unit vectors (cosine similarity equals dot product)
  - Speed: Fast inference on CPU (~15ms per batch), minimal memory footprint (~80 MB)
- **Offline Execution**:
  - Model weights are cached locally in the Hugging Face cache directory (`~/.cache/huggingface/hub/`).
  - For strictly air-gapped environments, set `HF_HUB_OFFLINE=1` in the environment.

---

## 4. Unknown & Unrecognized Skill Lifecycle

Skills are **never discarded** simply because they are missing from [skill_graph_v1.json](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Knowledge_Graph/skill_graph_v1.json) or [Road2Hire_ESCO_Mapping.csv](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Skill_Extraction/skill_taxonomy_mapper.py).

### Matching Status Tiers:

| Status Tier | Definition | Handling in Scoring | Knowledge Graph / ESCO Impact |
|---|---|---|---|
| **`CONFIRMED_MATCH`** | Canonical match, exact string match, or semantic similarity $\ge \tau_{\text{match}}$ without conflicting topical boundaries. | Included in `present_skills`; contributes to True Positives (TP). | Preserved as verified match. Does **not** auto-modify ESCO mapping without validation. |
| **`RELATED_SKILL`** | Topically or ecosystem-related skills (e.g. `Docker` vs `Kubernetes`, `FastAPI` vs `REST APIs`). | Included in `related_skills` with similarity evidence. **NEVER** treated as equivalent or counted as present. | Preserved as contextual association for career pathing; not merged into ontology. |
| **`UNCERTAIN_MATCH`** | Similarity falls in the ambiguous band $[\tau_{\text{uncertain}}, \tau_{\text{match}})$. | Routed to `unresolved_skills` with matching evidence and scores. Does **not** fulfill requirement. | Flagged for future human/taxonomy review. Never auto-added to graph. |
| **`NON_MATCH`** | Similarity $< \tau_{\text{uncertain}}$ or known distinct technologies (e.g. `Rust` vs `Go`, `Java` vs `JavaScript`, `C` vs `C++`). | Unmatched required skills remain in `missing_skills` (FN); candidate skills in `candidate_skills_not_required`. | No modification. |

---

## 5. Maximum-Weight Bipartite Assignment

To prevent greedy ordering bias (e.g., an earlier skill taking an ambiguous match that deprives another skill of its only valid match), matching between candidate skills $\{c_1, \dots, c_m\}$ and required skills $\{r_1, \dots, r_n\}$ is formulated as a global maximum-weight bipartite assignment:

$$\max_{\pi} \sum_{i} \text{sim}(c_i, r_{\pi(i)})$$

- Solved using the Hungarian algorithm via `scipy.optimize.linear_sum_assignment` on the negative similarity cost matrix.
- Edges below $\tau_{\text{uncertain}}$ or flagged as known distinct/related pairs are cost-penalized, preventing weak or invalid pairings from being forced.
- A pure-Python priority-queue fallback is provided if `scipy` is unavailable in restricted environments.

---

## 6. Empirical Threshold Selection Strategy

> [!IMPORTANT]
> **Cosine similarity is a geometric distance metric, NOT a posterior probability of equivalence.** Thresholds cannot be assumed a priori and must be calibrated empirically.

### Empirical Sweep Results across Calibration Pairs:

The sweep systematically evaluates grid thresholds from 0.60 to 0.95 in increments of 0.05, and explicitly includes candidate threshold 0.82:

| Threshold ($\tau$) | TP | FP | FN | TN | Precision | Recall | F1 | Notes |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| **0.60** | 4 | 0 | 2 | 9 | 1.000 | 0.667 | 0.800 | Optimal F1 plateau; closest to topical drift boundary |
| **0.65** | 4 | 0 | 2 | 9 | 1.000 | 0.667 | 0.800 | Optimal F1 plateau |
| **0.70** | 4 | 0 | 2 | 9 | 1.000 | 0.667 | 0.800 | Optimal F1 plateau |
| **0.75** | 4 | 0 | 2 | 9 | 1.000 | 0.667 | 0.800 | Optimal F1 plateau |
| **0.80** | 4 | 0 | 2 | 9 | 1.000 | 0.667 | 0.800 | Optimal F1 plateau |
| **0.82** | 4 | 0 | 2 | 9 | 1.000 | 0.667 | 0.800 | **Selected Provisional Match Threshold** ($\tau_{\text{match}}$) |
| **0.85** | 4 | 0 | 2 | 9 | 1.000 | 0.667 | 0.800 | Upper boundary of optimal plateau |
| **0.90** | 2 | 0 | 4 | 9 | 1.000 | 0.333 | 0.500 | Recall drops steeply (false negatives on `Golang`/`Go`) |
| **0.95** | 2 | 0 | 4 | 9 | 1.000 | 0.333 | 0.500 | Severe false negatives |

### Decision Rationale:
- **Optimal Plateau**: Across $\tau \in [0.60, 0.85]$, the model achieves 0 False Positives on deceptive lexical pairs (`Java`/`JavaScript`, `C`/`C++`) while preserving Recall on valid uncatalogued aliases (`Golang`/`Go` at sim ~0.87, `Postgres`/`PostgreSQL` at sim ~0.90).
- **Conservative Selection**: Rather than selecting $\tau = 0.60$ (which sits right next to the boundary of related technologies), we select **$\tau_{\text{match}} = 0.82$** to provide maximum safety margin against out-of-distribution false positives.
- **Uncertain Band**: **$\tau_{\text{uncertain}} = 0.65$** isolates ambiguous pairs for human/taxonomy review.

---

## 7. NDCG Applicability and Graded Evaluation

- **Binary Skill Gap Detection**: For standard required-skill gap detection, candidate output is an unranked set. Therefore, `"ndcg": None` is returned, adhering strictly to the Issue #16 convention.
- **Ranked Retrieval Queries**: NDCG is computed via [compute_ranking_ndcg](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Semantic_Matching/semantic_matcher.py#L462-L515) **only** when an ordered candidate pool and graded relevance judgments are present:
  - Relevance 2: Exact / Canonical equivalent skill
  - Relevance 1: Related / Ecosystem concept
  - Relevance 0: Irrelevant / Distinct technology
- Evaluated on benchmark query `SEM013` (`Go` with candidate pool `["Golang", "Docker", "Python"]`), achieving **NDCG@3 = 1.000**.

---

## 8. Comparative Evaluation with Issue #16 Baselines

Evaluated across the 13 annotated benchmark scenarios in [semantic_evaluation_data.json](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Semantic_Matching/semantic_evaluation_data.json):

| Matcher Subsystem | Macro Precision | Macro Recall | Macro F1 | Avg Match Score | Key Differentiator |
|---|:---:|:---:|:---:|:---:|---|
| **Keyword Baseline** | 1.000 | 0.154 | 0.778 | 0.154 | Exact string match only; fails on aliases and uncatalogued variants |
| **Taxonomy Baseline** | 1.000 | 0.200 | 0.667 | 0.077 | Normalizes curated synonyms; isolates uncatalogued skills as gaps |
| **Semantic Matching** | **1.000** | **0.385** | **0.889** | **0.385** | **Resolves uncatalogued aliases (Golang, Postgres) & preserves unfamiliar skills (Rust, Go)** |

*Note: Macro Precision is 1.000 across matchers because non-matches are correctly rejected as missing (FP = 0). Semantic matching achieves more than double the recall of keyword matching by resolving aliases for unfamiliar technologies.*

---

## 9. Running Analysis and Tests

### 1. Run Empirical Threshold Analysis Sweep
```powershell
.\.venv\Scripts\python.exe AI/Semantic_Matching/threshold_analysis.py
```

### 2. Run Comparative Evaluation Pipeline
```powershell
.\.venv\Scripts\python.exe AI/Semantic_Matching/evaluate_semantic.py
```

### 3. Run Semantic Matcher Test Suite
```powershell
.\.venv\Scripts\pytest.exe Tests/AI/test_semantic_skill_matcher.py -v
```

### 4. Run Baseline Regression Tests (Issue #16)
```powershell
.\.venv\Scripts\pytest.exe Tests/AI/test_skill_matching_baselines.py -v
```

### 5. Run Full AI Test Suite
```powershell
.\.venv\Scripts\pytest.exe Tests/AI
```

---

## 10. Documented Limitations

1. **Synthetic Data Disclaimer**: All benchmark metrics are computed on hand-crafted synthetic cases designed for calibration and regression testing. They do **not** establish unconstrained real-world production accuracy.
2. **Short Polysemous Tokens**: Single-word skills with ordinary English meanings (e.g., `Go`, `C`, `R`) can suffer from semantic drift without contextual expansion (`Go programming language`).
3. **One-to-One Bipartite Assumption**: Bipartite matching enforces 1-to-1 pairings. Compound skills (e.g. `Full Stack Development` subsuming `React` and `Node.js`) require future hybrid knowledge graph reasoning.
