# M3 — Hybrid Skill Gap Detection

## 1. Overview

**Project:** Road2Hire  
**Module:** AI / Skill Gap Detection (M3)  
**Status:** Completed  
**Branch:** `main`

### Objective

Implement an explainable, reliable, and mathematically sound Hybrid Skill Gap Detection system that compares a candidate's normalized skills against the requirements of a selected target ESCO occupation.

The system determines:
1. Which required skills the candidate possesses (full matches).
2. Which skills the candidate partially satisfies through taxonomy hierarchy, related skills, or semantic proximity.
3. Which essential and optional skills are missing.
4. An overall explainable coverage score, computed with a configurable weighting (defaulting to 75% essential and 25% optional).

---

## 2. Architecture & Data Flow

```text
  CandidateProfile (or Resume PDF) + Target ESCO Occupation
                           │
                           ▼
          [1. Target Occupation Resolution]
          ESCOKnowledgeGraph.resolve_occupation_uri()
          Fetch target skills partitioned into:
            ├─ Essential Skills (N_E)
            └─ Optional Skills  (N_O)
                           │
                           ▼
          [2. Candidate Skill Normalization]
          Extract candidate skills, concept URIs, and embeddings (384-d).
          Isolate unmapped candidate skills.
                           │
                           ▼
          [3. Three-Tier Hybrid Matching Engine]
          ┌────────────────────────────────────────────────────────┐
          │ Tier 1: Exact / Normalized Match (Credit = 1.0)        │
          │         - Direct concept URI equality                  │
          │         - Normalized preferred or alternative label    │
          ├────────────────────────────────────────────────────────┤
          │ Tier 2: ESCO Knowledge Graph Relations                │
          │         - is_narrower_than (Credit = 0.75)             │
          │         - is_related_to (Credit = 0.70)                │
          │         - is_broader_than (Credit = 0.60)              │
          ├────────────────────────────────────────────────────────┤
          │ Tier 3: Semantic Similarity Matching                   │
          │         - Hard-negative filter (KNOWN_DISTINCT_PAIRS)  │
          │         - Hungarian bipartite global optimal matching  │
          │         - sim >= 0.82: Confirmed Match (Credit = 1.0)  │
          │         - 0.65 <= sim < 0.82: Partial (Credit=0.50*sim)│
          │         - sim < 0.65: Non-Match (Credit = 0.0)         │
          └────────────────────────────────────────────────────────┘
                           │
                           ▼
          [4. Skill Gap Categorization]
          ├─ matched_skills: Full matches with audit evidence
          ├─ partially_matched_skills: Partial matches with evidence
          ├─ missing_essential_skills: Unmatched essential skills
          ├─ missing_optional_skills: Unmatched optional skills
          ├─ unmapped_candidate_skills: Unmapped candidate skills
          └─ surplus_candidate_skills: Candidate skills not required
                           │
                           ▼
          [5. Explainable Hybrid Scoring & Reporting]
          Compute Essential, Optional, and Overall Coverage.
          Generate structured SkillGapReport.
```

---

## 3. Hybrid Matching Methodology

Matching is conducted with strict **one-to-one assignment** across candidate and required skill sets. Once a candidate skill is matched, it is removed from the candidate pool and cannot satisfy another requirement.

### Tier 1: Exact & Normalized Mapping (Credit = 1.0)
- Identifies identical concepts where candidate concept URI matches the target requirement concept URI.
- If unmapped by URI, evaluates normalized preferred labels and alternative labels in the ESCO taxonomy.
- Matched skills receive full credit ($1.0$).

### Tier 2: ESCO Knowledge Graph Relationships
Unmatched candidate skills with valid ESCO URIs are compared against remaining target skills via NetworkX graph traversal:
- **`is_narrower_than` (Credit = 0.75)**: The candidate possesses a more specialized skill than required (e.g., specific framework vs. general skill).
- **`is_related_to` (Credit = 0.70)**: The candidate has a conceptually related skill directly connected in the ESCO graph.
- **`is_broader_than` (Credit = 0.60)**: The candidate has broader domain knowledge covering the requirement.

### Tier 3: Semantic Similarity Matching
Remaining candidate skills and required skills are paired using Sentence Transformer embeddings (`all-MiniLM-L6-v2`, 384 dimensions):
- **Hard-Negative Guardrails**: Negative pairs such as `Java` vs `JavaScript`, `C` vs `C++`, `Rust` vs `Go` are blocked by `KNOWN_DISTINCT_PAIRS` and given a similarity of 0.0.
- **Global Optimal Assignment**: Solves the maximum-weight bipartite matching problem (Hungarian algorithm via `scipy.optimize.linear_sum_assignment`) to avoid greedy ordering bias.
- **Threshold Calibration**:
  - $\text{similarity} \ge 0.82$: Confirmed match (Credit = $1.0$).
  - $0.65 \le \text{similarity} < 0.82$: Partial match (Credit = $0.50 \times \text{similarity}$).
  - $\text{similarity} < 0.65$: Non-match (Credit = $0.0$, skill remains missing).

---

## 4. Scoring Formulation & Rules

Let:
- $E$ = set of essential skills required by the occupation ($N_E = |E|$).
- $O$ = set of optional skills recommended by the occupation ($N_O = |O|$).
- $c(s) \in [0.0, 1.0]$ = credit awarded to skill $s \in E \cup O$.

### Essential Skill Coverage:
$$S_E = \begin{cases} \frac{\sum_{s \in E} c(s)}{N_E} & \text{if } N_E > 0 \\ 1.0 & \text{if } N_E = 0 \end{cases}$$

### Optional Skill Coverage:
$$S_O = \begin{cases} \frac{\sum_{s \in O} c(s)}{N_O} & \text{if } N_O > 0 \\ \text{null} & \text{if } N_O = 0 \end{cases}$$

