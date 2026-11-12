# Road2Hire — 05: AI/ML Output JSON Contract and Backend Integration Guide

**Document Version:** 1.0.0  
**Specification Version:** 1.0.0  
**Pipeline Engine Version:** 3.0.0  
**Status:** Completed & Validated  
**Module:** Public Python Interface, Schema Contracts & Backend Wiring  
**Formal Schemas:** [`AI/Pipeline/schemas/pipeline_output.schema.json`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Pipeline/schemas/pipeline_output.schema.json), [`AI/Pipeline/schemas/pipeline_error.schema.json`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Pipeline/schemas/pipeline_error.schema.json)  

---

## 1. Executive Summary & Purpose

This document defines the formal, versioned interface between the Road2Hire AI/ML pipeline and backend service layers (such as FastAPI web services, Celery asynchronous workers, and PostgreSQL persistence).

Backend developers can safely integrate with the AI/ML module through the stable Python API and Draft-07 JSON Schemas without needing to inspect or modify internal ML implementations (such as PyMuPDF stream parsers, Aho-Corasick Trie traversals, SentenceTransformer embeddings, or SHAP linear game-theoretic decompositions).

---

## 2. Public Python Integration Interface

The backend application imports entry points directly from `AI.Pipeline`:

```python
from AI.Pipeline import process_resume, get_pipeline, Road2HirePipeline
```

### 2.1 Primary Entry Point: `process_resume()`

`process_resume()` is a functional wrapper designed for web controllers and background workers:

```python
def process_resume(
    resume_path: str | Path,
    target_occupation: str | None = None,
    output_format: str = "none",
    generate_markdown: bool = True,
    allow_auto_select: bool = False,
    base_output_dir: str = "Outputs",
) -> dict:
    """
    Execute the complete end-to-end Road2Hire career readiness pipeline.

    Returns:
        dict: A canonical JSON-serializable dictionary conforming to
              pipeline_output.schema.json (status="success") or
              pipeline_error.schema.json (status="error").
    """
```

#### Parameter Reference

| Parameter | Type | Required | Default | Description & Validation Rules |
| :--- | :--- | :---: | :---: | :--- |
| `resume_path` | `str \| Path` | Yes | — | Absolute or relative path to a readable `.pdf` file. Non-existent files raise `ResumeValidationError` (`RESUME_NOT_FOUND`). |
| `target_occupation`| `Optional[str]` | No | `None` | Case-insensitive occupation title (e.g. `"Data Engineer"`) or canonical ESCO concept URI. |
| `output_format` | `str` | No | `"none"` | `"none"` (suppresses file I/O for speed in API workers), `"json"`, `"markdown"`, or `"both"`. |
| `generate_markdown`| `bool` | No | `True` | Generates a complete executive Markdown report in `data.report_markdown`. |
| `allow_auto_select`| `bool` | No | `False` | When `True`, automatically selects the highest-scoring occupation if `target_occupation=None`. |
| `base_output_dir` | `str` | No | `"Outputs"` | Destination directory when saving output files to disk. |

---

## 3. Core Contract Rules & Data Invariants

### 3.1 Schema Versioning & Stability
- The contract version follows Semantic Versioning (`MAJOR.MINOR.PATCH`).
- The current contract version is **`1.0.0`** (`pipeline_version: "1.0.0"` or `schema_version: "1.0.0"`).
- Non-breaking additive fields increment `MINOR`. Breaking changes increment `MAJOR`.

### 3.2 Nulls vs. Empty Collections
- **Arrays:** Never returned as `null`. When a candidate has no items (e.g. no missing skills, no warnings, no surplus skills), the field returns an empty array `[]`.
- **Objects:** Never omitted. Empty objects are serialized as `{}`.
- **Optional Scalar Fields:** When information cannot be extracted from a resume (e.g. candidate location or end date), the value is explicitly `null` (never guessed or fabricated).
- **Graceful Stage Degradation:** If an optional processing stage fails recoverably (e.g. SHAP calculation failure), the corresponding section is set to `null`, and a descriptive notice is appended to `warnings`.

### 3.3 Semantic Disambiguation of Scores & Probabilities

> [!IMPORTANT]
> The backend layer must never treat the various scores produced by the pipeline as interchangeable confidence percentages:

