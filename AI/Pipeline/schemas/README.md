# Road2Hire — AI/ML Pipeline JSON Schemas

**Schema Specification:** Draft-07  
**Schema Version:** `1.0.0`  
**Package:** `AI/Pipeline/schemas/`  

---

## 1. Overview

This directory provides versioned JSON Schema specifications governing the interface contracts between the Road2Hire AI/ML pipeline and backend service layers (e.g. FastAPI route handlers, task workers, and persistent stores).

- [`pipeline_output.schema.json`](AI/Pipeline/schemas/pipeline_output.schema.json): Standard canonical output contract for successful pipeline runs.
- [`pipeline_error.schema.json`](AI/Pipeline/schemas/pipeline_error.schema.json): Structured error payload contract for pipeline exceptions and validation failures.

---

## 2. Logical Sections of the Pipeline Output

The canonical output contract (`pipeline_output.schema.json`) defines 10 core logical sections:

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

The error contract (`pipeline_error.schema.json`) standardizes failures across all stages:

| Error Code | Stage | Typical Trigger | Recoverable |
|:---|:---|:---|:---:|
| `RESUME_NOT_FOUND` | `input_validation` | File path does not exist on disk | No |
| `INVALID_FILE_TYPE` | `input_validation` | File extension is not `.pdf` | No |
| `EMPTY_OR_CORRUPT_DOCUMENT` | `input_validation` | 0-byte or corrupted unparseable PDF stream | No |
| `TEXT_EXTRACTION_FAILED` | `resume_extraction` | Parser fails to extract any readable text | No |
| `NO_SKILLS_DETECTED` | `skill_extraction` | Zero skills detected in resume content | Yes (advisory) |
| `OCCUPATION_NOT_FOUND` | `occupation_resolution` | Target title cannot be resolved to any ESCO occupation | Yes (pass valid title) |
| `OCCUPATION_SELECTION_REQUIRED` | `occupation_resolution` | Target occupation query omitted in non-interactive mode | Yes (select suggestion) |
| `MODEL_ARTIFACT_MISSING` | `readiness_prediction` | Model weights or metadata files missing from disk | No |
| `READINESS_INFERENCE_FAILED` | `readiness_prediction` | Unexpected failure during feature extraction or scoring | No |
| `SHAP_EXPLANATION_FAILED` | `shap_explanation` | Numerical instability during SHAP decomposition | Yes (recoverable warning) |
| `PIPELINE_EXECUTION_ERROR` | `reporting` / generic | Unhandled runtime exception in pipeline | No |

---

## 4. Contract Rules & Conventions

1. **Required vs. Optional:** Core logical sections are always present in the response dictionary. If a stage is skipped or encounters a recoverable error (e.g. SHAP explainer failure), its field is set to `null` and a descriptive message is appended to `warnings`.
2. **Collections:** Arrays are returned as empty collections `[]` (never `null`) when no items exist.
3. **ESCO URIs:** Always represented as fully-qualified canonical HTTP URIs (e.g. `http://data.europa.eu/esco/occupation/...`).
4. **Timestamps:** ISO-8601 strings in UTC or local timezone format (e.g. `2026-11-07T14:10:00.000000`).
5. **Float Precision:** Coverage scores are normalized in `[0.0, 1.0]`; model probabilities are normalized to sum to `1.0`; timings are rounded to 4 decimal places.
6. **No Equivalence Claim:** Probabilities from the logistic regression classifier are uncalibrated heuristics; they must never be presented as validated real-world qualification percentages.
