# Road2Hire — AI/ML Canonical Output-to-Database Field Mapping

**Specification Version:** 1.0.0  
**Contract Version:** `1.0.0` (Draft-07 JSON Schema)  
**Pipeline Version:** `3.0.0`  
**Target Audience:** Backend Developers, Database Administrators, API Engineers  
**Status:** AI/ML Team Recommendation & Field-Level Data Dictionary  

---

> [!NOTE]
> **Implementation Scope & Architectural Boundary:**  
> This document defines an exhaustive field-by-field mapping between the canonical JSON output produced by the Road2Hire AI/ML pipeline (`UnifiedPipelineResult.to_canonical_dict()`) and recommended PostgreSQL database entities.  
> All suggested tables, columns, constraints, and data types are **architectural guidelines and recommendations**. They are designed to allow the backend engineering team to construct relational models and migrations without altering the AI/ML pipeline.

---

## 1. Mapped Output Sections Index

| Section | Canonical JSON Top-Level Key | Suggested Database Table / Entity | Primary Storage Strategy |
|:---:|:---|:---|:---|
| **1** | `metadata` | `pipeline_runs` | Dedicated Relational Columns + JSONB timings |
| **2** | `candidate_profile` | `candidate_profiles` | Hybrid (Normalized Identity + JSONB Sections) |
| **3** | `skills` | `candidate_skills` | Normalized Relational Rows (One row per skill) |
| **4** | `occupation_recommendations` | `occupation_recommendations` | Normalized Relational Rows (Ranked matches) |
| **5** | `target_occupation` | `target_occupations` | Dedicated Relational Table ($1:1$ with Run) |
| **6** | `skill_gap` | `skill_gap_analyses` | Relational Scores + JSONB Tier Details |
| **7** | `readiness` | `readiness_predictions` | Relational Probabilities + JSONB Features |
| **8** | `explanations` | `shap_explanations` | Relational Core Values + JSONB Waterfall Steps |
| **9** | `knowledge_graph` | `knowledge_graph_summaries` | Relational Metrics + JSONB Degree Maps |
| **10** | `learning_roadmap` | `learning_roadmaps` | Relational Headers + JSONB 4-Phase Curriculum |
| **11** | `errors` (Error Contract) | `pipeline_errors` | Dedicated Relational Error Log ($1:1$ with Run) |

---

## 2. Section-by-Section Detailed Field Mapping

### Section 1: Execution Metadata (`metadata.*`)
**Target Table:** `pipeline_runs`  
Represents a single execution run of the pipeline on a candidate's resume PDF.

| Canonical JSON Path | Suggested Column Name | PostgreSQL Data Type | Nullable? | Storage Strategy | Description & Constraints |
|:---|:---|:---|:---:|:---:|:---|
| `metadata.schema_version` | `schema_version` | `VARCHAR(16)` | No | Column | Output contract version (e.g. `'1.0.0'`). |
| `metadata.pipeline_version` | `pipeline_version` | `VARCHAR(16)` | No | Column | ML pipeline release version (e.g. `'3.0.0'`). |
| `metadata.status` | `status` | `VARCHAR(16)` | No | Column | Execution health: `'success'`, `'warning'`, or `'error'`. |
| `metadata.timestamp` | `executed_at` | `TIMESTAMPTZ` | No | Column | ISO-8601 execution timestamp. |
| `metadata.source_file` | `source_file_name` | `TEXT` | No | Column | Resume PDF filename or path evaluated. |
| `metadata.page_count` | `page_count` | `INTEGER` | No | Column | Total pages extracted (must be $\ge 1$). |
| `metadata.extraction_status` | `extraction_status` | `VARCHAR(32)` | No | Column | Text extraction status: `'success'`, `'needs_ocr'`, `'warning'`. |
| `metadata.execution_timings_seconds` | `timing_breakdown` | `JSONB` | Yes | JSONB | Per-stage timing dictionary in seconds. |
| `metadata.execution_timings_seconds.total_pipeline_seconds` | `total_duration_seconds` | `NUMERIC(8,4)` | Yes | Column | Total pipeline wall-clock execution time. |
| `warnings` | `warnings` | `JSONB` | No | JSONB | Array of diagnostic warning strings (`[]` if none). |
| `errors` | `errors` | `JSONB` | No | JSONB | Array of critical execution error strings. |
| `report_paths` | `report_file_paths` | `JSONB` | Yes | JSONB | Key-value paths for generated `.json` and `.md` reports. |

