# Road2Hire — AI/ML Pipeline Integration Guide & System Handover

**Document Version:** 1.0.0  
**Pipeline Version:** `3.0.0`  
**Target Milestone:** Phase 3 Handover to Backend Engineering  
**Primary Python Entry Point:** `Road2HirePipeline.run()` in [`AI/Pipeline/pipeline.py`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Pipeline/pipeline.py)  
**Schema Contract:** [`AI/Pipeline/pipeline_schema.py`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Pipeline/pipeline_schema.py)  
**CLI Interface:** [`AI/Pipeline/cli.py`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Pipeline/cli.py)  

---

## 1. Architectural Overview

The Road2Hire AI/ML pipeline delivers a production-grade, end-to-end career readiness and skill intelligence system. It unifies four core milestones into a single programmatic workflow:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       ROAD2HIRE AI/ML ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [Input Layer]                                                              │
│  └── Resume PDF (Single-column, multi-column, standard formatting)          │
│                                                                             │
│  [M2: Resume Intelligence & Skill Normalization]                            │
│  ├── PyMuPDF & pdfplumber Text Extraction                                   │
│  ├── Structural Section Detection (Experience, Education, Skills, Projects) │
│  ├── Aho-Corasick Trie Skill Extraction (99,676 ESCO canonical terms)       │
│  ├── Canonical ESCO Skill Normalization (URIs & preferred labels)           │
│  ├── Sentence-Transformers Semantic Embeddings (all-MiniLM-L6-v2)           │
│  └── Candidate Profile Assembly & Validation (Schema v1.1.0)                │
│                                                                             │
│  [M1 & M3: Knowledge Graph & Hybrid Skill Gap Detection]                    │
│  ├── ESCO Graph Occupation Matching (Ranked candidate occupations)          │
│  ├── Target Occupation Selection & Resolution (Strict canonical mapping)    │
│  ├── 3-Tier Hybrid Gap Detection (Exact, Hierarchical Graph, Semantic)      │
│  └── Personalized Knowledge Graph Construction (Candidate-Role Subgraph)    │
│                                                                             │
│  [M4 & M4.5: Career Readiness & SHAP Explainability]                        │
│  ├── Deterministic 9-Feature Extraction (Breadth, depth, tenure, projects)  │
│  ├── Empirical Out-of-Distribution (OOD) Detection (Bounds & Z-Scores)      │
│  ├── Multinomial Logistic Regression Prediction (Developing, Ready, NR)     │
│  └── Exact SHAP Attribution (LinearExplainer decomposition)                 │
│                                                                             │
│  [Delivery Layer]                                                           │
│  ├── 4-Phase Personalized Learning Roadmap Generation                       │
│  ├── Multi-Format Reporting (Structured JSON + GitHub-Flavored Markdown)    │
│  └── Stable Python Data Contract (UnifiedPipelineResult)                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Pipeline Execution Sequence

The pipeline executes through a verified 15-step sequence:

1. **Resume Input Validation:** Checks file existence, `.pdf` extension, and non-empty byte stream.
2. **Resume Text Extraction:** Extracts clean UTF-8 text and page metadata.
3. **Section Detection:** Identifies candidate sections using boundary-aware heading regex patterns.
4. **Candidate Profile Construction:** Assembles candidate contact information, education, experience, projects, and certifications.
5. **Skill Extraction:** Uses an Aho-Corasick Trie across 99,676 terms to extract exact and synonym mentions.
6. **ESCO Skill Normalization:** Maps extracted strings to canonical ESCO concept URIs and preferred labels.
7. **Occupation Recommendation:** Evaluates skill graph overlap to suggest top matching occupations.
8. **Target Occupation Selection:** Resolves user query (URI, title, or search term) to a validated canonical occupation.
9. **Hybrid Skill Gap Detection:** Compares candidate skills against essential and optional occupation requirements across 3 tiers.
10. **Personalized Knowledge Graph:** Generates an in-memory subgraph linking candidate credentials to target occupation skills.
11. **Career Readiness Prediction:** Extracts 9 structural profile signals and runs multinomial logistic regression inference.
12. **OOD Detection & Warnings:** Evaluates feature values against empirical training boundaries ($N=71$); emits warnings if extrapolating.
13. **SHAP Explanation Generation:** Computes exact feature attributions ($\phi_i$) for the predicted class.
14. **Personalized Learning Roadmap:** Generates a 4-phase prioritized learning curriculum with practical project milestones.
15. **Report Generation & Serialization:** Saves JSON and Markdown reports and returns the structured `UnifiedPipelineResult`.

