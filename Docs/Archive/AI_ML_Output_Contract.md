# Road2Hire — AI/ML Output JSON Contract & Integration Specification

**Specification Version:** `1.0.0`  
**Pipeline Engine Version:** `3.0.0`  
**JSON Schema Path:** [`AI/Pipeline/schemas/pipeline_output.schema.json`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Pipeline/schemas/pipeline_output.schema.json)  
**Error Schema Path:** [`AI/Pipeline/schemas/pipeline_error.schema.json`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Pipeline/schemas/pipeline_error.schema.json)  
**Schema Architecture Guide:** [`AI/Pipeline/schemas/README.md`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Pipeline/schemas/README.md)  

---

## 1. Executive Summary & Purpose

This document defines the formal, versioned JSON output interface between the Road2Hire AI/ML pipeline and backend service layers (such as FastAPI web services, message brokers, and relational databases). 

Backend developers can safely integrate with the pipeline through this contract without inspecting internal ML dependencies (such as Aho-Corasick Trie traversals, PyMuPDF parsers, SentenceTransformer embeddings, or SHAP linear game-theoretic decompositions).

---

## 2. Core Contract Rules & Data Invariants

### 2.1 Schema Versioning & Stability
- The contract version follows Semantic Versioning (`MAJOR.MINOR.PATCH`).
- The current contract version is **`1.0.0`** (`schema_version: "1.0.0"`).
- Non-breaking additions (such as auxiliary diagnostic fields) increment `MINOR`.
- Breaking changes (such as renaming or deleting a top-level key) increment `MAJOR`.

### 2.2 Nulls vs. Empty Collections
- **Arrays:** Never returned as `null`. When a candidate has no items (e.g. no missing skills, no warnings, no surplus skills), the field returns an empty array `[]`.
- **Objects:** Never omitted. Empty objects are serialized as `{}`.
- **Optional Scalar Fields:** When information cannot be extracted from a resume (e.g. candidate location or end date), the value is explicitly `null` (never fabricated or guessed).
- **Skipped Stages:** If an optional processing stage fails recoverably (e.g. SHAP calculation failure), the corresponding section is set to `null`, and a descriptive notification is appended to `warnings`.

### 2.3 Semantic Disambiguation of Scores & Probabilities
The backend layer must never treat the various scores produced by the pipeline as interchangeable confidence percentages:

| Metric Name | Source Module | Range | Nature | Interpretation |
|:---|:---|:---:|:---|:---|
| **`overall_skill_coverage_score`** | M3 Skill Gap Detector | `[0.0, 1.0]` | Heuristic Taxonomy Overlap | $0.75 \times \text{Essential Coverage} + 0.25 \times \text{Optional Coverage}$. Measures how many official ESCO requirements match resume strings. **Does not measure hiring probability.** |
| **`class_probabilities`** | M4 Readiness Classifier | Sum to `1.0` | Heuristic Model Odds | Softmax output of a regularized multinomial logistic regression ($N=71$). Reflects relative ranking under strong priors. **Uncalibrated; not real-world competence probabilities.** |
| **`contribution` (SHAP)** | M4.5 Explainability | $(-\infty, +\infty)$ | Marginal Log-Odds | Additive feature attribution ($\phi_i$) relative to the model intercept (`base_value`). Describes internal model behavior, not causal qualifications. |
| **`score` (Occupation Match)** | M2 Knowledge Graph | $\ge 0$ (Integer) | Graph Relation Count | Total number of candidate skills that have an ESCO graph edge to the occupation. |

### 2.4 Canonical ESCO URI Representation
All occupation and skill concepts preserve their official European Commission ESCO concept URIs:
- Occupation URI: `http://data.europa.eu/esco/occupation/<uuid>`
- Skill URI: `http://data.europa.eu/esco/skill/<uuid>`

### 2.5 Timestamps & Numeric Precision
- **Timestamps:** ISO-8601 strings in standard format (e.g. `2026-11-07T14:10:00.000000`).
- **Float Precision:** Coverage scores are floats in `[0.0, 1.0]`. Execution timings are measured in seconds rounded to 4 decimal places.

---

## 3. Logical Structure of the Output Contract

