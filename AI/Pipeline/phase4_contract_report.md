# Road2Hire — Phase 4: AI/ML Output JSON Schema & Backend Contract Completion Report

**Milestone:** Phase 4 — Finalize AI/ML Output JSON Schema & Backend Contract  
**Status:** Complete  
**Date:** November 2026  
**JSON Output Schema:** [`AI/Pipeline/schemas/pipeline_output.schema.json`](AI/Pipeline/schemas/pipeline_output.schema.json)  
**JSON Error Schema:** [`AI/Pipeline/schemas/pipeline_error.schema.json`](AI/Pipeline/schemas/pipeline_error.schema.json)  
**Contract Documentation:** `Docs/Archive/AI_ML_Output_Contract.md`
**Handover Guide:** `Docs/Archive/AI_ML_Pipeline_Integration_Guide.md`
**Schema Test Suite:** `Tests/AI/test_pipeline_schema_contract.py`  

---

## 1. Executive Summary

Milestone Phase 4 finalized a consistent, versioned JSON output interface contract for the Road2Hire AI/ML pipeline. The contract enables backend engineers (e.g. building FastAPI services and database schemas) to integrate with the pipeline without needing to understand or modify internal AI/ML dependencies (such as Aho-Corasick Trie matching, PyMuPDF parsers, SentenceTransformer embeddings, or SHAP linear game-theoretic decompositions).

All 10 logical sections of the AI/ML output were standardized, formal JSON Schema Draft-07 contracts were authored, defensive error payloads were specified, and 21 dedicated automated schema validation tests were added.

The complete AI test suite (344 tests) passed with 100% success.

---

## 2. Standardized JSON Output Contract (10 Logical Sections)

Conforming to [`AI/Pipeline/schemas/pipeline_output.schema.json`](AI/Pipeline/schemas/pipeline_output.schema.json):

1. **`metadata`**: Schema and pipeline versions, overall execution status (`success`, `warning`, `error`), ISO-8601 timestamp, source document path, page count, extraction status, and stage-by-stage execution durations.
2. **`candidate_profile`**: Structured candidate profile conforming to Schema v1.1.0 (`candidate`, `education`, `experience`, `projects`, `certifications`).
3. **`skills`**: Extracted skill mentions with character offsets and canonical ESCO taxonomy mappings (`ESCO_Skill_Id`, `ESCO_Skill_Name`, `confidence`).
4. **`occupation_recommendations`**: Ranked list of ESCO occupations based on knowledge graph overlap scoring.
5. **`target_occupation`**: Resolved canonical target occupation concept (`occupation_uri`, `occupation_label`, `resolution_source`).
6. **`skill_gap`**: Hybrid 3-tier skill gap analysis metrics (`overall_skill_coverage_score`, `essential_skill_coverage_score`, `optional_skill_coverage_score`, matched, partial, missing, and surplus skills).
7. **`readiness`**: Supervised career readiness prediction (`predicted_class`, heuristic uncalibrated probabilities, `is_ood`, `ood_warnings`, model version, training sample count, and limitations).
8. **`explanations`**: SHAP feature attributions (`target_class_explained`, base value, top positive/negative factors, cumulative waterfall steps, and global macro feature importance).
9. **`knowledge_graph`**: Graph topology summary metrics (node count, edge count, node/edge type breakdown).
10. **`learning_roadmap`**: Personalized 4-phase learning roadmap (Foundational, Core, Applied, Specialization) with practical portfolio projects and governance disclaimers.

In addition, top-level arrays `warnings` and `errors` capture diagnostic notices and fatal failure logs, while `report_paths` links to generated disk artifacts.

---

## 3. Standardized Error Contract

Conforming to [`AI/Pipeline/schemas/pipeline_error.schema.json`](AI/Pipeline/schemas/pipeline_error.schema.json):

Structured error responses are generated via [`create_error_response()`](AI/Pipeline/pipeline_schema.py):