---

### Section 2: Candidate Profile (`candidate_profile.*`)
**Target Table:** `candidate_profiles`  
Represents the structured resume intelligence extracted according to Schema v1.1.0.

| Canonical JSON Path | Suggested Column Name | PostgreSQL Data Type | Nullable? | Storage Strategy | Description & Constraints |
|:---|:---|:---|:---:|:---:|:---|
| `candidate_profile.schema_version` | `profile_schema_version` | `VARCHAR(16)` | No | Column | Candidate Profile Schema version (`'1.1.0'`). |
| `candidate_profile.candidate.name` | `candidate_name` | `VARCHAR(255)` | Yes | Column | Candidate full name extracted from header text. |
| `candidate_profile.candidate.email` | `candidate_email` | `VARCHAR(255)` | Yes | Column | Candidate email address (indexed for search). |
| `candidate_profile.candidate.phone` | `candidate_phone` | `VARCHAR(64)` | Yes | Column | Candidate phone number. |
| `candidate_profile.candidate.location` | `candidate_location` | `VARCHAR(255)` | Yes | Column | City, state, or country of residence. |
| `candidate_profile.candidate.summary` | `professional_summary` | `TEXT` | Yes | Column | Parsed professional statement or objective. |
| `candidate_profile.candidate` | `candidate_info_raw` | `JSONB` | Yes | JSONB | Complete candidate contact object including raw text spans. |
| `candidate_profile.education` | `education` | `JSONB` | No | JSONB | Array of academic qualifications (`degree`, `institution`, `field`, `dates`, `score`). |
| `candidate_profile.experience` | `experience` | `JSONB` | No | JSONB | Array of professional history (`job_title`, `organization`, `dates`, `responsibilities`, `skills_used`). |
| `candidate_profile.projects` | `projects` | `JSONB` | No | JSONB | Array of portfolio items (`project_name`, `description`, `technologies`). |
| `candidate_profile.certifications` | `certifications` | `JSONB` | No | JSONB | Array of certifications (`name`, `issuer`, `date`). |

---

### Section 3: Extracted & Normalized Skills (`skills.*`)
**Target Table:** `candidate_skills`  
Normalized individual skill records enabling high-speed relational queries (e.g. *"Candidates with Python and SQL"*).

| Canonical JSON Path | Suggested Column Name | PostgreSQL Data Type | Nullable? | Storage Strategy | Description & Constraints |
|:---|:---|:---|:---:|:---:|:---|
| `skills.extracted_skill_count` | `extracted_skill_count` | `INTEGER` | No | Run Column | Total raw skill mentions extracted via Trie. |
| `skills.mapped_skill_count` | `mapped_skill_count` | `INTEGER` | No | Run Column | Total skills normalized to ESCO concept URIs. |
| `skills.extracted_skills[].skill` | `raw_skill_name` | `VARCHAR(255)` | No | Row Column | Skill string literal found in resume text. |
| `skills.extracted_skills[].source_sections` | `source_sections` | `JSONB` | No | Row Column | Sections where skill occurred (e.g. `["skills", "experience"]`). |
| `skills.extracted_skills[].occurrences` | `occurrences` | `JSONB` | Yes | Row Column | Text character offsets and section context spans. |
| `skills.esco_mappings[].ESCO_Skill_Id` | `esco_skill_id` | `VARCHAR(512)` | Yes | Row Column | Canonical ESCO concept URI (indexed for fast joins). |
| `skills.esco_mappings[].ESCO_Skill_Name` | `esco_skill_name` | `VARCHAR(255)` | Yes | Row Column | Canonical ESCO preferred label. |
| `skills.esco_mappings[].ESCO_Skill_Type` | `esco_skill_type` | `VARCHAR(64)` | Yes | Row Column | Skill type: `'skill/competence'` or `'knowledge'`. |
| `skills.esco_mappings[].ESCO_Reuse_Level` | `esco_reuse_level` | `VARCHAR(64)` | Yes | Row Column | Reusability level: `'cross-sector'`, `'sector-specific'`. |
| `skills.esco_mappings[].ESCO_Mapping_Type` | `esco_mapping_type` | `VARCHAR(32)` | Yes | Row Column | Mapping fidelity: `'exact'`, `'synonym'`, `'semantic'`. |
| `skills.esco_mappings[].confidence` | `confidence` | `NUMERIC(4,3)` | Yes | Row Column | Normalization confidence score ($0.000$ to $1.000$). |