The canonical payload exposes 10 logical sections:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       CANONICAL OUTPUT CONTRACT (v1.0.0)                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. metadata                     - Versions, status, file path, timings     │
│  2. candidate_profile            - Contact info, education, experience, proj│
│  3. skills                       - Extracted text mentions & ESCO mappings  │
│  4. occupation_recommendations   - Ranked occupation matches from graph     │
│  5. target_occupation            - Confirmed target role & canonical URI    │
│  6. skill_gap                    - 3-tier hybrid coverage & missing skills  │
│  7. readiness                    - Predicted class, probabilities, OOD flag │
│  8. explanations                 - Exact SHAP feature contributions         │
│  9. knowledge_graph              - Graph topology node & edge counts        │
│ 10. learning_roadmap             - 4-phase prioritized learning curriculum  │
│                                                                             │
│  *  warnings                     - Non-fatal diagnostic notices             │
│  *  errors                       - Critical error logs                      │
│  *  report_paths                 - Persisted JSON and Markdown artifact URLs│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Sanitized Contract Examples

### Example 1: Successful Pipeline Execution (In-Distribution)

```json
{
  "schema_version": "1.0.0",
  "metadata": {
    "schema_version": "1.0.0",
    "pipeline_version": "3.0.0",
    "status": "success",
    "timestamp": "2026-11-07T14:10:00.000000",
    "source_file": "uploads/candidate_resume.pdf",
    "page_count": 1,
    "extraction_status": "success",
    "execution_timings_seconds": {
      "resume_prediction_seconds": 6.8412,
      "target_occupation_resolution_seconds": 0.0001,
      "skill_gap_detection_seconds": 0.0342,
      "personalized_graph_seconds": 0.0012,
      "readiness_prediction_seconds": 1.1245,
      "shap_explainability_seconds": 0.0312,
      "roadmap_generation_seconds": 0.0001,
      "total_pipeline_seconds": 8.0325
    }
  },
  "candidate_profile": {
    "schema_version": "1.1.0",
    "candidate": {
      "name": "Alex Morgan",
      "email": "alex.morgan@example.com",
      "phone": "+1-555-0199",
      "location": "San Francisco, CA",
      "summary": "Software engineer with 2 years of backend experience."
    },
    "education": [
      {
        "degree": "Bachelor of Science",
        "field_of_study": "Computer Science",
        "institution": "University of California",
        "start_date": "2018-09-01",
        "end_date": "2022-06-01",
        "score": null
      }
    ],
    "experience": [
      {
        "job_title": "Software Engineer",
        "organization": "Acme Technologies",
        "start_date": "2022-07-01",
        "end_date": null,
        "responsibilities": ["Developed backend data microservices in Python and PostgreSQL."],
        "skills_used": ["Python", "SQL", "Git"]
      }
    ],
    "projects": [
      {
        "project_name": "Data Pipeline",
        "description": "High-throughput streaming analytics pipeline using Python and Docker.",
        "technologies": ["Python", "Docker", "SQL"]
      }
    ],
    "certifications": []
  },
  "skills": {
    "extracted_skills": [
      {
        "skill": "Python",
        "source_sections": ["skills", "experience"],
        "occurrences": [
          {"section": "skills", "text": "Python", "start": 0, "end": 6}
        ]
      },
      {
        "skill": "SQL",
        "source_sections": ["skills"],
        "occurrences": [
          {"section": "skills", "text": "SQL", "start": 8, "end": 11}
        ]
      }
    ],
    "esco_mappings": [
      {
        "skill": "Python",
        "ESCO_Skill_Id": "http://data.europa.eu/esco/skill/ccd0a1d9-afda-43d9-b901-96344886e14d",
        "ESCO_Skill_Name": "Python (computer programming)",
        "ESCO_Skill_Type": "skill/competence",
        "ESCO_Reuse_Level": "cross-sector",
        "ESCO_Mapping_Type": "exact",
        "confidence": 1.0
      },
      {
        "skill": "SQL",
        "ESCO_Skill_Id": "http://data.europa.eu/esco/skill/598de5b0-5b58-4ea7-8058-a4bc4d18c742",
        "ESCO_Skill_Name": "SQL",
        "ESCO_Skill_Type": "knowledge",
        "ESCO_Reuse_Level": "cross-sector",
        "ESCO_Mapping_Type": "exact",
        "confidence": 1.0
      }
    ],
    "extracted_skill_count": 2,
    "mapped_skill_count": 2
  },
  "occupation_recommendations": [
    {
      "occupation_uri": "http://data.europa.eu/esco/occupation/2079755f-d809-49e6-8037-4de6180e54c0",
      "occupation_label": "data engineer",
      "score": 2,
      "essential_count": 2,
      "optional_count": 0,
      "supporting_skills": ["Python (computer programming)", "SQL"]
    }
  ],
  "target_occupation": {
    "occupation_uri": "http://data.europa.eu/esco/occupation/2079755f-d809-49e6-8037-4de6180e54c0",
    "occupation_label": "data engineer",
    "match_score": 2,
    "essential_matched": 2,
    "optional_matched": 0,
    "supporting_skills": ["Python (computer programming)", "SQL"],
    "resolution_source": "suggestion"
  },
  "skill_gap": {
    "overall_skill_coverage_score": 0.1875,
    "essential_skill_coverage_score": 0.1538,
    "optional_skill_coverage_score": 0.2857,
    "matched_skills": [
      {
        "candidate_skill": "Python",
        "occupation_skill": "Python (computer programming)",
        "match_tier": 1,
        "match_type": "exact",
        "credit": 1.0,
        "skill_uri": "http://data.europa.eu/esco/skill/ccd0a1d9-afda-43d9-b901-96344886e14d",
        "skill_type": "skill/competence"
      }
    ],
    "partially_matched_skills": [],
    "missing_essential_skills": [
      {
        "skill_uri": "http://data.europa.eu/esco/skill/a1b2c3d4-0000-0000-0000-000000000001",
        "skill_label": "data engineering",
        "skill_type": "skill/competence"
      }
    ],
    "missing_optional_skills": [],
    "surplus_candidate_skills": [],
    "unmapped_candidate_skills": []
  },
  "readiness": {
    "predicted_class": "Developing",
    "class_probabilities": {
      "Developing": 0.7241,
      "Job Ready": 0.2415,
      "Not Ready": 0.0344
    },
    "model_version": "0.1.0-exploratory",
    "model_type": "LogisticRegression",
    "feature_values": {
      "skills_count": 6.0,
      "exp_positions_count": 1.0,
      "has_senior_role": 0.0,
      "project_count": 1.0,
      "project_words": 12.0,
      "project_tech_count": 3.0,
      "has_production_system": 0.0,
      "edu_level_ordinal": 1.0,
      "is_stem_degree": 1.0
    },
    "is_experimental": true,
    "is_ood": false,
    "ood_warnings": [],
    "training_sample_count": 71,
    "training_class_distribution": {
      "Developing": 52,
      "Job Ready": 16,
      "Not Ready": 3
    },
    "feature_diagnostics": {},
    "limitations": [
      "Exploratory supervised model trained on an annotated pilot dataset (N=71).",
      "Predictions reflect profile depth and structural signals; they do not certify real-world competence.",
      "Class probabilities are heuristic estimates from regularized multinomial logistic regression and are not fully calibrated."
    ]
  },
  "explanations": {
    "target_class_explained": "Developing",
    "base_value": 0.4497,
    "top_positive_factors": [
      {
        "feature": "skills_count",
        "display_name": "Skills Count",
        "feature_value": 6.0,
        "contribution": 0.6541,
        "direction_relative_to_target": "positive",
        "description": "Number of verified technical skills normalized to canonical taxonomy"
      }
    ],
    "top_negative_factors": [],
    "feature_contributions": [],
    "human_readable_summary": "The model predicted 'Developing' with 72.4% confidence.",
    "waterfall_steps": [],
    "global_importance_ranking": [
      {
        "rank": 1,
        "feature": "skills_count",
        "display_name": "Skills Count",
        "mean_abs_shap": 0.9038,
        "description": "Number of verified technical skills normalized to canonical taxonomy"
      }
    ],
    "limitations": []
  },
  "knowledge_graph": {
    "total_nodes": 24,
    "total_edges": 38,
    "node_counts_by_kind": {"candidate": 1, "occupation": 1, "skill": 22},
    "edge_counts_by_relation": {"has_skill": 2, "requires_essential": 13, "requires_optional": 9},
    "target_occupation": "http://data.europa.eu/esco/occupation/2079755f-d809-49e6-8037-4de6180e54c0"
  },
  "learning_roadmap": {
    "target_occupation_title": "data engineer",
    "target_occupation_uri": "http://data.europa.eu/esco/occupation/2079755f-d809-49e6-8037-4de6180e54c0",
    "total_roadmap_skills": 1,
    "total_estimated_weeks": "12 – 22 Weeks",
    "phases": [
      {
        "phase_number": 1,
        "phase_name": "Phase 1: Foundational Competencies & Core Knowledge",
        "description": "Establish essential theoretical principles...",
        "estimated_weeks": "2 – 4 Weeks",
        "items": [
          {
            "skill_name": "data engineering",
            "esco_uri": "http://data.europa.eu/esco/skill/a1b2c3d4-0000-0000-0000-000000000001",
            "current_status": "missing_essential",
            "priority": "Critical",
            "importance_rationale": "Essential prerequisite for data pipelines.",
            "learning_outcome": "Build scalable data pipelines.",
            "suggested_activities": ["Study distributed systems architectures."],
            "practical_project": "Build an ETL data lake ingestion pipeline.",
            "estimated_duration_weeks": "2 – 3 Weeks",
            "prerequisites": ["Python", "SQL"],
            "completion_criteria": "Verifiable ETL pipeline deployed.",
            "resource_categories": []
          }
        ]
      },
      {
        "phase_number": 2,
        "phase_name": "Phase 2: Core Technical Implementation Skills",
        "description": "Acquire practical engineering tools...",
        "estimated_weeks": "4 – 8 Weeks",
        "items": []
      },
      {
        "phase_number": 3,
        "phase_name": "Phase 3: Applied Systems & Portfolio Project Execution",
        "description": "Bridge partially demonstrated skills...",
        "estimated_weeks": "4 – 6 Weeks",
        "items": []
      },
      {
        "phase_number": 4,
        "phase_name": "Phase 4: Advanced Specialization & Optional Capabilities",
        "description": "Expand professional differentiation...",
        "estimated_weeks": "2 – 4 Weeks",
        "items": []
      }
    ],
    "disclaimers": [
      "This learning roadmap is generated algorithmically from candidate resume evidence against the ESCO occupational framework.",
      "Completion of recommended learning items builds domain competency but does not guarantee employment or Job Ready certification."
    ]
  },
  "warnings": [],
  "errors": [],
  "report_paths": {
    "json": "Outputs/readiness_Alex_Morgan_candidate_resume_20261107_141000/career_readiness_report.json",
    "markdown": "Outputs/readiness_Alex_Morgan_candidate_resume_20261107_141000/career_readiness_report.md"
  }
}
```