| Error Code | Stage | Description | Recoverable |
|:---|:---|:---|:---:|
| `RESUME_NOT_FOUND` | `input_validation` | Resume file path does not exist on disk | No |
| `INVALID_FILE_TYPE` | `input_validation` | File extension is not `.pdf` | No |
| `EMPTY_OR_CORRUPT_DOCUMENT` | `input_validation` | 0-byte or corrupted unparseable PDF stream | No |
| `TEXT_EXTRACTION_FAILED` | `resume_extraction` | Parser fails to extract any readable text | No |
| `NO_SKILLS_DETECTED` | `skill_extraction` | Zero skills detected in resume content | Yes |
| `OCCUPATION_NOT_FOUND` | `occupation_resolution` | Target title cannot be resolved to any ESCO occupation | Yes |
| `OCCUPATION_SELECTION_REQUIRED` | `occupation_resolution` | Target occupation query omitted in non-interactive mode | Yes |
| `MODEL_ARTIFACT_MISSING` | `readiness_prediction` | Model weights or metadata files missing from disk | No |
| `READINESS_INFERENCE_FAILED` | `readiness_prediction` | Unexpected failure during feature extraction or scoring | No |
| `SHAP_EXPLANATION_FAILED` | `shap_explanation` | Numerical instability during SHAP decomposition | Yes |
| `PIPELINE_EXECUTION_ERROR` | `reporting` / generic | Unhandled runtime exception in pipeline | No |

---

## 4. Pipeline Schema Enhancements

In [`AI/Pipeline/pipeline_schema.py`](AI/Pipeline/pipeline_schema.py):
1. **`to_canonical_dict()`:** Returns strictly the 10-section canonical output contract.
2. **`to_dict(canonical=False)`:** Default mode returns a merged dictionary with both canonical logical sections and legacy top-level keys for 100% backward compatibility with existing tests and CLI scripts.
3. **`to_json(indent=2, canonical=False)`:** Formats either canonical or backward-compatible dictionaries to JSON strings.
4. **`create_error_response(...)`:** Standalone factory function generating schema-compliant error payloads.

---

## 5. Contract Rules & Governance Invariants

1. **Uncalibrated Probabilities:** Heuristic probabilities from multinomial logistic regression ($N=71$) reflect class ranking under priors; they are never described as calibrated real-world qualification percentages.
2. **Skill Coverage Distinctness:** The M3 coverage score measures taxonomy overlap against official ESCO definitions, distinct from hiring probability or candidate career readiness.
3. **OOD Detection:** When `is_ood == True`, explicit notices describe which features (e.g. `skills_count > 14.0`) exceed training bounds.
4. **Collections vs Nulls:** Empty collections are always returned as empty arrays `[]` (never `null`).
5. **Canonical URIs:** All ESCO concepts preserve their official European Commission HTTP URIs.

---

## 6. Test Suite Execution & Verification

- **Command:** `.venv\Scripts\python.exe -m pytest Tests/AI -v`
- **Total Tests Collected:** 344
- **Passed:** **344 passed**
- **Failed:** 0
- **Pass Rate:** **100.0%**
- **New Schema Validation Tests:** 21 tests in `Tests/AI/test_pipeline_schema_contract.py` passing.

---

## 7. Deliverables & Created Files

1. **Output Schema:** [`AI/Pipeline/schemas/pipeline_output.schema.json`](AI/Pipeline/schemas/pipeline_output.schema.json)
2. **Error Schema:** [`AI/Pipeline/schemas/pipeline_error.schema.json`](AI/Pipeline/schemas/pipeline_error.schema.json)
3. **Schema Architecture Guide:** [`AI/Pipeline/schemas/README.md`](AI/Pipeline/schemas/README.md)
4. **Contract Documentation & Examples:** `Docs/Archive/AI_ML_Output_Contract.md`
5. **Backend Handover Guide:** `Docs/Archive/AI_ML_Pipeline_Integration_Guide.md`
6. **Schema Validation Tests:** `Tests/AI/test_pipeline_schema_contract.py`
7. **Pipeline Schema Implementation:** [`AI/Pipeline/pipeline_schema.py`](AI/Pipeline/pipeline_schema.py)
8. **Phase 4 Completion Report:** [`AI/Pipeline/phase4_contract_report.md`](AI/Pipeline/phase4_contract_report.md)
