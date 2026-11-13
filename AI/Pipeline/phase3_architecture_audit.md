# Milestone Phase 3 — End-to-End AI/ML Pipeline Architecture Audit

**Status:** Completed  
**Pipeline Module:** [`AI/Pipeline/`](AI/Pipeline)  
**Central Pipeline Orchestrator:** [`AI/Pipeline/pipeline.py`](AI/Pipeline/pipeline.py)  
**Public Python Interface:** `Road2HirePipeline.run(resume_path, target_occupation=None)`  
**Unified Output Contract:** [`AI/Pipeline/pipeline_schema.py`](AI/Pipeline/pipeline_schema.py)  

---

## 1. Executive Summary

Milestone Phase 3 finalizes the complete, end-to-end Road2Hire AI/ML pipeline. The architecture unifies all capabilities developed across Milestones M1 through M4:
- **M1 (Knowledge Graph):** ESCO graph traversal, canonical concepts, hierarchy, and relationship extraction.
- **M2 (Resume Intelligence):** Resume text extraction, section detection, Aho-Corasick Trie skill extraction across 99,676 ESCO terms, canonical skill normalization, semantic embeddings, and candidate profile assembly.
- **M3 (Skill Gap Detection & Personalized Graph):** Hybrid 3-tier skill gap matching (exact, graph hierarchical, semantic similarity), coverage scoring, and candidate personalized knowledge graph construction.
- **M4 & M4.5 (Career Readiness & Explainability):** Supervised career readiness classification, empirical Out-of-Distribution (OOD) detection, and closed-form SHAP feature attribution.
- **Delivery Orchestration:** Target occupation resolution, 4-phase personalized learning roadmap generation, CLI interface, and multi-format report generation (JSON and Markdown).

This audit evaluates the integrity, sequence, error handling, and data contracts across all pipeline stages.

---

## 2. End-to-End Pipeline Stage Verification

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       ROAD2HIRE END-TO-END WORKFLOW                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [Stage 1: Input Validation]                                                │
│  Resume PDF Path -> File existence, extension (.pdf), and readability       │
│                                                                             │
│  [Stage 2: Resume Intelligence (M1 & M2)]                                   │
│  ├── PDF Text Extraction (PyMuPDF / pdfplumber fallback)                    │
│  ├── Heading & Section Segmentation (Experience, Education, Skills, Proj)   │
│  ├── Skill Extraction (Aho-Corasick Trie over 99,676 ESCO terms)            │
│  ├── ESCO Skill Normalization (Preferred labels & concept URIs)             │
│  ├── Semantic Skill Embeddings (MiniLM-L6-v2)                               │
│  ├── Knowledge Graph Occupation Matching (Ranked candidate occupations)     │
│  └── Candidate Profile Assembly & Validation (Schema v1.1.0)                │
│                                                                             │
│  [Stage 3: Target Occupation Resolution]                                    │
│  Explicit Query / CLI Argument / Ranked Match -> Resolved SelectedOcc       │
│  (Concept URI + Canonical Label; strictly no silent arbitrary substitutions)│
│                                                                             │
│  [Stage 4: Hybrid Skill Gap Detection (M3)]                                 │
│  Candidate Skills vs. Target Occupation Essential & Optional Requisitions   │
│  (Tier 1: Exact, Tier 2: Graph Parent/Child, Tier 3: MiniLM-L6-v2 Semantic)│
│                                                                             │
│  [Stage 5: Personalized Knowledge Graph (M3)]                               │
│  Sub-graph construction connecting candidate to target occupation & skills  │
│                                                                             │
│  [Stage 6: Supervised Career Readiness & OOD Detection (M4)]                │
│  ├── Deterministic 9-feature extraction from candidate profile evidence     │
│  ├── Empirical Out-of-Distribution (OOD) Detection against N=71 bounds      │
│  └── Multinomial Logistic Regression Inference (Developing, Job Ready, NR)  │
│                                                                             │
│  [Stage 7: SHAP Explainability (M4.5)]                                      │
│  LinearExplainer decomposition (Base Intercept + Feature Attributions)     │
│                                                                             │
│  [Stage 8: Personalized Learning Roadmap]                                   │
│  4-Phase Prioritized Roadmap (Foundational, Core, Projects, Optional)       │
│                                                                             │
│  [Stage 9: Report Generation & Python Return Contract]                     │
│  Structured UnifiedPipelineResult -> JSON export & Markdown report          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Audit Matrix