---

### Section 4: Occupation Recommendations (`occupation_recommendations[]`)
**Target Table:** `occupation_recommendations`  
Ranked occupation matches derived from knowledge graph overlap scoring.

| Canonical JSON Path | Suggested Column Name | PostgreSQL Data Type | Nullable? | Storage Strategy | Description & Constraints |
|:---|:---|:---|:---:|:---:|:---|
| (Array Index + 1) | `rank_order` | `INTEGER` | No | Column | Recommendation rank ($1$ to $10$). |
| `[].occupation_uri` | `occupation_uri` | `VARCHAR(512)` | No | Column | Canonical ESCO occupation URI (indexed). |
| `[].occupation_label` | `occupation_label` | `VARCHAR(255)` | No | Column | Standard ESCO occupation title. |
| `[].score` | `match_score` | `INTEGER` | No | Column | Overlap match score ($0$ to $100+$). |
| `[].essential_count` | `essential_matched` | `INTEGER` | No | Column | Number of essential skills matched. |
| `[].optional_count` | `optional_matched` | `INTEGER` | No | Column | Number of optional skills matched. |
| `[].supporting_skills` | `supporting_skills` | `JSONB` | No | JSONB | List of candidate skills supporting this recommendation. |

---

### Section 5: Target Occupation (`target_occupation.*`)
**Target Table:** `target_occupations`  
The specific canonical role resolved for skill gap, readiness, and roadmap generation.

| Canonical JSON Path | Suggested Column Name | PostgreSQL Data Type | Nullable? | Storage Strategy | Description & Constraints |
|:---|:---|:---|:---:|:---:|:---|
| `target_occupation.occupation_uri` | `occupation_uri` | `VARCHAR(512)` | No | Column | Canonical ESCO concept URI for the target role. |
| `target_occupation.occupation_label` | `occupation_label` | `VARCHAR(255)` | No | Column | Target occupation title (e.g. `'data engineer'`). |
| `target_occupation.match_score` | `match_score` | `INTEGER` | No | Column | Skill overlap score against this specific role. |
| `target_occupation.essential_matched` | `essential_matched` | `INTEGER` | No | Column | Essential skill count satisfied by candidate. |
| `target_occupation.optional_matched` | `optional_matched` | `INTEGER` | No | Column | Optional skill count satisfied by candidate. |
| `target_occupation.supporting_skills` | `supporting_skills` | `JSONB` | No | JSONB | Array of supporting candidate skill strings. |
| `target_occupation.resolution_source` | `resolution_source` | `VARCHAR(32)` | No | Column | Source: `'suggestion'`, `'direct_uri'`, `'taxonomy_lookup'`, `'top_recommendation'`. |

---

### Section 6: Skill Gap Analysis (`skill_gap.*`)
**Target Table:** `skill_gap_analyses`  
3-tier hybrid gap analysis evaluating candidate coverage against target role requirements.

| Canonical JSON Path | Suggested Column Name | PostgreSQL Data Type | Nullable? | Storage Strategy | Description & Constraints |
|:---|:---|:---|:---:|:---:|:---|
| `skill_gap.overall_skill_coverage_score` | `overall_coverage_score` | `NUMERIC(5,4)` | No | Column | Weighted coverage score ($0.0000$ to $1.0000$). |
| `skill_gap.essential_skill_coverage_score` | `essential_coverage_score` | `NUMERIC(5,4)` | No | Column | Essential requirements coverage ($0.0000$ to $1.0000$). |
| `skill_gap.optional_skill_coverage_score` | `optional_coverage_score` | `NUMERIC(5,4)` | No | Column | Optional requirements coverage ($0.0000$ to $1.0000$). |
| `skill_gap.matched_skills` | `matched_skills` | `JSONB` | No | JSONB | Array of exact Tier-1 matches with credits and URIs. |
| `skill_gap.partially_matched_skills` | `partially_matched_skills` | `JSONB` | No | JSONB | Array of Tier-2 (graph) and Tier-3 (semantic) partial matches. |
| `skill_gap.missing_essential_skills` | `missing_essential_skills` | `JSONB` | No | JSONB | Array of required essential skills candidate lacks. |
| `skill_gap.missing_optional_skills` | `missing_optional_skills` | `JSONB` | No | JSONB | Array of optional skills candidate lacks. |
| `skill_gap.surplus_candidate_skills` | `surplus_skills` | `JSONB` | Yes | JSONB | Skills candidate possesses not required by occupation. |
| `skill_gap.unmapped_candidate_skills` | `unmapped_skills` | `JSONB` | Yes | JSONB | Resume skills not recognized in ESCO taxonomy. |