---

## 3. Python Integration Interface (For Backend Developers)

Backend services (e.g. FastAPI route handlers or async background task workers) can import and execute the pipeline directly in Python using either the functional `process_resume(...)` interface or the object-oriented `get_pipeline()` singleton.

### Primary Function: `process_resume(...)`

```python
from pathlib import Path
from AI.Pipeline import (
    process_resume,
    UnifiedPipelineResult,
    ResumeValidationError,
    OccupationSelectionError,
    PipelineError,
)

# Mode A: Execution with an explicit target occupation
try:
    result: UnifiedPipelineResult = process_resume(
        resume_path="uploads/candidate_resume.pdf",
        target_occupation="data engineer",  # title, search string, or ESCO URI
        output_format="none",               # "none" avoids writing report files to disk
    )
except ResumeValidationError as e:
    # 400 Bad Request: missing file, non-PDF, 0-byte corrupt document
    print(f"Invalid resume file: {e}")
except OccupationSelectionError as e:
    # 422 Unprocessable Entity: target occupation invalid or missing.
    # e.suggested_occupations contains ranked recommendations to prompt the user
    print(f"Target occupation error: {e}")
    for occ in e.suggested_occupations[:5]:
        print(f" - {occ['occupation_label']} (Score: {occ['score']}, URI: {occ['occupation_uri']})")

# Mode B: Execution with automatic top-occupation resolution
result_auto = process_resume(
    resume_path="uploads/candidate_resume.pdf",
    target_occupation=None,
    auto_select_top_occupation=True,     # Auto-selects highest-scoring occupation
    output_format="none",
)

# Canonical JSON serialization for API responses (conforms to pipeline_output.schema.json)
api_response: dict = result.to_canonical_dict()
json_string: str = result.to_json(indent=2)
```

### Thread Safety & Resource Lifecycle

- **Thread-Safe Model Singletons:** `get_road2hire_model()` and `get_pipeline()` are protected with re-entrant thread locks (`threading.RLock`). They can be safely accessed concurrently across multi-threaded web worker threads (e.g. `run_in_threadpool` or gunicorn/uvicorn workers).
- **Zero Redundant Loading:** ESCO taxonomy, knowledge graph, and SentenceTransformer weights are initialized once in memory (~450MB total) and reused across all subsequent requests without reallocation.
- **Fast In-Memory Execution:** By specifying `output_format="none"`, disk I/O for Markdown and JSON report files is completely bypassed, keeping latency purely dedicated to compute.

---

## 4. Standardized Output Contract (`UnifiedPipelineResult`)

The returned object exposes 11 logical sections:

| # | Section | Key Field | Type | Description |
|:---:|:---|:---|:---|:---|
| **1** | **Metadata** | `status`<br>`pipeline_version`<br>`timestamp`<br>`execution_timings_seconds` | `str`<br>`str`<br>`str`<br>`dict[str, float]` | Overall execution health (`success`, `warning`, `error`), version, and stage timing breakdown. |
| **2** | **Candidate Profile** | `candidate_profile` | `dict[str, Any]` | Extracted contact info, education, experience, projects, and certifications (Schema v1.1.0). |
| **3** | **Skills** | `extracted_skills`<br>`esco_mappings` | `list[dict]`<br>`list[dict]` | Raw skill text occurrences and canonical ESCO taxonomy mapped concepts with concept URIs. |
| **4** | **Recommendations** | `occupation_matches` | `list[dict]` | Top ranked ESCO occupations based on candidate skill overlap. |
| **5** | **Target Occupation** | `selected_occupation` | `SelectedOccupation` | Confirmed target role (`occupation_uri`, `occupation_label`, `match_score`, `resolution_source`). |
| **6** | **Skill Gap Analysis** | `skill_gap_analysis` | `dict[str, Any]` | `overall_skill_coverage_score`, `matched_skills`, `partially_matched_skills`, `missing_essential_skills`, `missing_optional_skills`. |
| **7** | **Career Readiness** | `readiness_prediction` | `ReadinessPredictionData` | `predicted_class`, `class_probabilities`, `is_ood`, `ood_warnings`, `feature_values`, `limitations`. |
| **8** | **SHAP Explanation** | `shap_explanation` | `SHAPExplanationData` | `target_class_explained`, `base_value`, `top_positive_factors`, `top_negative_factors`, `waterfall_steps`, `global_importance_ranking`. |
| **9** | **Personalized KG** | `personalized_graph_summary` | `dict[str, Any]` | Node count, edge count, relation breakdown connecting candidate credentials to target occupation. |
| **10** | **Learning Roadmap** | `learning_roadmap` | `LearningRoadmap` | Prioritized 4-phase learning milestones (`total_roadmap_skills`, `total_estimated_weeks`, `phases`, `disclaimers`). |
| **11** | **Warnings & Errors** | `warnings`<br>`errors`<br>`report_paths` | `list[str]`<br>`list[str]`<br>`dict[str, str]` | Non-fatal diagnostics, recoverable issues, and persisted file paths on disk. |

---

## 5. Model Loading, Resource Requirements & Caching

### Memory Footprint & Loading Behavior
1. **ESCO Taxonomy (Heavy):** ~100MB RAM. Initialised once at startup and reused via module-level singleton `get_road2hire_model()`.
2. **ESCO Knowledge Graph (Heavy):** ~200MB RAM. In-memory NetworkX directed multi-graph connecting 3,008 occupations and 13,890 skills.
3. **SentenceTransformer Embeddings (GPU/CPU):** ~150MB RAM. Model `sentence-transformers/all-MiniLM-L6-v2`. Eagerly initialized and cached.
4. **M4 Readiness Pipeline & SHAP Explainer (Light):** ~15MB RAM. Lazily loaded upon first inference and cached in the `Road2HirePipeline` instance.

> [!TIP]
> **Production Best Practice:** Pre-warm the singleton model during application startup (e.g. in FastAPI lifespan handler):
> ```python
> @asynccontextmanager
> async def lifespan(app: FastAPI):
>     from AI.road2hire_model import get_road2hire_model
>     get_road2hire_model()  # Cold start occurs here once
>     yield
> ```

---

## 6. Readiness Limitations & Out-of-Distribution (OOD) Guidelines

Backend developers must adhere to the following governance rules when displaying readiness predictions:

1. **Model Is Exploratory ($N=71$):**
   The supervised classifier was trained on an initial pilot cohort of 71 candidate records. While methodologically rigorous (repeated stratified cross-validation), it is an exploratory baseline.
2. **Probabilities Are Uncalibrated Heuristics:**
   Softmax output values from regularized multinomial logistic regression reflect relative ranking across classes; they are **not** certified statistical probabilities of candidate employment.
3. **Handling OOD Flags in UI:**
   When `readiness_prediction.is_ood == True`, backend APIs must include the `ood_warnings` in the response and the frontend must display an advisory banner:
   > *"Notice: This resume contains feature counts (e.g. skill breadth) exceeding the model's training range. Predicted readiness represents a statistical extrapolation."*
4. **Coupled Presentation:**
   Always display the M4 readiness prediction **alongside** the M3 skill gap coverage score (`overall_skill_coverage_score`). Never present career readiness in isolation.