---

### Example 2: Execution with Warnings & Out-of-Distribution (OOD) Detection

When candidate feature values exceed the bounds observed in the training cohort ($N=71$):

```json
{
  "schema_version": "1.0.0",
  "metadata": {
    "schema_version": "1.0.0",
    "pipeline_version": "3.0.0",
    "status": "warning",
    "timestamp": "2026-11-07T14:15:00.000000",
    "source_file": "uploads/senior_engineer_resume.pdf",
    "page_count": 2,
    "extraction_status": "success",
    "execution_timings_seconds": {
      "total_pipeline_seconds": 9.4215
    }
  },
  "candidate_profile": { ... },
  "skills": { ... },
  "target_occupation": {
    "occupation_uri": "http://data.europa.eu/esco/occupation/2079755f-d809-49e6-8037-4de6180e54c0",
    "occupation_label": "data engineer",
    "resolution_source": "suggestion"
  },
  "readiness": {
    "predicted_class": "Job Ready",
    "class_probabilities": {
      "Developing": 0.0084,
      "Job Ready": 0.9902,
      "Not Ready": 0.0014
    },
    "model_version": "0.1.0-exploratory",
    "model_type": "LogisticRegression",
    "feature_values": {
      "skills_count": 18.0,
      "exp_positions_count": 6.0,
      "has_senior_role": 1.0,
      "project_count": 4.0,
      "project_words": 180.0,
      "project_tech_count": 12.0,
      "has_production_system": 1.0,
      "edu_level_ordinal": 2.0,
      "is_stem_degree": 1.0
    },
    "is_experimental": true,
    "is_ood": true,
    "ood_warnings": [
      "Feature 'skills_count' (18.0) exceeds training maximum (14.0). Extrapolating into high log-odds regime.",
      "Feature 'exp_positions_count' (6.0) exceeds training maximum (4.0)."
    ],
    "training_sample_count": 71,
    "limitations": [
      "Exploratory supervised model trained on an annotated pilot dataset (N=71).",
      "Notice: Profile features exceed training bounds; predicted probabilities reflect statistical model extrapolation."
    ]
  },
  "warnings": [
    "M4 OOD Notice: Feature 'skills_count' (18.0) exceeds training maximum (14.0). Extrapolating into high log-odds regime.",
    "M4 OOD Notice: Feature 'exp_positions_count' (6.0) exceeds training maximum (4.0)."
  ],
  "errors": []
}
```

