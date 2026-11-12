# Road2Hire: Shared AI–Backend Reference

## 1. Purpose and division of responsibility

Road2Hire helps a user understand how their resume aligns with occupations, identify skill gaps, assess career readiness, and plan learning steps.

The AI pipeline turns a resume into structured career-analysis results. The backend provides authenticated APIs, validates ownership and inputs, invokes the pipeline when analysis is requested, stores the result, and serves saved results and mutable learning progress to the frontend. The frontend should use the endpoint contracts in [API_INTEGRATION_GUIDE.md](./API_INTEGRATION_GUIDE.md); this document is architectural context, not a second API manual.

## 2. End-to-end workflow

1. **Upload:** An authenticated user uploads a PDF through the resume API. The backend validates the extension, content type, size (5 MB maximum), and PDF signature, writes it under `Backend/uploads/`, and saves its metadata in `resumes`. The upload request also checks the submitted user ID against the authenticated user.
2. **Analyze:** A request to run matching or analysis resolves a resume owned by that user. `Services/pipeline_service.py` also checks that the stored file resolves to a regular file inside the configured upload directory.
3. **Run the AI pipeline:** The service creates a `pipeline_runs` record, transitions it from `pending` to `running`, and invokes `AI.Pipeline.process_resume(...)`. It supplies the resume path, requested target occupation (if any), occupation-selection option, and `output_format="none"` so retrieving analysis does not generate report files.
4. **Persist:** The service converts the result using `to_canonical_dict()`, sanitizes local file paths, and saves the complete result in `pipeline_runs.canonical_output`. Run status and available summary columns are updated. A compact `skill_gaps` summary is recorded for runs with a valid target and coverage data.
5. **Reuse:** Result-reading APIs read the saved run and its `canonical_output`; they do not rerun inference simply to return readiness, explanations, recommendations, or roadmap details. Roadmap progress is materialized in `learning_tasks` when needed and returned alongside the saved item details.

The pipeline itself performs resume processing and skill extraction, occupation ranking and target resolution, hybrid skill-gap analysis, knowledge-graph summary generation, readiness prediction, SHAP explanation, and roadmap generation. Stages can have different availability: a completed run may contain warnings or omit a result section. A successful HTTP response is not by itself proof that every AI stage produced output; inspect the run's status and saved warnings/results.

The older `GET /resumes/{resume_id}/analysis` flow is separate legacy functionality: it uses resume processing and skill extraction to populate `candidate_profiles`. It is not the unified `PipelineRun` workflow and does not create a canonical pipeline result.

### Run lifecycle and partial results

`pipeline_runs.status` is constrained to `pending`, `running`, `completed`, or `failed`. The service persists the initial states before expensive inference, then records completion or failure. Completed runs may still contain warnings and missing optional AI-stage output; `completed` means execution completed, not that every stage returned a prediction. Failed runs keep error code, stage, and message fields, and a structured failure payload may be saved in `canonical_output`. Retrieval APIs should distinguish a missing run, a non-completed run, and a completed run with a missing result section.

The service uses a separate database session for persisted run state so the in-flight request session does not hold a long-lived transaction during AI execution. Resume ownership and file-path validation happen before inference. Canonical serialization is checked and sanitized so local filesystem paths are not returned as stored result content.

## 3. AI/backend integration contract

### Entry point and invocation

- Public entry point: `AI.Pipeline.process_resume(resume_path, target_occupation=None, *, auto_select_top_occupation=False, output_dir=None, output_format="both", top_n_occupations=10, pipeline=None)`.
- Backend wrapper: `Backend/Services/pipeline_service.py`, through `run_pipeline_for_resume(...)`.
- The service uses the unified entry point and `output_format="none"`. The AI package returns a `UnifiedPipelineResult`; the backend calls `to_canonical_dict()` and stores the serialized representation.
- Pipeline execution is explicit: result retrieval endpoints use existing completed runs. A matching request that asks for a new target may create a new run and execute AI.

### Canonical result

The current canonical JSONB object is the detailed result and includes these sections:

| Key | Purpose |
|---|---|
| `schema_version`, `metadata` | Contract version and run/source metadata |
| `candidate_profile`, `skills` | Extracted profile and skill evidence |
| `occupation_recommendations`, `target_occupation` | Ranked ESCO occupations and selected target |
| `skill_gap` | Hybrid match evidence, coverage and missing-skill details |
| `readiness`, `explanations` | Readiness result and feature/SHAP explanation, when available |
| `knowledge_graph` | Graph summary information |
| `learning_roadmap` | Phases, items, resource categories, activities and outcomes |
| `warnings`, `errors`, `report_paths` | Partial-result diagnostics and report metadata |