### Overall Skill Coverage:
By default, essential skills carry 75% weight and optional skills carry 25% weight:
$$S_{\text{overall}} = \begin{cases} S_E & \text{if } N_O = 0 \text{ or } S_O \text{ is null} \\ w_E \cdot S_E + w_O \cdot S_O & \text{otherwise} \end{cases}$$
where $w_E = 0.75$ and $w_O = 0.25$ (normalized to sum to 1.0).

### Edge Case Handlers
1. **Empty Candidate Profile (Freshers / No Skills)**:
   - Coverage scores are strictly $0.0$.
   - All essential and optional skills are listed under `missing_essential_skills` and `missing_optional_skills`.
2. **Occupations with Zero Optional Skills**:
   - `optional_skill_coverage_score` is reported as `null`.
   - `overall_skill_coverage_score` is driven 100% by essential skills, preventing division-by-zero or arbitrary score penalties.

### Non-Probabilistic Guardrail
> **Notice**: Skill coverage scores represent heuristic alignment between candidate skills and ESCO occupation requirements. They are **not** probabilities, hiring guarantees, or statistically validated predictors of job performance.

---

## 5. Structured Output Schema (`SkillGapReport`)

```json
{
  "target_occupation": {
    "uri": "http://data.europa.eu/esco/occupation/...",
    "preferred_label": "software developer",
    "description": "Software developers design, test...",
    "essential_skills_count": 25,
    "optional_skills_count": 18,
    "total_skills_count": 43
  },
  "overall_skill_coverage_score": 0.425,
  "essential_skill_coverage_score": 0.480,
  "optional_skill_coverage_score": 0.260,
  "scoring_weights": {
    "essential": 0.75,
    "optional": 0.25
  },
  "matched_skills": [
    {
      "tier": "exact",
      "candidate_skill": "Python",
      "candidate_uri": "http://data.europa.eu/esco/skill/4c5b2a62-...",
      "target_skill": "Python (computer programming)",
      "target_uri": "http://data.europa.eu/esco/skill/4c5b2a62-...",
      "target_skill_type": "essential",
      "graph_relationship": "exact_concept_match",
      "similarity_score": 1.0,
      "credit_assigned": 1.0,
      "explanation": "Exact match with required essential skill 'Python (computer programming)'."
    }
  ],
  "partially_matched_skills": [
    {
      "tier": "graph",
      "candidate_skill": "use scripting programming",
      "candidate_uri": "...",
      "target_skill": "computer programming",
      "target_uri": "...",
      "target_skill_type": "essential",
      "graph_relationship": "is_narrower_than",
      "similarity_score": 0.75,
      "credit_assigned": 0.75,
      "explanation": "Candidate skill 'use scripting programming' has an ESCO taxonomy relationship (is_narrower_than) with essential skill 'computer programming'."
    }
  ],
  "missing_essential_skills": [
    {
      "skill_uri": "...",
      "skill_label": "design database scheme",
      "relation_type": "essential",
      "skill_type": "skill/competence"
    }
  ],
  "missing_optional_skills": [
    {
      "skill_uri": "...",
      "skill_label": "use agile methodologies",
      "relation_type": "optional",
      "skill_type": "skill/competence"
    }
  ],
  "unmapped_candidate_skills": [],
  "surplus_candidate_skills": ["baking bread"],
  "matching_summary": {
    "total_candidate_skills": 5,
    "matched_skills_count": 2,
    "partially_matched_skills_count": 1,
    "missing_essential_skills_count": 22,
    "missing_optional_skills_count": 17,
    "unmapped_candidate_skills_count": 0,
    "surplus_candidate_skills_count": 1
  },
  "disclaimer": "Skill coverage scores represent a heuristic alignment..."
}
```

---

## 6. Pipeline Integration

The detector is accessible via:
1. **Direct detector interface**:
   ```python
   from AI.Skill_Gap import get_skill_gap_detector

   detector = get_skill_gap_detector()
   report = detector.detect_gap(candidate_profile, "software developer")
   ```
2. **Central Model interface**:
   ```python
   from AI.road2hire_model import Road2HireModel

   model = Road2HireModel()
   report = model.detect_skill_gap("path/to/resume.pdf", "software developer")
   ```
   *Note*: The central `Road2HireModel.predict()` output remains completely unmodified, ensuring 100% backward compatibility with M1 and M2 consumers.

---

## 7. Test Results

Comprehensive automated testing is implemented in `Tests/AI/test_skill_gap_detector.py`:
- Scoring formulas and weightings.
- Zero-credit handling for freshers.
- Zero-optional occupation handling.
- Exact match tier.
- Graph relation tier.
- Semantic similarity tier.
- Deceptive distinct pair rejection (`Java` vs `JavaScript`, `C` vs `C++`).
- Unmapped and surplus skill isolation.
- Strict one-to-one matching verification.
- Invalid occupation error handling.
- PDF resume end-to-end integration through `Road2HireModel`.
- Full regression testing across `Tests/AI/`.

**Test Suite Summary**:
- Total Tests Executed: **173 passed** in 281.80s.
- `Tests/AI/test_skill_gap_detector.py`: **12/12 passed**.
- Regressions: **0**.

---

## 8. Limitations & Future Improvements

1. **Static ESCO Relations**: ESCO graph relationships are static curated relations and may not capture all emerging open-source tool relationships.
2. **Polysemy in Embedding Space**: While guarded with hard-negative lists and bipartite matching, polysemous domain terms (e.g. "driver" in hardware vs. transportation) benefit from full context strings.
3. **Future Extension**: Learning path generation and course recommendations based directly on `missing_essential_skills` (Phase 5 / M4).