---

### Example 3: Pipeline Failure (Structured Error Contract)

When an unrecoverable failure occurs (such as an unparseable 0-byte corrupt document or missing file):

```json
{
  "schema_version": "1.0.0",
  "status": "error",
  "timestamp": "2026-11-07T14:20:00.000000",
  "error": {
    "code": "EMPTY_OR_CORRUPT_DOCUMENT",
    "message": "Failed to process resume 'corrupt_upload.pdf': file is empty or corrupted binary.",
    "stage": "input_validation",
    "details": {
      "source_file": "corrupt_upload.pdf",
      "byte_size": 0
    },
    "recoverable": false
  },
  "warnings": []
}
```

When an occupation is missing in non-interactive mode:

```json
{
  "schema_version": "1.0.0",
  "status": "error",
  "timestamp": "2026-11-07T14:21:00.000000",
  "error": {
    "code": "OCCUPATION_SELECTION_REQUIRED",
    "message": "No target occupation specified. In non-interactive mode, an explicit occupation must be provided.",
    "stage": "occupation_resolution",
    "details": {
      "suggested_occupations": [
        {"rank": 1, "label": "data engineer", "uri": "http://data.europa.eu/esco/occupation/2079755f-d809-49e6-8037-4de6180e54c0"},
        {"rank": 2, "label": "software developer", "uri": "http://data.europa.eu/esco/occupation/36d3936a-297c-473c-bb0f-07ef46c24bc9"}
      ]
    },
    "recoverable": true
  },
  "warnings": []
}
```