These are actual canonical section names; older documents that refer to names such as `skill_gap_analysis`, `readiness_prediction`, or `shap_explanation` describe an earlier in-memory representation, not the current stored JSON contract. The pipeline can return a warning or error at the AI level; the backend separately owns the persisted run lifecycle and exposes a failed run's error fields.

### What the stages contribute

- Resume processing extracts a profile and skill evidence; ESCO mapping normalizes skills and supports occupation ranking.
- Occupation selection resolves a requested target or selects a ranked occupation when the caller permits automatic selection.
- Hybrid skill-gap analysis compares candidate evidence with the selected occupation's ESCO requirements and keeps matched, partial, and missing evidence in the detailed result.
- Knowledge-graph generation currently contributes summary metrics to the canonical result.
- Readiness and SHAP stages can be unavailable or experimental; warnings explain missing outputs when the pipeline emits them.
- Roadmap generation organizes development suggestions into phases and items, including activities/resources when present in the AI result.

The backend does not independently recompute these sections when serving saved results. `skill_gaps` summarizes coverage for database queries, and `learning_tasks` adds mutable progress; neither replaces the canonical evidence.

## 4. Database: source of truth and relationships

The current database has seven tables. SQLAlchemy models are in `Backend/Models/`; migrations are under `Backend/alembic/versions/`.

| Table | Role |
|---|---|
| `users` | Account identity and password hash |
| `resumes` | User-owned uploaded PDF metadata and stored path |
| `candidate_profiles` | Mutable extracted/profile fields used by profile APIs and legacy resume analysis |
| `pipeline_runs` | One record per unified AI execution, lifecycle state, summary fields and canonical JSONB |
| `skill_gaps` | Optional compact coverage summary, at most one per pipeline run |
| `learning_tasks` | Mutable status/progress for roadmap items belonging to a specific run |
| `jobs` | User-owned occupation targets and supplied job description/skills; not live job listings |

### Key relationships

- `users` → `resumes`: one-to-many. Deleting a user cascades to their resumes.
- `users` → `candidate_profiles`: one-to-zero-or-one. The profile belongs to a user; its resume reference is optional.
- `users` → `pipeline_runs`: one-to-many. Runs are user-owned.
- `resumes` → `pipeline_runs`: one-to-many. A composite `(user_id, resume_id)` foreign key ensures the referenced resume belongs to the same user; deleting a resume with runs is restricted.
- `pipeline_runs` → `skill_gaps`: one-to-zero-or-one, unique by `pipeline_run_id`; deleting the run cascades to its summary.
- `pipeline_runs` → `learning_tasks`: one-to-many; deleting the run cascades to progress rows.
- `users` → `jobs`: one-to-many; deleting the user cascades to their jobs.

### Why the run is central

`pipeline_runs.canonical_output` is the authoritative detailed snapshot for that execution. It avoids duplicating every AI result as relational columns or separate result tables and preserves the exact output needed to serve different result views. `pipeline_runs` also holds lifecycle, ownership, error, and frequently queried summary values. `skill_gaps` is only a query-friendly summary—not another authoritative copy of all skill evidence. `learning_tasks` is relational because progress changes independently of the generated roadmap.

Roadmap item progress is unique within a run by `(pipeline_run_id, logical_item_key)`. The backend derives the key from phase number and stable skill URI, falling back to case-folded skill name, then hashes that identity. It intentionally excludes run ID and mutable status. Repeated same-skill items in one phase collapse to one logical progress task; different phases or distinct skill identities remain distinct. Each task also retains the original item JSON in `roadmap_item_data`.

`learning_tasks.status` is constrained to `not_started`, `in_progress`, or `completed`; `progress` is a bounded numeric percentage. The progress API updates these mutable columns without rewriting `roadmap_item_data` or the run's canonical roadmap. This keeps both the generated item and the user's latest progress available.

`candidate_profiles` remains useful for profile APIs and the legacy extraction flow. A profile snapshot is also present in canonical pipeline output, but it is a historical input/result snapshot rather than the mutable profile record. `jobs.required_skills` stores user-supplied JSON, but current job matching runs against the job's target ESCO occupation; custom required skills are not independently evaluated.

### Lifecycle and query implications