---

### Section 7: Career Readiness Prediction (`readiness.*`)
**Target Table:** `readiness_predictions`  
Supervised multi-class readiness inference and Out-of-Distribution empirical diagnostics (M4).

| Canonical JSON Path | Suggested Column Name | PostgreSQL Data Type | Nullable? | Storage Strategy | Description & Constraints |
|:---|:---|:---|:---:|:---:|:---|
| `readiness.predicted_class` | `predicted_class` | `VARCHAR(32)` | Yes | Column | Category: `'Developing'`, `'Job Ready'`, or `'Not Ready'`. Nullable if inference skipped. |
| `readiness.class_probabilities.Developing` | `prob_developing` | `NUMERIC(5,4)` | Yes | Column | Uncalibrated model heuristic estimate for Developing category (must not be presented as calibrated confidence or real-world hiring probability). |
| `readiness.class_probabilities.Job Ready` | `prob_job_ready` | `NUMERIC(5,4)` | Yes | Column | Uncalibrated model heuristic estimate for Job Ready category (must not be presented as calibrated confidence or real-world hiring probability). |
| `readiness.class_probabilities.Not Ready` | `prob_not_ready` | `NUMERIC(5,4)` | Yes | Column | Uncalibrated model heuristic estimate for Not Ready category (must not be presented as calibrated confidence or real-world hiring probability). |
| `readiness.model_version` | `model_version` | `VARCHAR(32)` | Yes | Column | Model release identifier (e.g. `'0.1.0-exploratory'`). |
| `readiness.model_type` | `model_type` | `VARCHAR(64)` | Yes | Column | Estimator architecture (e.g. `'LogisticRegression'`). |
| `readiness.is_experimental` | `is_experimental` | `BOOLEAN` | Yes | Column | Always `TRUE` for pilot baseline models. |
| `readiness.is_ood` | `is_ood` | `BOOLEAN` | Yes | Column | Out-of-Distribution extrapolation flag. |
| `readiness.ood_warnings` | `ood_warnings` | `JSONB` | Yes | JSONB | Array of diagnostic strings detailing out-of-bound signals. |
| `readiness.feature_values` | `feature_values` | `JSONB` | Yes | JSONB | 9 extracted feature values evaluated by classifier. |
| `readiness.training_sample_count` | `training_sample_count` | `INTEGER` | Yes | Column | Pilot cohort sample size ($N=71$). |
| `readiness.limitations` | `limitations` | `JSONB` | Yes | JSONB | Scientific disclaimers and governance caveats. |

---

### Section 8: Explainability & SHAP Attributions (`explanations.*`)
**Target Table:** `shap_explanations`  
Exact SHAP feature attributions explaining the candidate's career readiness score (M4.5).

| Canonical JSON Path | Suggested Column Name | PostgreSQL Data Type | Nullable? | Storage Strategy | Description & Constraints |
|:---|:---|:---|:---:|:---:|:---|
| `explanations.target_class_explained` | `target_class_explained` | `VARCHAR(32)` | Yes | Column | Readiness class explained (matches `predicted_class`). |
| `explanations.base_value` | `base_value` | `NUMERIC(8,4)` | Yes | Column | Model baseline expected value (intercept log-odds). |
| `explanations.human_readable_summary` | `human_readable_summary` | `TEXT` | Yes | Column | Natural language explanation synthesized from attributions. |
| `explanations.top_positive_factors` | `top_positive_factors` | `JSONB` | Yes | JSONB | Top factors supporting the predicted readiness state. |
| `explanations.top_negative_factors` | `top_negative_factors` | `JSONB` | Yes | JSONB | Top factors constraining the candidate's readiness state. |
| `explanations.feature_contributions` | `feature_contributions` | `JSONB` | Yes | JSONB | Full array of 9 SHAP attribution values ($\phi_i$). |
| `explanations.waterfall_steps` | `waterfall_steps` | `JSONB` | Yes | JSONB | Pre-formatted visualization coordinates for chart rendering. |
| `explanations.global_importance_ranking` | `global_importance_ranking` | `JSONB` | Yes | JSONB | Macro feature importance ranking across training set. |
| `explanations.limitations` | `shap_limitations` | `JSONB` | Yes | JSONB | Explainer assumptions and interpretation boundaries. |