---

### Example 4: Edge Cases (Candidate with Zero Missing Skills)

When a candidate profile already fulfills all required essential and optional skills for the target occupation:

```json
{
  "schema_version": "1.0.0",
  "status": "success",
  "metadata": {
    "status": "success",
    "pipeline_version": "3.0.0"
  },
  "skill_gap": {
    "overall_skill_coverage_score": 1.0000,
    "essential_skill_coverage_score": 1.0000,
    "optional_skill_coverage_score": 1.0000,
    "matched_skills": [ ... ],
    "partially_matched_skills": [],
    "missing_essential_skills": [],
    "missing_optional_skills": []
  },
  "learning_roadmap": {
    "target_occupation_title": "data engineer",
    "total_roadmap_skills": 0,
    "total_estimated_weeks": "0 Weeks (Candidate profile fulfills all target occupation requirements)",
    "phases": [
      {
        "phase_number": 1,
        "phase_name": "Phase 1: Foundational Competencies & Core Knowledge",
        "description": "Establish essential theoretical principles...",
        "estimated_weeks": "0 Weeks",
        "items": []
      },
      {
        "phase_number": 2,
        "phase_name": "Phase 2: Core Technical Implementation Skills",
        "description": "Acquire practical engineering tools...",
        "estimated_weeks": "0 Weeks",
        "items": []
      },
      {
        "phase_number": 3,
        "phase_name": "Phase 3: Applied Systems & Portfolio Project Execution",
        "description": "Bridge partially demonstrated skills...",
        "estimated_weeks": "0 Weeks",
        "items": []
      },
      {
        "phase_number": 4,
        "phase_name": "Phase 4: Advanced Specialization & Optional Capabilities",
        "description": "Expand professional differentiation...",
        "estimated_weeks": "0 Weeks",
        "items": []
      }
    ],
    "disclaimers": [ ... ]
  }
}
```

---

## 5. Backend Database Mapping & Storage Recommendations

When persisting pipeline outputs in a relational database (e.g., PostgreSQL):

| Contract Section | Recommended Storage Strategy | Rationale |
|:---|:---|:---|
| `metadata` | Relational columns (`status`, `page_count`, `created_at`) | Enables high-performance indexing, dashboard metrics, and telemetry filtering. |
| `candidate_profile` | `JSONB` column (`candidate_profile`) | Preserves flexible nested candidate structures without complex relational join tables. |
| `target_occupation` | Relational foreign key or URI column (`target_occupation_uri`) | Allows fast filtering of candidates by target occupation. |
| `skill_gap` | Relational score (`overall_coverage: float`) + `JSONB` | Enables fast threshold filtering (`WHERE overall_coverage >= 0.70`) while preserving skill-level match details. |
| `readiness` | Relational enum (`readiness_class`) + `JSONB` | Enables candidate indexing by readiness status (`Job Ready`, `Developing`) while keeping OOD diagnostics in JSONB. |
| `explanations` | `JSONB` column | Stored for explainability audit trails and interactive waterfall UI rendering. |
| `learning_roadmap` | `JSONB` column | Stored directly for UI rendering in candidate dashboard. |