| Metric Name | Canonical Path | Range | Nature | Non-Probabilistic Interpretation |
| :--- | :--- | :---: | :--- | :--- |
| **Match Score** | `data.skill_gap_analysis.match_score` | `[0.0, 1.0]` | Heuristic Alignment | $0.75 \times \text{Essential} + 0.25 \times \text{Optional}$ coverage. Measures taxonomy overlap. **Not hiring probability.** |
| **Class Probabilities**| `data.career_readiness.class_probabilities` | Sum to `1.0` | Model Heuristic | Softmax output of regularized logistic regression ($N=71$). **Uncalibrated; not real-world competence probabilities.** |
| **SHAP Attribution**| `data.explainability.attributions[].contribution`| $(-\infty, +\infty)$ | Marginal Log-Odds | Local feature attribution ($\phi_i$) relative to baseline log-odds. Describes model behavior, not causal proof. |
| **Graph Match Score**| `data.top_matching_occupations[].match_score` | $\ge 0$ (Int) | Graph Edge Count | Count of candidate skills directly connected to occupation in ESCO knowledge graph. |

### 3.4 Canonical ESCO URI Representation
All occupation and skill concepts preserve their official European Commission ESCO concept URIs:
- Occupation URI: `http://data.europa.eu/esco/occupation/<uuid>`
- Skill URI: `http://data.europa.eu/esco/skill/<uuid>`

---

## 4. Logical Sections of the Canonical Output Contract

Every successful response (`status: "success"`) provides 10 structured sections:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       CANONICAL OUTPUT CONTRACT (v1.0.0)                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. metadata                     - Ingestion file, schema version, latency  │
│  2. candidate_profile            - Contact info, education, experience, proj│
│  3. extracted_skills             - Normalized skill concepts & categories   │
│  4. target_occupation            - Confirmed target role & canonical URI    │
│  5. top_matching_occupations     - Top 5 graph-matched alternatives         │
│  6. skill_gap_analysis           - 3-tier coverage & missing/matched lists  │
│  7. career_readiness             - Predicted tier, probabilities, OOD flag  │
│  8. explainability               - SHAP local feature attributions          │
│  9. knowledge_graph              - Graph topology node & edge counts        │
│ 10. learning_roadmap             - 4-phase prioritized learning curriculum  │
│                                                                             │
│  *  report_markdown              - Full human-readable executive summary    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Canonical JSON Payloads & Schema Examples

### 5.1 Success Response (`pipeline_output.schema.json`)