---

### Section 9: Personalized Knowledge Graph (`knowledge_graph.*`)
**Target Table:** `knowledge_graph_summaries`  
Topology metrics for the candidate-specific knowledge graph subgraph.

| Canonical JSON Path | Suggested Column Name | PostgreSQL Data Type | Nullable? | Storage Strategy | Description & Constraints |
|:---|:---|:---|:---:|:---:|:---|
| `knowledge_graph.total_nodes` | `total_nodes` | `INTEGER` | No | Column | Total graph entities (Candidate, Skills, Education, Roles). |
| `knowledge_graph.total_edges` | `total_edges` | `INTEGER` | No | Column | Total relationship edges in personalized subgraph. |
| `knowledge_graph.target_occupation` | `target_occupation_uri` | `VARCHAR(512)` | Yes | Column | Concept URI of the occupation subgraph target. |
| `knowledge_graph.node_counts_by_kind` | `node_counts_by_kind` | `JSONB` | Yes | JSONB | Breakdown: `{"Skill": 14, "Candidate": 1, "Degree": 1}`. |
| `knowledge_graph.edge_counts_by_relation` | `edge_counts_by_relation` | `JSONB` | Yes | JSONB | Breakdown: `{"possesses_skill": 14, "requires_skill": 22}`. |

---

### Section 10: Personalized Learning Roadmap (`learning_roadmap.*`)
**Target Table:** `learning_roadmaps`  
A 4-phase structured curriculum designed to bridge the candidate's missing essential and optional skills.

| Canonical JSON Path | Suggested Column Name | PostgreSQL Data Type | Nullable? | Storage Strategy | Description & Constraints |
|:---|:---|:---|:---:|:---:|:---|
| `learning_roadmap.target_occupation_title` | `target_occupation_title` | `VARCHAR(255)` | Yes | Column | Curriculum target title (e.g. `'data engineer'`). |
| `learning_roadmap.target_occupation_uri` | `target_occupation_uri` | `VARCHAR(512)` | Yes | Column | Target ESCO concept URI. |
| `learning_roadmap.total_roadmap_skills` | `total_skills_to_learn` | `INTEGER` | Yes | Column | Total skills sequenced across all 4 phases. |
| `learning_roadmap.total_estimated_weeks` | `total_duration_weeks` | `VARCHAR(32)` | Yes | Column | Estimated curriculum timeline (e.g. `'16-24 weeks'`). |
| `learning_roadmap.phases` | `phases` | `JSONB` | Yes | JSONB | Complete 4-phase structured array with all milestone items. |
| `learning_roadmap.disclaimers` | `disclaimers` | `JSONB` | Yes | JSONB | Advisory guidance and prerequisite disclaimers. |

---

### Section 11: Pipeline Execution Errors (`pipeline_error.*`)
**Target Table:** `pipeline_errors`  
Standardized error logging conforming to [`pipeline_error.schema.json`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Pipeline/schemas/pipeline_error.schema.json).

| Canonical JSON Path | Suggested Column Name | PostgreSQL Data Type | Nullable? | Storage Strategy | Description & Constraints |
|:---|:---|:---|:---:|:---:|:---|
| `status` | `status` | `VARCHAR(16)` | No | Column | Always `'error'`. |
| `timestamp` | `occurred_at` | `TIMESTAMPTZ` | No | Column | Failure timestamp. |
| `error.code` | `error_code` | `VARCHAR(64)` | No | Column | Standard machine code (e.g. `'OCCUPATION_NOT_FOUND'`). |
| `error.stage` | `error_stage` | `VARCHAR(64)` | No | Column | Stage of failure (e.g. `'occupation_resolution'`). |
| `error.message` | `error_message` | `TEXT` | No | Column | Human-readable explanation of failure. |
| `error.recoverable` | `recoverable` | `BOOLEAN` | No | Column | `TRUE` if user can retry with valid inputs (e.g. valid role). |
| `error.details` | `error_details` | `JSONB` | Yes | JSONB | Suggested occupations or diagnostic error context. |
| `warnings` | `warnings` | `JSONB` | No | JSONB | Diagnostics collected prior to the fatal error. |