---

## 7. Error Handling & Structured Failure Contracts

When pipeline operations fail, the exception types map directly to standard HTTP status codes:

| Exception Class | HTTP Status Equivalent | Standard Error Code | Trigger Condition | Recommended Backend Action |
|:---|:---:|:---|:---|:---|
| `ResumeValidationError` | `400 Bad Request` | `RESUME_NOT_FOUND`<br>`INVALID_FILE_TYPE`<br>`EMPTY_OR_CORRUPT_DOCUMENT` | File does not exist, file is not `.pdf`, 0-byte corrupt file, or unreadable binary. | Return error message to user; prompt for valid PDF upload. |
| `OccupationSelectionError` | `400 Bad Request` | `OCCUPATION_NOT_FOUND`<br>`OCCUPATION_SELECTION_REQUIRED` | Target occupation query could not be resolved to any ESCO occupation, or query omitted in non-interactive mode. | Return top suggested occupations provided in `ranked_matches` to client for selection. |
| `PipelineError` | `500 Server Error` | `MODEL_ARTIFACT_MISSING`<br>`PIPELINE_EXECUTION_ERROR` | Unexpected internal exception or missing model weights during pipeline processing. | Log full traceback; return generic processing error to client. |

### Helper Function for Backend Error Payloads
Backend endpoints can construct error responses conforming strictly to [`pipeline_error.schema.json`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Pipeline/schemas/pipeline_error.schema.json) using the built-in helper:

```python
from AI.Pipeline import create_error_response

# Construct structured JSON error payload
error_payload = create_error_response(
    code="OCCUPATION_NOT_FOUND",
    message="Target occupation 'quantum chef' could not be resolved to any canonical ESCO concept.",
    stage="occupation_resolution",
    details={"query": "quantum chef"},
    recoverable=True,
    warnings=["Suggestions available in previous step."],
)
```

Recoverable issues (such as SHAP calculation failure or OCR notification) do **not** raise exceptions; they append descriptive messages to `result.warnings` and set `result.status = "warning"`.

---

## 8. Database Architecture & PostgreSQL JSONB Guidelines

When persisting pipeline outputs in PostgreSQL, the backend service should partition relational indexable columns from semi-structured JSONB payloads:

| Field / Section | Storage Type | Recommended Column Name | Justification |
|:---|:---|:---|:---|
| `candidate_profile.candidate.name` | `VARCHAR(255)` | `candidate_name` | Fast search, filtering, and sorting in candidate tables. |
| `candidate_profile.candidate.email`| `VARCHAR(255)` | `candidate_email`| Unique constraint, candidate identity lookup. |
| `target_occupation.occupation_uri`  | `TEXT` | `target_occupation_uri` | Foreign key / index to filter candidates by target role. |
| `target_occupation.occupation_label`| `VARCHAR(255)` | `target_occupation_title` | Display on job application cards without deserializing JSONB. |
| `skill_gap.overall_skill_coverage_score` | `NUMERIC(5, 4)` | `overall_skill_coverage` | Fast filtering (`WHERE overall_skill_coverage >= 0.70`). |
| `readiness.predicted_class`        | `VARCHAR(50)` | `readiness_class` | Fast indexing (`Developing`, `Job Ready`, `Not Ready`). |
| `readiness.is_ood`                 | `BOOLEAN` | `is_ood` | Flagging anomalous profiles for review. |
| `candidate_profile` (full)         | `JSONB` | `profile_data` | Preserves nested education, experience, and project trees. |
| `skill_gap` (full)                 | `JSONB` | `skill_gap_data` | Preserves 3-tier matched, partial, and missing skill lists. |
| `readiness` (full)                 | `JSONB` | `readiness_data` | Preserves heuristic probabilities and OOD feature diagnostics. |
| `explanations` (full)              | `JSONB` | `shap_explanation_data` | Powers interactive waterfall and attribution visualizations. |
| `learning_roadmap` (full)          | `JSONB` | `roadmap_data` | Renders 4-phase learning milestones in user dashboard. |