| Pipeline Stage | Module Source | Input Contract | Output Contract | Verification Status | Notes / Safeguards |
|:---|:---|:---|:---|:---:|:---|
| **1. Resume Input Validation** | `AI/Pipeline/pipeline.py` | `Path \| str` | Validated `Path` | **PASS** | Rejects non-existent files and non-PDF extensions with `ResumeValidationError`. |
| **2. Text Extraction** | `AI/Resume_Extraction/` | PDF file | Raw text, page count | **PASS** | Validates extraction status (`success` vs `needs_ocr`). |
| **3. Section Detection** | `AI/Candidate_Profile/` | Raw text | Segmented sections dict | **PASS** | Robust regex headings for Experience, Education, Skills, Projects. |
| **4. Skill Extraction** | `AI/Skill_Extraction/` | Resume sections | Mapped raw skill terms | **PASS** | Aho-Corasick Trie matching over 99,676 canonical terms. |
| **5. ESCO Normalization** | `AI/Skill_Normalization/` | Raw skill terms | ESCO URIs & labels | **PASS** | Resolves preferred and alt labels; preserves canonical concept URIs. |
| **6. Profile Assembly** | `AI/Candidate_Profile/` | Structured blocks | CandidateProfile v1.1.0 | **PASS** | Validated with `profile_validator`; extracts candidate contact info. |
| **7. Occupation Ranking** | `AI/road2hire_model.py` | Mapped skills | Ranked occupation list | **PASS** | Ranks by essential & optional overlap via ESCO graph. |
| **8. Target Occupation Resolution** | `AI/Pipeline/target_occupation_selector.py` | Query + Ranked matches | `SelectedOccupation` | **PASS** | Matches by URI, exact label, or substring; errors if unresolvable. Never substitutes arbitrary defaults. |
| **9. Skill Gap Analysis** | `AI/Skill_Gap/` | Profile + Target URI | `SkillGapReport` dict | **PASS** | 3-tier hybrid matching; calculates overall, essential, and optional coverage. |
| **10. Personalized KG** | `AI/Knowledge_Graph/` | Profile + Gap report | `PersonalizedKnowledgeGraph` | **PASS** | Emits node/edge summaries and subgraphs linking candidate to target role. |
| **11. Readiness Prediction** | `AI/Readiness_Model/` | Structured evidence | `ReadinessPredictionData` | **PASS** | Multinomial Logistic Regression over 9 profile features. |
| **12. OOD Detection** | `AI/Readiness_Model/ood_detector.py` | 9-feature dict | `OODDetectionResult` | **PASS** | Flags features exceeding empirical bounds ($N=71$) without mutating data. |
| **13. SHAP Explainability** | `AI/Readiness_Model/shap_explainer.py` | Evidence + Target class | `SHAPExplanationData` | **PASS** | Exact mathematical attribution; efficiency axiom verified ($\le 10^{-6}$). |
| **14. Learning Roadmap** | `AI/Pipeline/roadmap_generator.py` | Gap report + Target role | `LearningRoadmap` | **PASS** | 4-phase structured curriculum with disclaimers and practical projects. |
| **15. Report Generation** | `AI/Pipeline/report_generator.py` | `UnifiedPipelineResult` | Markdown & JSON files | **PASS** | Writes artifacts to `Outputs/<candidate_dir>/`; clean JSON serialization. |

---

## 4. Confirmed Strengths & Existing Functionality

1. **Eager & Reusable Resource Caching:**
   - The heavy resources (ESCO taxonomy with 99,676 skill terms, ESCO knowledge graph, and `SentenceTransformer` embeddings) are initialised once via `get_road2hire_model()` and cached globally. Subsequent pipeline executions avoid cold-start overhead.
   - The M4 readiness model (`readiness_classifier_pipeline.joblib`) and SHAP explainer are lazily loaded on first inference and cached in `Road2HirePipeline`.
2. **Strict Non-Destructive OOD Detection:**
   - Feature values are never clamped or altered. Out-of-distribution flags (`is_ood=True`) and warning notices are surfaced transparently in JSON schemas, CLI summaries, and Markdown reports.
3. **Target Occupation Propagation Integrity:**
   - The resolved `SelectedOccupation` (concept URI and preferred label) is consistently passed to the M3 Skill Gap Detector, Personalized Knowledge Graph, Learning Roadmap Generator, and Report Generator.
4. **Data Leakage & Anti-Circularity Safeguards:**
   - The M4 readiness model operates strictly on 9 profile depth features, completely excluding candidate identifiers, PII, and human rubric sub-ratings.

---

## 5. Identified Integration Gaps & Improvements (Addressed in Phase 3)

1. **Overall Pipeline Status Property:**
   - While `extraction_status` captured PDF text extraction status, `UnifiedPipelineResult` lacked an explicit top-level `status` (`success`, `warning`, `error`) summarizing overall pipeline health.
   - *Improvement:* Added `status: Literal["success", "warning", "error"]` to `UnifiedPipelineResult` and serialized in `to_dict()`.
2. **Convenience JSON Serialization Helper:**
   - Backend consumers often require a direct JSON string without manually invoking `json.dumps(result.to_dict())`.
   - *Improvement:* Added `to_json(indent=2)` directly on `UnifiedPipelineResult`.
3. **Global SHAP Feature Importance Pass-Through:**
   - Global feature rankings from `AI/Readiness_Model/saved_models/global_shap_importance.json` were calculated during model training but not formally embedded in `SHAPExplanationData`.
   - *Improvement:* Added `global_importance_ranking` field to `SHAPExplanationData` schema and populated it during pipeline execution.
4. **Zero-Gap Roadmap Edge Case:**
   - When a candidate's profile covers 100% of target occupation skills (or has 0 missing skills), the roadmap generator hardcoded `"12 – 22 Weeks"`.
   - *Improvement:* Handled zero-gap condition explicitly to output `"0 Weeks (Core requirements covered)"` with tailored congratulatory guidance.
5. **Robust Independent Python Entry Point:**
   - Ensured `Road2HirePipeline.run()` can be imported and executed completely independently of the CLI, returning a structured Python dataclass with clear exceptions on failure.

---

## 6. Audit Conclusion

The Road2Hire pipeline architecture is coherent, modular, and methodologically sound. All 15 execution steps are connected with verified input/output contracts. With the standardization improvements identified above, the pipeline is ready for backend integration handover.
