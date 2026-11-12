# Skill Matching Baselines — Keyword & Taxonomy

Documentation for the baseline skill matching implementations in Road2Hire ([M3][AI-ML] Issue #16).

---

## 1. Purpose and Scope

In Road2Hire, job readiness scoring and skill gap detection require comparing a candidate's skills against job required skills. The baseline subsystem provides two distinct, non-ML baseline matching approaches:

1. **Keyword Baseline (`keyword_baseline.py`)**:
   - Performs exact, case-insensitive string matching.
   - Serves as the minimal, transparent benchmark baseline.
   - Does not perform synonym resolution or taxonomy traversal.

2. **Taxonomy Baseline (`taxonomy_baseline.py`)**:
   - Performs alias expansion and canonical skill normalization using the Road2Hire Skill Graph vocabulary (`skill_graph_v1.json`) and curated synonyms (`SKILL_SYNONYMS`).
   - Resolves curated European Skills, Competences, and Occupations (ESCO) taxonomy mappings (`Road2Hire_ESCO_Mapping.csv`).
   - Distinguishes taxonomy vocabulary coverage gaps from genuine missing skills without forcing incorrect mappings.

Both matchers are kept strictly distinguishable so they can be evaluated independently against ground-truth benchmarks.

---

## 2. Usage and Differences

### A. Keyword Matcher

```python
from AI.Baseline.keyword_baseline import keyword_match, keyword_match_with_metrics

candidate = ["ML", "sklearn", "Python"]
required = ["Machine Learning", "Scikit-learn", "Python"]

# Backward-compatible 3-field output:
base_result = keyword_match(candidate, required)
# {
#   "present_skills": ["Python"],
#   "missing_skills": ["Machine Learning", "Scikit-learn"],
#   "match_score": 0.33
# }

# Extended output with gap-detection metrics and diagnostics:
metric_result = keyword_match_with_metrics(candidate, required)
# {
#   "present_skills": ["Python"],
#   "missing_skills": ["Machine Learning", "Scikit-learn"],
#   "match_score": 0.33,
#   "tp": 1, "fp": 0, "fn": 2,
#   "precision": 1.0,
#   "recall": 0.3333333333333333,
#   "f1": 0.5,
#   "candidate_skills_not_required": ["ML", "sklearn"],
#   "ndcg": None
# }
```

### B. Taxonomy Matcher

```python
from AI.Baseline.taxonomy_baseline import taxonomy_match

candidate = ["ML", "sklearn", "Python"]
required = ["Machine Learning", "Scikit-learn", "Python"]

result = taxonomy_match(candidate, required)
# {
#   "present_skills": ["Machine Learning", "Scikit-learn", "Python"],
#   "missing_skills": [],
#   "unrecognized_candidate": [],
#   "unrecognized_required": [],
#   "candidate_skills_not_required": [],
#   "esco_status": {
#     "Machine Learning": "exact_concept",
#     "Scikit-learn": "unmapped",
#     "Python": "exact_concept"
#   },
#   "match_score": 1.0,
#   "tp": 3, "fp": 0, "fn": 0,
#   "precision": 1.0,
#   "recall": 1.0,
#   "f1": 1.0,
#   "ndcg": None
# }
```

### Key Differences Summary

| Feature | Keyword Matcher | Taxonomy Matcher |
|---|---|---|
| **Matching Mechanism** | Exact case-insensitive string equality | Canonical name normalization via synonym map & vocabulary |
| **Alias Expansion** | ❌ None (`ML` != `Machine Learning`) | ✅ Supported (`ML` $\rightarrow$ `Machine Learning`, `sklearn` $\rightarrow$ `Scikit-learn`) |
| **Vocabulary Gap Handling** | Matches any string verbatim if case matches | Isolates unrecognized terms in `unrecognized_candidate` / `unrecognized_required` |
| **ESCO Classification** | None | Annotates each recognized skill with its ESCO status |
| **Unmapped ESCO Matching** | Matches regardless of taxonomy | Matches at canonical level; annotates status as `"unmapped"` |

---

## 3. Skill Normalization and Alias Expansion

Skill normalization is performed using `normalize_skill_name(skill_name, vocabulary)` from `AI.Skill_Extraction.skill_extractor`.

Resolution order:
1. `skill_name.casefold()` is checked against `SKILL_SYNONYMS`:
   - `"python"` $\rightarrow$ `"Python"`
   - `"ml"` $\rightarrow$ `"Machine Learning"`
   - `"machine learning"` $\rightarrow$ `"Machine Learning"`
   - `"sklearn"`, `"scikit learn"`, `"scikit-learn"` $\rightarrow$ `"Scikit-learn"`
   - `"numpy"` $\rightarrow$ `"NumPy"`
   - `"pandas"` $\rightarrow$ `"Pandas"`
2. If not in synonyms, `skill_name.casefold()` is checked against entries in the curated vocabulary (`skill_graph_v1.json`):
   - `"Python"`, `"Machine Learning"`, `"NumPy"`, `"Pandas"`, `"Scikit-learn"`, `"SQL"`, `"Git"`, `"REST APIs"`, `"Data Analysis"`.
3. If not found in either synonyms or vocabulary, `normalize_skill_name()` returns `None`.

---

## 4. ESCO Mapping and Vocabulary Statuses

ESCO mappings are loaded from `Datasets/Skill_Taxonomy/Processed/Road2Hire_ESCO_Mapping.csv` via `load_esco_mapping()`.

### Skill Status Classification

1. **`"exact_concept"`**:
   - The skill is present in the ESCO CSV with an explicit concept URI and ESCO concept name (e.g., `"Python"`, `"Machine Learning"`).
2. **`"unmapped"`**:
   - The skill is recorded in the ESCO CSV with `Mapping_Type == "unmapped"` and empty URI/name fields (e.g., `"NumPy"`, `"Pandas"`, `"Scikit-learn"`).
   - **Crucial Rule**: Unmapped ESCO skills **still match at the canonical level**. Their lack of an ESCO URI is an annotation, not a blocker for candidate evaluation.
3. **`"not_in_esco_csv"`**:
   - The skill is in Road2Hire's graph vocabulary (`skill_graph_v1.json`), but has no row in the curated ESCO CSV (e.g., `"SQL"`, `"Git"`, `"REST APIs"`, `"Data Analysis"`).
4. **Unrecognized by current vocabulary/taxonomy matcher (`None`)**:
   - The skill does not appear in the current vocabulary or synonym table (e.g., `"JavaScript"`, `"React"`, `"UnknownFramework"`).
   - **Diagnostic Label**: These are recorded in `unrecognized_candidate` or `unrecognized_required` as *"not recognized by the current vocabulary/taxonomy matcher"*. This indicates a vocabulary coverage boundary in the platform's current taxonomy, **not** that the skill itself is invalid or fictional.

---

## 5. Metrics and Conventions

All metrics are implemented in `AI/Baseline/evaluation_metrics.py` from first principles with zero external dependencies.

### A. Frame of Reference: Required-Skill Gap Detection

The core task is determining whether each **required job skill** is present or missing in the candidate:
- **True Positive (TP)**: A required skill correctly identified as present in the candidate.
- **False Negative (FN)**: A required skill the candidate lacks (reported in `missing_skills`).
- **False Positive (FP)**: A required skill incorrectly asserted to be present when the candidate lacks it. Because both matchers perform exact matching (string or canonical), **$\text{FP} = 0$ by construction**.

### B. Precision Limitation

Because $\text{FP} = 0$ by construction:
$$\text{Precision} = \frac{\text{TP}}{\text{TP} + \text{FP}} = \frac{\text{TP}}{\text{TP}} = 1.0 \quad (\text{when } \text{TP} > 0)$$

**Important Limitation**: Under this required-skill gap framing, Precision confirms that the matcher never produces false alarms on required skills. However, it does **not** evaluate whether the candidate holds irrelevant skills. Any candidate skills not required by the job are captured separately in `candidate_skills_not_required` and do not affect Precision, Recall, or F1.

### C. Undefined-Value Conventions ($0/0$)

| Situation | Precision | Recall | F1 | `match_score` |
|---|---|---|---|---|
| **No required skills** ($|req| = 0$) | `None` (0/0) | `None` (0/0) | `None` | `0.0` |
| **Empty candidate** ($cand = []$, $|req| > 0$) | `None` (0/0) | `0.0` | `None` | `0.0` |
| **No overlap** ($\text{TP} = 0$, $|req| > 0$) | `None` (0/0) | `0.0` | `None` | `0.0` |
| **Perfect match** ($\text{TP} > 0, \text{FN} = 0$) | `1.0` | `1.0` | `1.0` | `1.0` |

### D. Macro-Aggregation Conventions (`aggregate_metrics`)

When computing macro-averages across evaluation samples:
- `Recall` is defined for all typical samples ($0.0$ when all required skills are missing) and is included in the macro-average.
- Samples with undefined `Precision` (`None`) or `F1` (`None`) are **excluded** from the macro-averages for Precision and F1. Only defined values contribute.
- Undefined sample counts are reported as `precision_undefined_count` and `f1_undefined_count` so callers can assess sample coverage.
- If all samples have `Precision = None`, `macro_precision` returns `None`.

### E. NDCG Applicability

Both keyword and taxonomy matchers produce unranked binary sets of present/missing skills. Therefore, both matchers return `"ndcg": None`. A first-principles utility `ndcg_at_k(ranked_list, relevant_set, k)` is provided in `evaluation_metrics.py` for future ranked/embedding matchers and is independently tested.

---

## 6. Evaluation Benchmark Suite (`evaluation_data.json`)

The evaluation suite defines 8 distinct benchmark cases with hand-traced, independently verified ground truth:

| ID | Description | Candidate Skills | Required Skills | Keyword Match Score / P / R / F1 | Taxonomy Match Score / P / R / F1 | Key Test Characteristic |
|---|---|---|---|---|---|---|
| **EVAL001** | Partial match | `Python`, `Pandas`, `NumPy` | `Python`, `Pandas`, `Scikit-learn`, `Machine Learning` | 0.50 / 1.0 / 0.50 / 0.67 | 0.50 / 1.0 / 0.50 / 0.67 | Normal partial overlap |
| **EVAL002** | Full match | `Python`, `Machine Learning`, `Scikit-learn` | `Python`, `Machine Learning`, `Scikit-learn` | 1.0 / 1.0 / 1.0 / 1.0 | 1.0 / 1.0 / 1.0 / 1.0 | Perfect coverage |
| **EVAL003** | Cross-domain | `JavaScript`, `React` | `Python`, `JavaScript`, `React` | 0.67 / 1.0 / 0.67 / 0.80 | 0.0 / None / 0.0 / None | JS and React recognized by keyword; categorized as vocabulary gap in taxonomy |
| **EVAL004** | Alias expansion | `ML`, `sklearn`, `Python` | `Machine Learning`, `Scikit-learn`, `Python` | 0.33 / 1.0 / 0.33 / 0.50 | 1.0 / 1.0 / 1.0 / 1.0 | Key differentiator: synonyms expanded in taxonomy only |
| **EVAL005** | ESCO unmapped | `NumPy`, `Python` | `NumPy`, `Pandas` | 0.50 / 1.0 / 0.50 / 0.67 | 0.50 / 1.0 / 0.50 / 0.67 | Unmapped ESCO skills still match at canonical level |
| **EVAL006** | No overlap | `SQL`, `Git` | `Python`, `Machine Learning`, `Scikit-learn` | 0.0 / None / 0.0 / None | 0.0 / None / 0.0 / None | All required missing; Precision is `None` (0/0) |
| **EVAL007** | Empty candidate | `[]` | `Python`, `Pandas` | 0.0 / None / 0.0 / None | 0.0 / None / 0.0 / None | Edge case: empty candidate list |
| **EVAL008** | Unrecognized skill | `UnknownFramework`, `Python` | `Python`, `Machine Learning` | 0.50 / 1.0 / 0.50 / 0.67 | 0.50 / 1.0 / 0.50 / 0.67 | Unrecognized candidate skill excluded from matching, not forced |

---

## 7. Running Tests

### Run Issue #16 Skill Matching Baseline Tests
```powershell
.\.venv\Scripts\pytest Tests/AI/test_skill_matching_baselines.py -v
```

### Run Full AI Test Suite
```powershell
.\.venv\Scripts\pytest Tests/AI
```
