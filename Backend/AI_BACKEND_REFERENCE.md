# Road2Hire Backend and AI Reference

This document describes behavior verified in the current source tree. It distinguishes implemented backend behavior from capabilities described in project plans but not currently connected.

## 1. Project overview

Road2Hire is a career-readiness application. The FastAPI backend currently provides:

- Registration, login, JWT verification, and basic profile reads/updates.
- Resume PDF upload, metadata listing, download, and on-demand analysis.
- Skill-gap calculations using extracted resume skills and caller-supplied role requirements.
- Persistence and history for skill-gap results.
- Dashboard/activity summaries, readiness scores, and skill-gap-driven learning tasks.
- Occupation-level matches from local ESCO skill/occupation data.

The backend is not a general job-board, course catalogue, or conversational AI service. Several broader features described in the project README and architecture notes remain planned or depend on AI/frontend work; see [Implemented, pending, and future work](#15-implemented-pending-and-future-work).

## 2. Backend layout

| Path | Purpose |
|---|---|
| `Main.py` | Creates the FastAPI application, registers routers, and exposes root, health, and database-test routes. |
| `Api/auth.py` | Registration and login. |
| `Api/profile.py` | Current-user dependency and profile GET/PATCH. |
| `Api/resume.py` | Resume upload, listing router, download, analysis, and deletion. |
| `Api/skill_gaps.py` | Skill-gap calculation, persistence, cached results, and history. |
| `Api/dashboard.py` | Dashboard summary and activity derived from persisted records. |
| `Api/career_insights.py` | Career-readiness score and learning-roadmap construction. |
| `Api/tasks.py` | Learning-task progress updates. |
| `Api/jobs.py` | Occupation matches derived from ESCO skill mappings. |
| `Api/assistant.py` | Explicit unavailable response for the unintegrated career assistant. |
| `Models/` | SQLAlchemy models for users, resumes, skill-gap analyses, and learning tasks. |
| `Schemas/` | Pydantic request/response models used by auth, resume upload, task progress, and assistant input. |
| `Services/file_service.py` | Resume file creation, upload-directory path validation, and removal. |
| `Core/database.py` | `.env` loading, SQLAlchemy engine/session, and request-scoped database dependency. |
| `Core/security.py` | Password hashing/verification and JWT creation settings. |
| `alembic.ini`, `alembic/env.py`, `alembic/versions/` | Alembic configuration, model metadata loading, and versioned migrations. |
| `requirements.txt` | Backend dependency declarations; see [Configuration and dependency notes](#3-technology-stack-and-configuration). |

The AI code is in the repository-level `AI/` directory, not `Backend/`. Resume and skill-gap routes import selected AI functions directly.

## 3. Technology stack and configuration

| Concern | Current implementation |
|---|---|
| API | FastAPI with Pydantic request/response validation |
| Persistence | SQLAlchemy ORM; PostgreSQL is the configured target |
| Migrations | Alembic |
| Authentication | Bearer JWT, HS256, 60-minute expiration |
| Password storage | Passlib bcrypt context |
| PDF processing | PyMuPDF (`pymupdf`) |
| Local data | CSV mappings for learning resources, jobs, and ESCO skills/occupations; JSON skill graph |

`Backend/Core/database.py` calls `load_dotenv()` and reads `DATABASE_URL`. `Backend/Core/security.py` reads `SECRET_KEY`. Provide these variables in a local `Backend/.env`; do not commit real values. `Backend/.env.example` identifies the variable names without supplying credentials. The application constructs its engine at import time, so a missing or invalid `DATABASE_URL` can prevent imports and server startup.

The backend `requirements.txt` pins FastAPI, Uvicorn, Pydantic, and related packages, but does not declare every library imported by the source. In particular, the backend code also imports SQLAlchemy, Alembic, a PostgreSQL driver, python-dotenv, python-jose, Passlib/bcrypt, email-validator, and PyMuPDF. Confirm these are installed in the active environment. `AI/Skill_Extraction/skill_embeddings.py` additionally requires `sentence-transformers`; this helper is not used by the API and that package was not available in the inspected backend environment.

The sample `.env.example` contains variable names only. Never put actual passwords, token values, or signing keys in this document or in source control.

## 4. Activate and run on Windows

From PowerShell:

```powershell
Set-Location D:\Final_projext\Road2Hire\Backend
.\.venv\Scripts\Activate.ps1
uvicorn Main:app --reload
```

If PowerShell blocks activation, use the environment's executable directly:

```powershell
Set-Location D:\Final_projext\Road2Hire\Backend
.\.venv\Scripts\python.exe -m uvicorn Main:app --reload
```

Run from `Backend/` so `Main:app`, the local configuration, and the relative Alembic setup resolve as expected. The resume API adds the repository root to `sys.path` to import the repository-level `AI` package.

## 5. HTTP API reference

Unless noted otherwise, private endpoints require:

```http
Authorization: Bearer <access_token>
```

Examples below use placeholder values and illustrate response shapes; they are not real user records. Validation errors from FastAPI commonly use `422`. Endpoints do not all define explicit response schemas, so examples omit incidental fields where noted.

### Root, health, and database probe

| Method and path | Authentication | Behavior |
|---|---|---|
| `GET /` | None | Returns an API welcome message and running status. |
| `GET /health` | None | Returns `{"status":"healthy"}`. |
| `GET /db-test` | None | Executes `SELECT 1`; returns `{"database":"connected"}` on success or a failure object containing an error string. |

### Authentication and profile

| Method and path | Authentication | Request | Success / relevant errors |
|---|---|---|---|
| `POST /auth/register` | None | JSON: `{"name":"Example User","email":"person@example.test","password":"example-password"}` | `200` with `{"id":1,"name":"Example User","email":"person@example.test"}`. Duplicate email: `400`. Invalid email/body: `422`. |
| `POST /auth/login` | None | JSON: `{"email":"person@example.test","password":"example-password"}` | `200` with `{"access_token":"<token>","token_type":"bearer"}`. Invalid credentials: `401`. |
| `GET /profile` | Bearer token | No body | `200` with `{"id":1,"name":"Example User","email":"person@example.test"}`. |
| `PATCH /profile` | Bearer token | JSON with one or both mutable fields, e.g. `{"name":"Updated Name"}` or `{"email":"new@example.test"}` | `200` with updated profile. Empty body/no fields or empty/null value: `400`; duplicate email: `409`; invalid email: `422`. |

The slash variants `/profile/` are also registered but hidden from the generated OpenAPI schema; `/profile` is the documented path.

### Resumes

| Method and path | Authentication | Request | Success / relevant errors |
|---|---|---|---|
| `GET /resumes` | Bearer token | None | `200` with an array of the authenticated user's metadata: `id`, `user_id`, `original_name`, `stored_name`, `uploaded_at`, and `download_url`. |
| `POST /resume/upload` | **No authentication dependency is currently applied.** Requires multipart form fields `user_id` and `file`. | PDF upload, maximum 5 MiB; filename must end in `.pdf`, content type must be `application/pdf`, and bytes must start with `%PDF-`. | `200` with `{"message":"Resume uploaded successfully","resume":{...}}`. Unknown `user_id`: `404`; invalid PDF/name/content type/signature: `400`; too large: `413`; storage/database failure: `500`. |
| `GET /resume/{resume_id}/download` | Bearer token; resume must belong to the current user | Path ID | `200` PDF response. Unowned/missing resume or missing local file: `404`. |
| `GET /resume/{resume_id}/analysis` | Bearer token; resume must belong to the current user | Path ID | `200` with extraction, section, and skill fields described in [Resume processing](#8-resume-upload-storage-analysis-and-deletion). Missing resume/file: `404`; scanned PDF needing OCR or analysis input error: `422`; unexpected pipeline failure: `500`. |
| `DELETE /resumes/{resume_id}` | Bearer token; resume must belong to the current user | Path ID | `200` with `{"message":"Resume deleted successfully","resume_id":1}`. Missing/unowned resume: `404`; invalid stored path or file-removal/database problem: `500`. |

The upload route accepting an arbitrary form `user_id` without authenticating that user is current behavior, not an ownership guarantee. Do not treat that route as enforcing authenticated-user ownership.

Example list response:

```json
[
  {
    "id": 1,
    "user_id": 1,
    "original_name": "resume.pdf",
    "stored_name": "<generated-name>.pdf",
    "uploaded_at": "2026-01-01T12:00:00Z",
    "download_url": "/resume/1/download"
  }
]
```

The upload response uses `Schemas.resume.ResumeUploadResponse` and embeds a `ResumeResponse` containing `id`, `user_id`, `original_name`, `stored_name`, `file_path`, and `uploaded_at`. The listing deliberately does not return `file_path`.

### Skill-gap analysis and history

| Method and path | Authentication | Request | Success / relevant errors |
|---|---|---|---|
| `GET /skill-gaps/` | Bearer token; resume must belong to current user | Query parameters `resume_id`, `target_role`, and one or more repeated `required_skills` values | `200` saved analysis with `id`, `resume_id`, role, required/matched/missing skills, percentage `match_score`, `created_at`, and `cached`. Unknown/unowned resume or missing file: `404`; empty requirements/role: `422`; OCR required: `422`; calculation/database failure: `500`. |
| `GET /skill-gaps/history` | Bearer token | Optional `limit` (1–100, default 20) and `offset` (default 0) | `200` with `items`, `total`, `limit`, and `offset`. |
| `GET /skill-gaps/history/{analysis_id}` | Bearer token; analysis must belong to current user | Path ID | `200` analysis fields; missing/unowned analysis: `404`. |

Example request:

```text
GET /skill-gaps/?resume_id=1&target_role=Software%20Developer&required_skills=Python&required_skills=SQL
```

Example response:

```json
{
  "id": 3,
  "resume_id": 1,
  "target_role": "Software Developer",
  "required_skills": ["Python", "SQL"],
  "matched_skills": ["Python"],
  "missing_skills": ["SQL"],
  "match_score": 50.0,
  "created_at": "2026-01-01T12:00:00Z",
  "cached": false
}
```

### Dashboard, readiness, roadmap, and tasks

| Method and path | Authentication | Request | Success / relevant errors |
|---|---|---|---|
| `GET /dashboard` | Bearer token | None | `200` counts, average saved match score or `null`, latest resume, and latest skill-gap analysis (each latest item may be `null`). |
| `GET /activity` | Bearer token | Optional `limit` (1–100, default 20) | `200` with recent resume-upload, skill-gap-analysis, and non-default task-progress records; no synthetic events are created. |
| `GET /career-readiness` | Bearer token | None | `200` with latest saved skill-gap score as `score` or `null` when no analysis exists, plus its formula, role, and available analysis data. |
| `GET /learning-roadmap` | Bearer token | None | `200` with tasks generated from the latest analysis's missing skills, persisted progress, and any exactly matching CSV resources. Without analysis, returns an empty task list. Invalid saved missing-skill data: `500`; resource file unavailable/unreadable: `503`; task persistence failure: `409` or `500`. |
| `PATCH /tasks/{task_id}` | Bearer token; task must belong to current user | JSON with `status` (`not_started`, `in_progress`, `completed`) and/or `progress` (integer 0–100) | `200` with saved task state. No fields: `400`; null/inconsistent values: `422`; missing/unowned task: `404`; database failure: `500`. |

Example dashboard response:

```json
{
  "resume_count": 1,
  "skill_gap_count": 2,
  "average_match_score": 62.5,
  "latest_resume": {
    "id": 1,
    "original_name": "resume.pdf",
    "uploaded_at": "2026-01-01T12:00:00Z"
  },
  "latest_skill_gap": {
    "id": 3,
    "resume_id": 1,
    "target_role": "Software Developer",
    "match_score": 50.0,
    "created_at": "2026-01-01T12:00:00Z"
  }
}
```

Example task update:

```json
{"progress": 40}
```

When only `progress` is provided, the backend sets `not_started` for 0, `in_progress` for 1–99, and `completed` for 100. Explicit `completed` sets progress to 100; explicit `not_started` sets it to 0. A completed task cannot be sent with a non-100 progress value.

The readiness formula is inherited from the saved skill-gap analysis: `round(matched_required_skills / total_required_skills, 2) * 100`. It is a skill-match percentage, not a wider assessment of interviews, education, or employability.

The roadmap is based on verified `missing_skills`; a GET may create missing `learning_tasks` rows for that analysis. Resource records are loaded from `Datasets/Learning_Resources/Processed/Learning_Resources.csv` and matched by case-folded skill name. The inspected CSV contained a header and zero resource rows, so the current response reports `dataset_empty` and returns no course suggestions.

### Occupation matches and assistant

| Method and path | Authentication | Request | Success / relevant errors |
|---|---|---|---|
| `GET /jobs/matches` | Bearer token | Optional `limit` (1–50, default 10) | `200` with ESCO occupation matches based on matched skills in the user's latest saved analysis. No analysis or no mapped skills returns an empty list with a message. Missing/unreadable mapping data: `503`; invalid saved skill data: `500`. |
| `POST /assistant/messages` | Bearer token | JSON: `{"message":"How can I improve my skills?"}`; 1–4000 characters | Currently returns `503` with a configuration reason. It does not generate or store an assistant answer. Invalid request: `422`. |

Job matching is occupation matching, not matching to available job vacancies. The response has `match_type: "occupation"`, `data_source: "ESCO skill-to-occupation mapping"`, and `job_listings_available: false`. Match score is the percentage of distinct ESCO skill IDs for an occupation that intersect the candidate's mapped skill IDs. The repository's job metadata CSV was empty when inspected.

The assistant's current `503` body is shaped like:

```json
{
  "detail": {
    "message": "Career assistant is not configured.",
    "reason": "The repository contains a skill knowledge graph and embedding helper, but no retrieval corpus, RAG/chat pipeline, or configured local language model.",
    "accepted_message_length": 25
  }
}
```

The accepted message text is not echoed back.

## 6. Authentication and ownership

- Registration hashes the submitted password and returns only `id`, `name`, and `email`; the stored model field is `password_hash`.
- Login verifies the password and issues a JWT with the user's email in `sub`. `Core/security.py` uses HS256 and a 60-minute expiration.
- `Api.profile.get_current_user` extracts a Bearer token, decodes it with the configured secret/algorithm, resolves the current user by email, and returns `401` for invalid/expired tokens or a missing user. With the default `HTTPBearer` behavior, an absent authorization header is rejected before the dependency runs.
- Profile, resume listing/download/analysis/deletion, skill-gap, dashboard, activity, readiness, roadmap, task, job-match, and assistant routes use this current-user dependency.
- Private resume/analysis/task queries include the authenticated user's ID in the lookup. Skill-gap history and dashboard queries are similarly scoped.
- **Exception:** `POST /resume/upload` currently accepts a `user_id` form field and checks only that the user exists; it has no JWT/current-user dependency. The caller can select a different existing account ID.
- Since the JWT subject is an email, after changing an account email, sign in again to obtain a token with the new subject.

## 7. PostgreSQL, ORM models, and migrations

### Models and relationships

| Table | Current columns and constraints | Links |
|---|---|---|
| `users` | `id`, `name`, `email` (unique/indexed), `password_hash` | Parent of resumes, skill gaps, and tasks through foreign keys. |
| `resumes` | `id`, `user_id`, `original_name`, `stored_name` (unique), `file_path`, `uploaded_at` | `user_id` references `users.id` with `ON DELETE CASCADE`. |
| `skill_gaps` | `id`, `user_id`, `resume_id`, `target_role`, `requirements_hash`, JSON `required_skills` / `matched_skills` / `missing_skills`, `match_score`, `created_at` | User and resume foreign keys cascade on delete. Unique constraint: `(resume_id, target_role, requirements_hash)`. |
| `learning_tasks` | `id`, `user_id`, `skill_gap_id`, `skill_name`, `status`, `progress`, `created_at`, `updated_at` | User and skill-gap foreign keys cascade on delete. Status and progress have database checks; `(skill_gap_id, skill_name)` is unique. |

The SQLAlchemy models are in `Models/`; `Models/__init__.py` imports them so Alembic can populate `Base.metadata`. `get_db()` creates one `SessionLocal` session per dependency call and closes it when the request finishes.

### Database and Alembic workflow

Set `DATABASE_URL` for the SQLAlchemy engine before starting the app. Alembic reads its migration connection from `sqlalchemy.url` in `alembic.ini`; ensure it targets the intended database. The Alembic environment also imports `Core.database`, so the environment configuration must be available when Alembic loads.

From `Backend/` with dependencies installed:

```powershell
alembic current
alembic heads
alembic upgrade head
```

To create a migration after a model change:

```powershell
alembic revision --autogenerate -m "describe the schema change"
```

Review generated operations before applying them. The checked-in chain includes revisions for resumes, skill gaps, and learning tasks. The initial `a2ba68957958_create_users_table.py` revision currently has `pass` in both `upgrade()` and `downgrade()`; it does not create the `users` table. A clean database therefore needs a valid users-table creation/provisioning step before dependent migrations can succeed. Confirm the actual PostgreSQL schema and Alembic target before upgrading; this reference does not apply migrations.

## 8. Resume upload, storage, analysis, and deletion

1. The upload handler receives a multipart `user_id` and PDF file. It checks the `.pdf` suffix, `application/pdf` content type, a filename length limit of 255 characters, a maximum size of 5 MiB, and the `%PDF-` signature.
2. `Services/file_service.py` writes bytes into `Backend/uploads/` under a generated UUID filename. The `resumes` row stores the original name, generated stored name, absolute file path, user ID, and upload time. If the metadata insert fails, the handler rolls back and attempts to remove the written file.
3. `GET /resumes` returns metadata for the authenticated user. `GET /resume/{resume_id}/download` and `GET /resume/{resume_id}/analysis` require ownership.
4. Analysis calls `AI.Resume_Processing.resume_pipeline.process_resume(file_path)` and then `AI.Skill_Extraction.skill_extractor.extract_skills(result)`. The response includes resume ID/name/status, pipeline version, extraction status, page count, sections, detected section names, extracted skills, count, and extraction method.
5. `DELETE /resumes/{resume_id}` checks ownership and validates that the resolved file path is directly inside the configured upload directory before deleting metadata and then the local file. The resume foreign key cascade removes its skill-gap rows; skill-gap cascade removes associated learning tasks.

PDF processing extracts selectable text. Encrypted PDFs are unsupported; scanned/image-only PDFs produce `needs_ocr` and the API returns `422` because OCR is not integrated. The analysis route does not persist its extraction output; saved skill-gap analyses are persisted separately by `GET /skill-gaps/`.

## 9. AI integration contracts and limitations

### Resume processing modules

| Module/function | Input | Output / behavior |
|---|---|---|
| `AI.Resume_Processing.pdf_extractor.extract_resume_text(pdf_path)` | String or `Path` to a PDF | Dict with `source_file`, `page_count`, page-level text, cleaned full `text`, `character_count`, and `extraction_status` (`success` or `needs_ocr`). Invalid path/type/PDF errors are raised. |
| `AI.Resume_Processing.section_detector.detect_resume_sections(text)` | Extracted text string | Dict with recognized `sections`, original `detected_headings`, `detected_section_names`, `section_count`, and `detection_method`. Heading matching is rule-based. |
| `AI.Resume_Processing.resume_pipeline.process_resume(pdf_path)` | String or `Path` to a PDF | Combines PDF and section outputs; adds `pipeline_version: "1.0.0"`. This is the function called by resume analysis and skill-gap calculation. |
| `AI.Resume_Processing.resume_pipeline.save_resume_json(resume_data, output_path)` | Pipeline result dict and destination | Writes UTF-8 JSON and returns the destination `Path`. It is not used by the API routes. |

`AI.Skill_Extraction.skill_extractor.extract_skills(resume_data, vocabulary=None)` expects a dict containing a `sections` mapping. It checks rule-based whole-phrase matches in skills, experience, projects, summary, education, and certifications. The default vocabulary is loaded from `AI/Knowledge_Graph/skill_graph_v1.json`; the checked-in graph has five named skills. Results contain `source_file`, `extraction_method: "knowledge_graph_keyword_matching"`, a `skills` list, and `skill_count`. Each skill item contains a canonical `skill`, source sections, and occurrence locations/text.

`normalize_skill_name(skill_name, vocabulary=None)` canonicalizes known names/aliases, and `load_skill_vocabulary(graph_path=...)` loads graph skill names. The extractor also recognizes configured aliases including `ML` for Machine Learning and common Scikit-learn spellings. This is vocabulary-based keyword extraction, not a learned resume-understanding model.

### Skill matching and occupation mapping

`AI.Baseline.keyword_baseline.keyword_match(candidate_skills, required_skills)` takes two lists of strings and performs case-insensitive exact string matching. Its result contains `present_skills`, `missing_skills`, and fractional `match_score` rounded to two decimals. `/skill-gaps/` converts that fractional score to a percentage and compares requirements supplied in query parameters; it does not obtain role requirements from the job-description dataset.

`AI.Skill_Extraction.skill_taxonomy_mapper.map_skills_to_esco(extracted_skills, mapping_path=...)` enriches skill dicts using `Datasets/Skill_Taxonomy/Processed/Road2Hire_ESCO_Mapping.csv`. The inspected mapping has five Road2Hire entries, two with ESCO IDs and three marked unmapped. `GET /jobs/matches` separately joins case-insensitive names/IDs against `Datasets/ESCO_ONET/Mappings/ESCO_Skill_Mapping.csv` to calculate occupation overlap. This is occupation-level data, not vacancy data.

`AI.Skill_Extraction.skill_embeddings.generate_skill_embeddings(skills, model_name="sentence-transformers/all-MiniLM-L6-v2")` returns the model name, embedding dimension, and per-skill vectors; `cosine_similarity(first_embedding, second_embedding)` compares vectors after validating dimensions/non-zero inputs. This module imports Sentence Transformers, but it is not wired into the current resume, skill-gap, or jobs APIs. The package/model availability is not guaranteed by the backend dependency file.

## 10. Skill-gap persistence, cache, and history

`GET /skill-gaps/` checks that the requested resume belongs to the current user and that its file exists. It then computes a SHA-256 key from:

- The current resume file bytes.
- The case-folded target role.
- The sorted, case-folded required-skill list.

If a saved row for that user's resume and hash exists, it returns it with `cached: true`. Otherwise it processes the resume, extracts candidate skills, runs exact keyword matching, stores the result in `skill_gaps`, and returns `cached: false`. Changing the resume content or analysis inputs results in a different cache key.

`GET /skill-gaps/history` returns paginated user-owned rows. `GET /skill-gaps/history/{analysis_id}` returns one analysis only if it belongs to the current user. Deleting a resume cascades to its skill-gap rows through the database foreign key.

## 11. Learning roadmap and task progress

`GET /learning-roadmap` selects the current user's latest saved skill-gap record. For each distinct missing skill it creates a `learning_tasks` row if one does not already exist for that analysis/skill, then returns task ID, skill name, status, progress, and resources looked up by exact case-insensitive skill name.

`PATCH /tasks/{task_id}` updates only a task owned by the authenticated user. `status` is restricted to `not_started`, `in_progress`, or `completed`; progress is restricted to 0–100. When only progress is sent, the route derives the matching status. When a status is sent, completion is set to 100 and not-started to 0; contradictory explicit values are rejected. `GET /activity` includes tasks with non-default progress/status.

The task table ties progress to one skill-gap analysis, not to an independently curated course plan. Current learning-resource data contains no rows, so course recommendations are not available from the checked-in dataset.

## 12. Career assistant status

`POST /assistant/messages` validates a 1–4000 character message and requires authentication, but it intentionally raises `503 Service Unavailable`. The repository contains a small skill graph and a standalone embedding helper; current backend source contains no retrieval corpus/index, RAG orchestration, chat model client, or configured local language model. The endpoint does not return generated advice. A usable assistant requires those resources/dependencies and an explicit integration contract before implementation.

## 13. Tests and Swagger

The repository's `Tests/Backend/` currently contains only `.gitkeep`; no backend API test suite is checked in. AI tests exist under `Tests/AI/`, but they are outside the backend folder.

Example AI tests from the repository root (after installing the project's required test and runtime dependencies):

```powershell
python -m pytest Tests\AI\test_resume_processing.py Tests\AI\test_skill_extractor.py
```

For manual API testing:

1. Set local configuration and start the server as in [Activate and run on Windows](#4-activate-and-run-on-windows).
2. Open `http://127.0.0.1:8000/docs`.
3. Call `POST /auth/register`, then `POST /auth/login`.
4. Use the returned bearer token in Swagger's **Authorize** dialog for protected endpoints.
5. Upload a small valid PDF using `POST /resume/upload`; the current API asks for `user_id` plus the file as multipart fields.
6. Exercise listing/download/analysis, then call `GET /skill-gaps/` with repeated `required_skills` query values. Check the saved history, readiness, roadmap, and task patch routes.
7. Expect `GET /jobs/matches` to return occupation matches where mapped skills overlap, not job listings. Expect `POST /assistant/messages` to return `503` until the assistant is integrated.

The examples and Swagger describe the application contract; successful database-backed calls still require a reachable PostgreSQL instance with the expected schema.

## 14. Environment and troubleshooting

| Symptom | Check |
|---|---|
| Import/startup error mentioning `DATABASE_URL` or engine creation | Confirm `Backend/.env` is present, the variable is set to a valid SQLAlchemy PostgreSQL URL, and the PostgreSQL driver is installed. The engine is created at import time. |
| Authentication fails after changing email | Login again; tokens use the email as `sub`, and each request looks up the user by that subject. Confirm `SECRET_KEY` is consistent across app restarts/workers. |
| Alembic cannot connect or targets the wrong database | Check the Alembic `sqlalchemy.url` configuration and `DATABASE_URL`; `alembic.ini` and SQLAlchemy application configuration are separate inputs. Do not paste credentials into logs or documentation. |
| Fresh-database migration reports a missing `users` table | The initial users migration is currently empty. Provision/create the users table using an approved schema migration before applying dependent resume/skill-gap migrations. |
| Resume upload rejects a file | Verify suffix, multipart content type, size (at most 5 MiB), and the PDF header. |
| Resume analysis says OCR is required | The current extractor reads selectable PDF text only; OCR is not integrated. |
| Resume record exists but download/analysis says file missing | Check that its file still exists under `Backend/uploads/` and that the DB path points to it. |
| Roadmap has no resources | The checked-in learning-resource CSV currently has zero rows; do not substitute invented courses. |
| Occupation matches are empty or incomplete | Candidate skills must match available ESCO mappings; only two of the five curated Road2Hire skills were mapped in the inspected file. Job listings are not present in the inspected job metadata CSV. |
| Assistant returns `503` | This is expected until retrieval, model resources, dependencies, and chat orchestration are connected. |
| AI embedding helper cannot import | Its `sentence-transformers` dependency is separate from the API integration and is absent from the inspected backend environment. |

## 15. Implemented, pending, and future work

### Implemented in the current backend

- FastAPI app and health/database-probe routes.
- Registration/login, bearer JWT verification, and profile GET/PATCH.
- PDF upload, resume metadata list, authenticated download/analysis, and owned deletion with upload-directory path validation.
- Resume text extraction, rule-based section detection, and graph-vocabulary skill extraction.
- User-owned skill-gap computation, hash-based cache lookup, persistence, and history.
- Dashboard/activity summaries, persisted task progress, latest-analysis career-readiness score, and skill-gap-driven roadmap tasks.
- ESCO occupation-level overlap matches.

### Pending or limited

- Resume upload must be authenticated and bound to the authenticated user rather than accepting a caller-chosen `user_id`.
- The `users` table creation migration is a no-op; clean-database provisioning is incomplete in the checked-in migration chain.
- Learning-resource CSV is empty, so the roadmap currently has tasks without course resources.
- Job-description metadata is empty, so job matching is occupation-level ESCO data rather than active job opportunities.
- OCR for scanned resumes is not integrated.
- Semantic embeddings are not connected to API matching and their dependency/model availability is not part of the backend configuration.
- The assistant route is a validated, authenticated placeholder that returns `503`; no RAG/chat pipeline is wired.
- No backend API tests are checked in. The frontend teammate owns the UI integration; API connectivity and shared live behavior must be verified separately.

### Future work requiring explicit implementation

- Add and test an authenticated upload contract.
- Add a reviewed users-table migration and validate the complete migration chain against an empty PostgreSQL database.
- Populate and maintain verified learning resources and job/occupation requirements with provenance.
- Define whether career readiness should include more than the current saved skill-match percentage.
- Integrate retrieval and a supported model for the assistant only after the corpus, dependencies, runtime resources, safety behavior, and request/response contract are available.
- Add backend tests for authorization/ownership, file lifecycle, caching, migrations, and the current API response contracts.