```json
{
  "pipeline_version": "1.0.0",
  "execution_timestamp": "2026-11-08T15:00:00.000000+00:00",
  "status": "success",
  "data": {
    "metadata": {
      "pipeline_version": "1.0.0",
      "schema_version": "1.0.0",
      "source_file": "uploads/candidate_resume.pdf",
      "page_count": 1,
      "extraction_status": "success",
      "selection_mode": "explicit",
      "execution_timings_seconds": {
        "text_extraction_seconds": 0.0841,
        "skill_extraction_seconds": 0.4120,
        "gap_analysis_seconds": 0.2150,
        "readiness_inference_seconds": 0.0120,
        "shap_explainability_seconds": 0.0340,
        "total_pipeline_seconds": 1.8450
      }
    },
    "candidate_profile": {
      "name": "Alex Morgan",
      "email": "alex.morgan@example.com",
      "phone": "+1-555-010-2040",
      "location": "Pune, India",
      "summary": "Computer science graduate interested in data engineering.",
      "total_experience_years": 1.5,
      "education": [
        {
          "degree": "Bachelor of Technology in Computer Science",
          "field_of_study": "Computer Science",
          "institution": "Example Institute of Technology",
          "start_year": 2022,
          "end_year": 2026,
          "cgpa": 8.8,
          "percentage": null,
          "academic_level": "bachelor"
        }
      ],
      "experience": [
        {
          "job_title": "Data Engineering Intern",
          "organization": "Example Tech",
          "employment_type": "internship",
          "start_date": "January 2025",
          "end_date": "June 2025",
          "responsibilities": ["Built ETL pipelines using Python and SQL."],
          "skills_used": ["Python", "SQL"]
        }
      ],
      "projects": [
        {
          "project_name": "ETL Ingestion Engine",
          "description": "Built automated data ingestion pipeline using Python.",
          "technologies": ["Python", "PostgreSQL", "Docker"]
        }
      ],
      "certifications": []
    },
    "extracted_skills": [
      {
        "skill_name": "Python (computer programming)",
        "canonical_uri": "http://data.europa.eu/esco/skill/4c5b2a62-5a76-4d99-a7a8-cbf04e9e8d1e",
        "category": "programming_languages",
        "confidence": 1.0,
        "source_contexts": ["skills", "experience", "projects"]
      }
    ],
    "target_occupation": {
      "preferred_label": "data engineer",
      "canonical_uri": "http://data.europa.eu/esco/occupation/2079755f-d809-49e6-8037-4de6180e54c0",
      "code": "2512.1",
      "description": "Data engineers design, construct, test and maintain data architectures."
    },
    "top_matching_occupations": [
      {
        "preferred_label": "data engineer",
        "canonical_uri": "http://data.europa.eu/esco/occupation/2079755f-d809-49e6-8037-4de6180e54c0",
        "match_score": 5
      }
    ],
    "skill_gap_analysis": {
      "match_score": 0.7250,
      "essential_coverage": 0.7000,
      "optional_coverage": 0.8000,
      "matched_skills": [
        {
          "skill_name": "Python (computer programming)",
          "canonical_uri": "http://data.europa.eu/esco/skill/4c5b2a62-5a76-4d99-a7a8-cbf04e9e8d1e",
          "tier": "exact",
          "credit": 1.0,
          "is_essential": true
        }
      ],
      "partially_matched_skills": [],
      "missing_essential_skills": [
        {
          "skill_name": "manage database security",
          "canonical_uri": "http://data.europa.eu/esco/skill/7d12f122-83bc-4672-8809-6799011e0394",
          "skill_type": "skill/competence"
        }
      ],
      "missing_optional_skills": []
    },
    "career_readiness": {
      "predicted_class": "Developing",
      "class_probabilities": {
        "Developing": 0.7842,
        "Job Ready": 0.1834,
        "Not Ready": 0.0324
      },
      "feature_vector": {
        "skill_overlap_ratio": 0.4200,
        "years_experience": 1.5,
        "education_level_numeric": 2,
        "essential_skill_coverage": 0.7000,
        "optional_skill_coverage": 0.8000
      },
      "is_ood": false,
      "ood_warnings": []
    },
    "explainability": {
      "predicted_class_explained": "Developing",
      "base_value": 1.1245,
      "attributions": [
        {
          "feature_name": "essential_skill_coverage",
          "display_name": "Essential Skill Coverage",
          "feature_value": 0.7000,
          "contribution": 0.6421,
          "direction": "positive",
          "description": "Coverage of mandatory skills defined by ESCO"
        }
      ]
    },
    "knowledge_graph": {
      "total_nodes": 48,
      "total_edges": 72,
      "node_counts_by_kind": {
        "candidate": 1,
        "education": 1,
        "experience": 1,
        "project": 1,
        "candidate_skill": 6,
        "esco_skill": 37,
        "occupation": 1
      }
    },
    "learning_roadmap": {
      "target_occupation_title": "data engineer",
      "total_roadmap_skills": 1,
      "total_estimated_weeks": "2 – 4 Weeks",
      "phases": [
        {
          "phase_number": 1,
          "phase_name": "Phase 1: Foundational Competencies & Core Knowledge",
          "description": "Establish core theoretical and architectural foundations.",
          "estimated_weeks": "2 – 4 Weeks",
          "milestones": [
            {
              "skill_name": "manage database security",
              "canonical_uri": "http://data.europa.eu/esco/skill/7d12f122-83bc-4672-8809-6799011e0394",
              "priority": "Critical",
              "learning_activities": ["Study RBAC, TLS encryption, and least-privilege principles."],
              "practical_project_scenario": "Configure PostgreSQL row-level security and TLS authentication.",
              "completion_criteria": "Successfully enforce encrypted client connections and role boundaries."
            }
          ]
        }
      ]
    },
    "report_markdown": "# Road2Hire Career Readiness Report\n..."
  }
}
```

---

### 5.2 Structured Error Responses (`pipeline_error.schema.json`)

When an error occurs, the pipeline catches the condition and returns a structured error object with `status: "error"`:

#### Example: Corrupted or 0-Byte PDF
```json
{
  "pipeline_version": "1.0.0",
  "execution_timestamp": "2026-11-08T15:05:00.000000+00:00",
  "status": "error",
  "error": {
    "code": "RESUME_PARSE_FAILED",
    "message": "Input resume file 'empty_corrupt.pdf' is empty (0 bytes) or corrupted.",
    "stage": "input_validation",
    "details": {
      "source_file": "empty_corrupt.pdf",
      "byte_size": 0
    }
  }
}
```