- Use the run's `user_id` to scope history and enforce ownership. Runs also point to the source resume, so the exact input remains traceable.
- Use `completed_at` and `created_at` for latest-result ordering; a latest endpoint should filter for completed runs and for the relevant result section when appropriate.
- The relational summary columns on a run support common filters and compact responses. Detailed skill match lists, readiness diagnostics, explanations, graph summary, and roadmap remain in JSONB.
- `skill_gaps` is optional because some pipeline outputs do not provide enough valid target/coverage data to make a summary row.
- A task belongs to one run, so progress is tied to the roadmap snapshot that produced it. A later analysis creates a separate set of tasks rather than silently changing the earlier run's progress.

## 5. Backend module responsibilities

| Area | Responsibility |
|---|---|
| `Backend/Main.py` | Creates the FastAPI application and registers API routers |
| `Backend/Api/profile.py` | Authentication, registration/login and user profile operations |
| `Backend/Api/resume.py` | Resume upload, ownership-aware retrieval and legacy analysis |
| `Backend/Api/skill_gaps.py` | Unified analysis requests, run history/results, skill evidence and graph-summary view |
| `Backend/Api/jobs.py` | User-owned job records, occupation matches and job-targeted pipeline runs |
| `Backend/Api/career_insights.py` | Saved readiness/SHAP results, recommendations, roadmap, resources and task progress |
| `Backend/Api/dashboard.py`, `Backend/Api/activity.py` | Dashboard and activity views over backend records |
| `Backend/Api/assistant.py` | Authenticated request validation; no functioning RAG/chat engine is currently connected |
| `Backend/Services/pipeline_service.py` | Ownership/file checks, AI invocation, run lifecycle, canonical persistence and failure handling |
| `Backend/Services/file_service.py` | Safe uploaded-file storage and removal |
| `Backend/Schemas/` | Pydantic request/response validation and serialization |
| `Backend/Core/` | Database session/base configuration and authentication/security utilities |

For exact routes, request/response schemas, status codes, and frontend examples, see [API_INTEGRATION_GUIDE.md](./API_INTEGRATION_GUIDE.md).

## 6. External AI resources and dependencies

### ESCO taxonomy

The taxonomy loader expects English CSV exports in `Datasets/Skill_Taxonomy/Raw/ESCO/`:

- `skills_en.csv`
- `skillGroups_en.csv`
- `skillSkillRelations_en.csv`
- `broaderRelationsSkillPillar_en.csv`
- `occupations_en.csv`
- `occupationSkillRelations_en.csv`

The loader uses these to normalize skills, resolve occupation matches, and provide occupation-skill requirements and relationships. The dataset-preparation documentation identifies the data as official ESCO v1.1. All six expected files were present during this reference update. The loader raises `FileNotFoundError` if the ESCO directory or required skills file is absent; missing other relation files are reported as loading errors and can reduce available taxonomy information.

### Readiness and runtime dependencies

- Saved readiness artifact: `AI/Readiness_Model/saved_models/readiness_classifier_pipeline.joblib`.
- Companion metadata: `AI/Readiness_Model/saved_models/model_metadata.json`.
- Metadata identifies a logistic-regression model, version `0.1.0-exploratory`, trained on dataset `M4.3-pilot-N71` with 71 samples. This is exploratory; the small sample and class imbalance limit confidence. Model artifact compatibility depends on compatible Python/scikit-learn/joblib versions.
- The pipeline also relies on the ESCO CSVs, resume-processing dependencies, pandas/NumPy/scikit-learn/SciPy, sentence-transformers, NetworkX, SHAP, and JSON-schema validation. Backend pins are maintained in `Backend/requirements.txt`; keep AI/runtime dependencies and artifact versions aligned when environments change.

These files are runtime inputs, not migrations or database seed data. Keep taxonomy exports and model assets in their expected locations when deploying; a valid database alone is not enough to make AI processing available. Ordinary API/database operations should not trigger model downloads or replace the saved artifact.

### Runtime configuration

- Runtime SQLAlchemy configuration reads `DATABASE_URL`; configure it for the intended PostgreSQL database before starting the API.
- Alembic uses its configured database URL, with `ALEMBIC_TEST_URL` available for test migration runs. Keep migration execution pointed at the same database that the application will use.
- Resume files are stored under the backend upload directory and are referenced by metadata in the database. Back up or retain both storage and database records together if resume persistence is required.
- Database setup commands and environment configuration belong in `Database/DATABASE_SETUP.md`; do not place real credentials in this reference or other committed documentation.

## 7. Implemented behavior and limitations