---

## 9. System Responsibilities Matrix

| Capability / Concern | AI/ML Pipeline Responsibility | Backend Service Responsibility |
|:---|:---:|:---:|
| **Resume Text & Skill Extraction** | **YES** | NO |
| **ESCO Normalization & Concept Matching** | **YES** | NO |
| **Skill Gap & Readiness Calculation** | **YES** | NO |
| **SHAP Explanation Decomposition** | **YES** | NO |
| **Learning Roadmap Generation** | **YES** | NO |
| **User Authentication & Auth0/JWT** | NO | **YES** |
| **File Upload Storage (S3 / Local)** | NO | **YES** |
| **Database Persistence (PostgreSQL)** | NO | **YES** |
| **API Rate Limiting & Background Tasks** | NO | **YES** |
| **Email Notifications & Webhooks** | NO | **YES** |

---

## 10. Sample Sanitized Canonical JSON Output (v1.0.0)

```json
{
  "status": "success",
  "pipeline_version": "3.0.0",
  "timestamp": "2026-11-07T14:10:00.000000",
  "source_file": "uploads/sample_resume.pdf",
  "page_count": 1,
  "extraction_status": "success",
  "candidate_profile": {
    "candidate_info": {
      "name": "Alex Morgan",
      "email": "alex.morgan@example.com",
      "phone": "+1-555-0199",
      "location": "San Francisco, CA"
    },
    "education": [
      {
        "degree": "Bachelor of Science",
        "field_of_study": "Computer Science",
        "institution": "University of California"
      }
    ],
    "experience": [
      {
        "job_title": "Software Engineer",
        "organization": "Acme Corp",
        "responsibilities": ["Developed backend data microservices in Python and SQL"]
      }
    ]
  },
  "selected_occupation": {
    "occupation_uri": "http://data.europa.eu/esco/occupation/2079755f-d809-49e6-8037-4de6180e54c0",
    "occupation_label": "data engineer",
    "match_score": 14,
    "resolution_source": "suggestion"
  },
  "skill_gap_analysis": {
    "overall_skill_coverage_score": 0.4286,
    "essential_skill_coverage_score": 0.3846,
    "optional_skill_coverage_score": 0.5000,
    "matched_skills": [
      {"candidate_skill": "Python", "occupation_skill": "Python (computer programming)", "match_type": "exact"}
    ],
    "missing_essential_skills": [
      {"skill_label": "data engineering", "skill_type": "skill/competence", "skill_uri": "http://data.europa.eu/esco/skill/..."}
    ]
  },
  "readiness_prediction": {
    "predicted_class": "Developing",
    "class_probabilities": {
      "Developing": 0.7241,
      "Job Ready": 0.2415,
      "Not Ready": 0.0344
    },
    "is_ood": false,
    "ood_warnings": [],
    "model_version": "0.1.0-exploratory",
    "training_sample_count": 71
  },
  "shap_explanation": {
    "target_class_explained": "Developing",
    "base_value": 0.4497,
    "top_positive_factors": [
      {
        "feature": "skills_count",
        "display_name": "Skills Count",
        "feature_value": 6.0,
        "contribution": 0.6541
      }
    ],
    "top_negative_factors": [],
    "human_readable_summary": "The model predicted 'Developing' with 72.4% confidence."
  },
  "learning_roadmap": {
    "target_occupation_title": "data engineer",
    "total_roadmap_skills": 8,
    "total_estimated_weeks": "12 – 22 Weeks",
    "phases": [
      {
        "phase_number": 1,
        "phase_name": "Phase 1: Foundational Competencies & Core Knowledge",
        "estimated_weeks": "2 – 4 Weeks",
        "items": []
      }
    ]
  },
  "warnings": [],
  "errors": []
}
```