#### Example: Unresolvable Target Occupation
```json
{
  "pipeline_version": "1.0.0",
  "execution_timestamp": "2026-11-08T15:06:00.000000+00:00",
  "status": "error",
  "error": {
    "code": "OCCUPATION_NOT_FOUND",
    "message": "Target occupation 'Quantum Alchemist' could not be resolved in the ESCO taxonomy.",
    "stage": "occupation_resolution",
    "details": {
      "input_occupation": "Quantum Alchemist",
      "suggested_occupations": [
        {
          "preferred_label": "data engineer",
          "canonical_uri": "http://data.europa.eu/esco/occupation/2079755f-d809-49e6-8037-4de6180e54c0"
        }
      ]
    }
  }
}
```

---

## 6. Standardized Error Codes & HTTP Mapping

Backend web controllers should map pipeline error codes to corresponding HTTP response statuses:

| Pipeline Error Code | Stage | HTTP Status | Description |
| :--- | :--- | :---: | :--- |
| `RESUME_NOT_FOUND` | `input_validation` | `404 Not Found` | The specified resume file does not exist on disk. |
| `RESUME_PARSE_FAILED` | `input_validation` | `422 Unprocessable`| File is empty (0-byte), not a valid PDF, or has no extractable text. |
| `INVALID_INPUT` | `input_validation` | `400 Bad Request` | Unsupported argument types or malformed options. |
| `OCCUPATION_NOT_FOUND` | `occupation_resolution`| `404 Not Found` | Target occupation title/URI not found in ESCO taxonomy. |
| `OCCUPATION_SELECTION_REQUIRED`| `occupation_resolution`| `422 Unprocessable`| Target occupation was omitted while auto-selection was disabled. |
| `READINESS_MODEL_ERROR`| `readiness_inference` | `500 Internal Error`| Model artifact loading or feature vector extraction failure. |
| `PIPELINE_EXECUTION_ERROR`| `pipeline_execution` | `500 Internal Error`| Unexpected runtime exception during pipeline orchestration. |

---

## 7. FastAPI Backend Integration Pattern

To integrate `process_resume()` into a FastAPI application without blocking the server event loop:

### 7.1 Startup Pre-Warming (Lifespan Context)
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from AI.Pipeline import get_pipeline

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-warm heavy singletons (ESCO graph, MiniLM embeddings, readiness model)
    print("Pre-warming Road2Hire AI/ML singleton...")
    pipeline = get_pipeline()
    pipeline._ensure_graph()
    pipeline._ensure_skill_extractor()
    pipeline._ensure_readiness_model()
    print("Road2Hire AI/ML Engine is ready.")
    yield

app = FastAPI(title="Road2Hire API", lifespan=lifespan)
```

### 7.2 Asynchronous Background Worker Execution
Because full resume analysis requires $1.8\text{s}$ to $2.5\text{s}$, **never execute `process_resume()` directly inside an HTTP endpoint thread**:

```python
import uuid
from pathlib import Path
from fastapi import UploadFile, File, Form, HTTPException, status
from AI.Pipeline import process_resume

# Enqueue background task
@app.post("/api/v1/resumes/analyze", status_code=status.HTTP_202_ACCEPTED)
async def analyze_resume_endpoint(
    resume: UploadFile = File(...),
    target_occupation: str | None = Form(None),
):
    if not resume.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # Save to secure spool
    task_id = str(uuid.uuid4())
    spool_path = Path("/tmp/spool") / f"{task_id}.pdf"
    spool_path.parent.mkdir(parents=True, exist_ok=True)
    with open(spool_path, "wb") as f:
        f.write(await resume.read())

    # Dispatch to background task queue (e.g. Celery / ARQ / Redis Queue)
    # celery_worker.process_resume_task.delay(str(spool_path), target_occupation)

    return {
        "task_id": task_id,
        "status": "PENDING",
        "message": "Resume queued for AI analysis."
    }
```

---

## 8. Related Documentation

- For overall architecture and pipeline stages, see [01: Architecture & Pipeline](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Docs/01_AI_ML_Architecture_and_Pipeline.md).
- For research questions, literature review, and taxonomy design, see [02: Research & Taxonomy](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Docs/02_AI_ML_Research_and_Taxonomy.md).
- For algorithmic formulas, matching tiers, and SHAP math, see [03: Algorithms & Methodology](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Docs/03_AI_ML_Algorithms_and_Methodology.md).
- For empirical evaluation, cross-validation metrics, and known limitations, see [04: Model Evaluation & Limitations](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Docs/04_AI_ML_Model_Evaluation_and_Limitations.md).
- For database architecture and PostgreSQL mappings, see [06: Database Storage Specification](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Docs/06_AI_ML_Database_Storage_Specification.md).
- For engineering handover and checklists, see [07: Final Handover Document](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Docs/07_AI_ML_Final_Handover.md).