**Implemented:** authenticated ownership checks for user resources and pipeline runs; unified run creation and persisted lifecycle; canonical-result retrieval; occupation recommendations; matched/partial/missing skill evidence; readiness and explanations from saved output; roadmap retrieval and resources from saved output; task progress updates; basic dashboard/activity APIs.

**Limitations to remember:**

- Career readiness is experimental, based on a pilot dataset, and must not be presented as a validated hiring decision. Prediction probabilities and explanations inherit model/data limitations.
- AI stages can be incomplete or warning-producing; readiness, SHAP, graph, or roadmap data may be absent from an otherwise completed run.
- The knowledge-graph API returns the saved summary and a derived skill-match view, not a complete persisted graph topology.
- Job-specific `required_skills` are stored but matching uses the target ESCO occupation, not an independent comparison against those custom skills. The jobs table is not a job-board feed.
- Resume processing has no OCR fallback for image-only PDFs.
- Career Assistant currently returns an unavailable response (503); authentication and request validation do not imply that retrieval-augmented chat is implemented.
- `candidate_profiles.resume_id` is optional; the profile model does not itself enforce that the referenced resume is owned by the same user. Run-to-resume ownership is enforced separately by the composite foreign key and service checks.

The readiness metadata reports 71 training samples, and the saved estimator is experimental rather than a production-calibrated classifier. Historical model compatibility was not proven by reading metadata alone; upgrading scientific Python packages should be treated as an artifact compatibility change and validated against the actual saved model before deployment.

### Integration boundaries to preserve

- Bearer-token authentication is enforced by the API layer. The pipeline service additionally validates that the user owns the resume; a numeric resume or run ID is never authorization by itself.
- `PipelineRun.canonical_output` may contain extracted candidate-profile information. Treat it as user-sensitive data and return it only through ownership-checked routes.
- The legacy candidate-profile path and the unified pipeline path have different purposes. Avoid silently changing a profile endpoint to trigger AI analysis or to return a pipeline snapshot.
- The AI package returns a result object; backend routers expose selected typed response models for common views. The full saved run is available separately, so a response projection is not a second canonical contract.
- Error handling should preserve the difference between pipeline failure and absence of an optional output. Do not convert an unavailable readiness or explanation into a fabricated default prediction.

## 8. Decisions and context for future work

- Treat `PipelineRun` as the record of every unified AI execution. Use `canonical_output` for detailed historical results and the run columns for lifecycle and query-friendly summaries.
- Do not rerun AI to retrieve an existing result. A new analysis is a new run.
- Keep mutable roadmap progress in `learning_tasks`; do not overwrite the roadmap snapshot in canonical output when a user changes progress.
- Do not add result tables or duplicate full canonical sections without a concrete query, relationship, or lifecycle requirement.
- Backend development has kept `AI/` read-only. Changes to the AI output contract, taxonomy assets, or readiness artifact require coordinated integration and compatibility review.
- Backend tests belong under `Tests/Backend/`; AI assets/tests are separate and should remain untouched during backend-only changes.
- Database reference documentation is in `Database/`; the frontend API handoff is [API_INTEGRATION_GUIDE.md](./API_INTEGRATION_GUIDE.md). Prefer those sources for schema/setup and endpoint details rather than duplicating them here.
- When changing the canonical result shape, update the AI output contract, backend consumers/schemas, and representative saved-result tests together. Preserve optionality: not every run has every section.
- When adding a relational projection, identify its query or lifecycle need and define how it remains consistent with the canonical snapshot. Avoid treating duplicated summary data as a second source of truth.
- Distinguish the two matching concepts: occupation recommendations come from ESCO-based resume analysis, while a saved `Job` is a user-owned target used to request matching against that target occupation.
- Do not describe Career Assistant as retrieval-augmented until a real retrieval/chat implementation is connected and its behavior has been validated.
- Keep operational setup and table-level DDL in `Database/DATABASE_SETUP.md` and `Database/schema.sql`; those references should be checked against the current models and Alembic chain when the schema changes.
- SQLAlchemy model registration is centralized through `Backend/Models/__init__.py`, which is imported by Alembic configuration so model metadata is available to migrations.
- The pipeline/roadmap redesign intentionally replaced legacy skill-gap and task fields. Existing records were test data and did not impose a backward-compatibility requirement; schema evolution should continue through Alembic rather than a parallel database implementation.
- Keep endpoint count/path verification tied to the live OpenAPI document. Router aliases may exist for compatibility even when only one route is intentionally documented.
- Test ordinary backend behavior with isolated database fixtures and mocks for expensive model inference. Do not make routine API tests depend on downloading AI models or using production data.
