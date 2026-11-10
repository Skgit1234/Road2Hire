# Road2Hire frontend API integration guide

This guide describes the FastAPI routes currently registered in `Backend/Main.py`, as verified against the generated OpenAPI schema. Example values are illustrative and are not user data. Fields such as uploaded file paths and pipeline output are shown as placeholders or representative objects.

## A. Backend setup and base URL

The API has no global `/api` prefix. For local development, start it from `Backend/` after configuring the backend environment:

```powershell
.\.venv\Scripts\python.exe -m uvicorn Main:app --reload
```

The usual local base URL is `http://localhost:8000`; confirm the actual host and port used by the running server. OpenAPI/Swagger is exposed at `/docs`, and the OpenAPI JSON is at `/openapi.json`.

The backend reads `DATABASE_URL` and `SECRET_KEY` from its environment (or local `Backend/.env`). Do not put either value in frontend code. The current `Main.py` does not install CORS middleware. For cross-origin local development, use a same-origin frontend proxy or configure an approved CORS policy in the backend before browser requests; do not assume cross-origin calls are enabled.

Operational endpoints are listed at the end of the guide.

## B. Authentication and JWT usage

Registration and login are public. Other application endpoints use HTTP Bearer authentication through the `get_current_user` dependency. Login returns a bearer token; send it on each authenticated request:

```http
Authorization: Bearer <access_token>
```

The JWT is signed with HS256, expires after 60 minutes, and identifies the account by email in its `sub` claim. Store it using the frontend's approved secure session strategy; do not log or commit it. The API does not expose a refresh-token endpoint.

Typical authentication failures are `401 Unauthorized` for an invalid/expired token or a token whose user is no longer present. FastAPI's HTTP Bearer dependency may also return `403` if the Authorization header is absent.

## C. Endpoint reference

Unless specified otherwise, request-body validation errors return `422`. Authenticated endpoints scope data to the current user's account; foreign or nonexistent resources are generally reported as `404` to avoid disclosing another user's records.

### 1. Authentication

#### `POST /auth/register`

- **Authentication:** Not required.
- **Body:** `UserCreate` JSON. Required: `name` (string), `email` (valid email string), `password` (string).
- **Success:** `200`, `UserResponse`.
- **Errors:** `400` if the email is already registered; `422` for invalid/missing fields. Database failures may surface as server errors.
- **Behavior:** Password is hashed before persistence; `password_hash` is never returned.

Request:

```json
{"name":"Taylor Example","email":"taylor@example.test","password":"<password>"}
```

Representative response:

```json
{"id":12,"name":"Taylor Example","email":"taylor@example.test"}
```

#### `POST /auth/login`

- **Authentication:** Not required.
- **Body:** `UserLogin` JSON with required `email` and `password`.
- **Success:** `200`.
- **Errors:** `401` for invalid email/password; `422` for malformed body/email.

Request and response:

```json
{"email":"taylor@example.test","password":"<password>"}
```

```json
{"access_token":"<JWT returned by this response>","token_type":"bearer"}
```

Use the returned token in the Bearer header for all authenticated endpoints.

### 2. User profiles

#### `GET /profile`

- **Authentication:** Required.
- **Parameters/body:** None.
- **Success:** `200`, `ProfileResponse`: `{ "id": integer, "name": string, "email": string }`.
- **Errors:** Authentication errors.

#### `PATCH /profile`

- **Authentication:** Required.
- **Body:** `ProfileUpdate`; optional `name` and/or `email` strings. Send at least one field. Fields cannot be `null` or blank. Email is validated as an email address.
- **Success:** `200`, updated `ProfileResponse`.
- **Errors:** `400` if no fields are supplied or a value is blank; `409` if the email is already in use; `422` for schema validation; database errors may surface as server errors.

Request:

```json
{"name":"Taylor Example"}
```

#### `GET /profile/candidate`

- **Authentication:** Required.
- **Parameters/body:** None.
- **Success:** `200`, `CandidateProfileResponse`: profile `id`, `user_id`, nullable `resume_id`, `skills`, `education`, `experience`, `projects`, `certifications`, and `updated_at`.
- **Errors:** `404` if no extracted candidate profile exists; `500` if the profile query fails; authentication errors.
- **Note:** This is the latest extracted profile snapshot, not an individual pipeline-run result.

Representative response:

```json
{
  "id": 8,
  "user_id": 12,
  "resume_id": 31,
  "skills": [
    {
      "skill": "Python",
      "source_sections": ["skills"],
      "occurrences": [{"section":"skills","text":"Python","start":0,"end":6}]
    }
  ],
  "education": ["BSc Computer Science"],
  "experience": ["Software developer"],
  "projects": [],
  "certifications": [],
  "updated_at": "2026-11-10T10:00:00Z"
}
```

### 3. Resume management

#### `POST /resume/upload`

- **Authentication:** Required.
- **Content type:** `multipart/form-data`.
- **Fields:** `user_id` (required form integer) and `file` (required upload). `user_id` must equal the authenticated user's ID.
- **Success:** `200`, `ResumeUploadResponse` containing `message` and a `resume` object (`id`, `user_id`, `original_name`, `stored_name`, `file_path`, `uploaded_at`).
- **Errors:** `400` for non-PDF extension, non-`application/pdf` content type, filename longer than 255 characters, or invalid `%PDF-` signature; `403` if `user_id` is not the authenticated user; `413` if larger than 5 MiB; `500` for storage/database failures; `422` for missing/invalid multipart fields; authentication errors.
- **Important:** Maximum accepted size is 5 MiB (5 * 1024 * 1024 bytes). Use `FormData`; do not manually set the multipart `Content-Type` boundary. The response schema includes `file_path`, which is backend storage metadata; do not display or depend on it in the UI.

Example:

```js
const form = new FormData();
form.append("user_id", String(currentUser.id));
form.append("file", file);
await fetch(`${API_BASE}/resume/upload`, {
  method: "POST",
  headers: { Authorization: `Bearer ${token}` },
  body: form
});
```

Illustrative response shape:

```json
{
  "message": "Resume uploaded successfully",
  "resume": {
    "id": 31,
    "user_id": 12,
    "original_name": "resume.pdf",
    "stored_name": "<server-generated-name>",
    "file_path": "<backend-managed-storage-path>",
    "uploaded_at": "2026-11-10T10:00:00Z"
  }
}
```

#### `GET /resumes`

- **Authentication:** Required.
- **Parameters/body:** None.
- **Success:** `200`, array of resume metadata: `id`, `user_id`, `original_name`, `stored_name`, `uploaded_at`, and `download_url`.
- **Errors:** Authentication errors.
- **Ordering:** Newest `uploaded_at` first. There is no pagination.

#### `GET /resume/{resume_id}/download`

- **Authentication:** Required; only the owner can download.
- **Path:** `resume_id` integer.
- **Success:** `200`, PDF file response (`application/pdf`).
- **Errors:** `404` if the resume is not owned/found or the backing file is missing; `422` for an invalid path parameter; authentication errors.

#### `DELETE /resumes/{resume_id}`

- **Authentication:** Required; only the owner can delete.
- **Path:** `resume_id` integer.
- **Success:** `200`, `{ "message": "Resume deleted successfully", "resume_id": integer }`.
- **Errors:** `404` if not owned/found; `500` for invalid stored file path, database deletion failure, or file-removal failure; `422` for an invalid path parameter; authentication errors.
- **History behavior:** A resume referenced by pipeline-run history may be protected by the database's `ON DELETE RESTRICT` constraint; a resulting database error is returned as `500`. Do not assume resume deletion removes analysis history.

#### `GET /resume/{resume_id}/analysis`

- **Authentication:** Required; only the owner can analyze.
- **Path:** `resume_id` integer.
- **Success:** `200`, an untyped JSON object with `resume_id`, `original_name`, `status`, `pipeline_version`, `extraction_status`, `page_count`, `sections`, `detected_section_names`, `extracted_skills`, `skill_count`, and `skill_extraction_method`.
- **Errors:** `404` if resume/file is unavailable; `422` if OCR is needed or parsing fails; `500` for other analysis/persistence errors; authentication errors.
- **Important:** This legacy extraction endpoint updates the latest `candidate_profiles` snapshot. It is separate from the unified pipeline-run workflow at `POST /skill-gaps/analyze` and does not provide the unified run's analysis-history contract.

### 4. Skill-gap analysis and history

#### `POST /skill-gaps/analyze`

- **Authentication:** Required.
- **Body:** `SkillGapAnalysisRequest`: `resume_id` (positive integer) and either `target_occupation` (nonblank string, max 512 characters) or `auto_select_top_occupation: true`. `auto_select_top_occupation` defaults to `false`.
- **Success:** `200`, `SkillGapAnalysisResponse` with `pipeline_run_id`, `status`, `matching_basis`, `warnings`, `target_occupation`, `skill_gap`, `learning_roadmap`, `knowledge_graph`, and `error`.
- **Errors:** `422` for invalid body or invalid resume path; `404` if the resume is not owned/found; `500` for an unhandled pipeline invocation error; authentication errors.
- **Important:** `200` means the request was processed and a response was returned. Check `status`: the stored pipeline run may be `completed` or `failed`. A structured pipeline failure is represented in the response's `error`; it is not necessarily an HTTP error.
- **Ownership:** Resume must belong to the authenticated user.

Explicit-target request:

```json
{"resume_id":31,"target_occupation":"Data Engineer"}
```

Automatic occupation-selection request:

```json
{"resume_id":31,"auto_select_top_occupation":true}
```

Representative response:

```json
{
  "pipeline_run_id": 104,
  "status": "completed",
  "matching_basis": "Unified AI pipeline skill matching against ESCO occupation requirements.",
  "warnings": [],
  "target_occupation": {"preferred_label":"Data Engineer","uri":"<ESCO URI>"},
  "skill_gap": {"matched_skills":[],"partially_matched_skills":[],"missing_essential_skills":[]},
  "learning_roadmap": {},
  "knowledge_graph": {},
  "error": null
}
```

Canonical output sections can be absent or null depending on the result; use the corresponding retrieval endpoints for typed readiness, explanation, recommendation, and roadmap responses.

#### `GET /skill-gaps/`

- **Authentication:** Required.
- **Query:** Required `resume_id` (positive integer), `target_role` (nonblank, up to 512 characters); optional repeated `required_skills` string query parameters.
- **Success:** `200`, same `SkillGapAnalysisResponse` shape as analysis.
- **Errors:** `404` resume not found/owned; `422` invalid query or resume file; `500` pipeline invocation failure; authentication errors.
- **Important:** This GET route invokes the unified pipeline; it is not a read-only cached lookup. Custom `required_skills` are not independently evaluated by the pipeline. If supplied, a warning is included and matching still uses ESCO occupation requirements. Prefer the POST endpoint for new analyses.

Example:

```text
GET /skill-gaps/?resume_id=31&target_role=Data%20Engineer&required_skills=Python&required_skills=SQL
```

#### `GET /skill-gaps/history`

- **Authentication:** Required.
- **Query:** `limit` optional, default 20, range 1–100; `offset` optional, default 0, minimum 0.
- **Success:** `200`, `SkillGapHistoryResponse`: `items`, `total`, `limit`, `offset`. Items include run ID (`id`), `resume_id`, `status`, target occupation URI/title, coverage scores, readiness class, and timestamps.
- **Errors:** `422` for invalid pagination values; authentication errors.
- **Behavior:** History is pipeline-run history for the authenticated user, across statuses; it is not restricted to completed runs.

#### `GET /skill-gaps/history/{analysis_id}`

- **Authentication:** Required.
- **Path:** `analysis_id` is the pipeline-run ID.
- **Success:** `200`, `SkillGapAnalysisResponse`.
- **Errors:** `404` if the run is not owned/found; `422` for invalid path parameter; authentication errors.

#### `GET /skill-gaps/runs/{run_id}`

- **Authentication:** Required; run ownership enforced.
- **Path:** `run_id` integer.
- **Success:** `200`, `PipelineRunResultResponse`: `pipeline_run_id`, `status`, `resume_id`, full `canonical_output` object, and nullable `error`.
- **Errors:** `404` if run is not owned/found; `422` for invalid path parameter; authentication errors.
- **Use:** Retrieve the complete saved canonical result or inspect a failed/running run. This route does not rerun inference.

#### `GET /skill-gaps/runs/{run_id}/priorities`

- **Authentication:** Required; run ownership enforced.
- **Path:** `run_id` integer.
- **Success:** `200`, `SkillPriorityResponse`: `pipeline_run_id`, nullable `target_occupation`, flattened roadmap `items` with phase number/name added.
- **Errors:** `404` if run is not owned/found; `422` for invalid path parameter; authentication errors.
- **Behavior:** Items are taken from the saved canonical roadmap; they are not recalculated.

#### `GET /skill-gaps/runs/{run_id}/knowledge-graph`

- **Authentication:** Required; run ownership enforced.
- **Path:** `run_id` integer.
- **Success:** `200`, `KnowledgeGraphResponse`: `pipeline_run_id`, graph `summary`, `nodes`, `relationships`, and a `scope` description.
- **Errors:** `404` if run is not owned/found; `422` for invalid path parameter; authentication errors.
- **Important:** The endpoint returns canonical graph summary information and derives skill-match nodes/relationships from matched and partially matched skill-gap evidence. The complete graph topology is not stored or returned.

### 5. Job creation and job matching

#### `POST /jobs`

- **Authentication:** Required.
- **Body:** `JobCreate`: required `title` (1–255 chars), `description` (nonblank string), `target_occupation` (1–512 chars), optional `required_skills` array (defaults to empty). Each requirement has `skill_name` (1–255 chars), `importance` (`essential` or `optional`, default `essential`), and nullable `canonical_uri` (max 512 chars).
- **Success:** `201`, `JobResponse` with job fields, owner ID and timestamps.
- **Errors:** `422` for validation; `500` if job persistence fails; authentication errors.

Request:

```json
{
  "title":"Data Engineer",
  "description":"Build and maintain data systems.",
  "target_occupation":"Data Engineer",
  "required_skills":[
    {"skill_name":"Python","importance":"essential","canonical_uri":null}
  ]
}
```

#### `GET /jobs`

- **Authentication:** Required.
- **Parameters/body:** None.
- **Success:** `200`, array of the current user's `JobResponse` records, newest first. No pagination.
- **Errors:** Authentication errors.

#### `GET /jobs/{job_id}`

- **Authentication:** Required; only the owner can retrieve the job.
- **Path:** `job_id` integer.
- **Success:** `200`, `JobResponse`.
- **Errors:** `404` if not owned/found; `422` for invalid path parameter; authentication errors.

#### `GET /jobs/matches`

- **Authentication:** Required.
- **Query:** Optional `resume_id` (positive integer); optional `limit`, default 10, range 1–50.
- **Success:** `200`, `OccupationMatchesResponse`: nullable `analysis_id`, `candidate_skills`, `matches`, `message`.
- **Errors:** `404` if a supplied resume is not owned/found; `422` for invalid query; authentication errors.
- **Behavior:** Reads the newest **completed** pipeline run, optionally filtered to the owned resume. If there is no completed run it returns `200` with `analysis_id: null`, empty arrays, and a message to run matching first.
- **Matching distinction:** `matches` are saved ESCO occupation recommendations from the pipeline, not live job listings.

#### `POST /jobs/{job_id}/matches`

- **Authentication:** Required; job and resume ownership are enforced.
- **Path:** `job_id` integer.
- **Body:** `JobMatchRequest`: required positive integer `resume_id`.
- **Success:** `200`, `JobMatchingResponse` containing `job`, `run`, `matching_basis`, and `job_specific_required_skills_applied`.
- **Errors:** `404` if job or resume is not owned/found; `422` if the resume path is invalid or body invalid; `500` for unexpected matching failure; authentication errors.
- **Pipeline status:** The response can still be `200` with a run whose `status` is `failed`; inspect `run.status` and error fields.
- **Important distinction:** The API runs the unified pipeline with the saved job's `target_occupation`. The job's custom `required_skills` are not applied as independent matching criteria; `job_specific_required_skills_applied` is `false`. The matching basis is ESCO occupation matching, not an evaluation against arbitrary job requirements.

### 6. Career readiness

#### `GET /career-readiness`

- **Authentication:** Required.
- **Parameters/body:** None.
- **Success:** `200`, `CareerReadinessPredictionResponse`.
- **Errors:** `404` if there is no completed run with readiness data; `503` if saved readiness fields are malformed; authentication errors.
- **Behavior:** Returns the latest completed run containing readiness data; does not execute the pipeline.

#### `GET /career-readiness/runs/{run_id}`

- **Authentication:** Required; run ownership enforced.
- **Path:** `run_id` integer.
- **Success:** `200`, same readiness response.
- **Errors:** `404` if run is not owned/found or readiness is unavailable; `409` if the owned run is not completed; `503` if stored readiness data is invalid; `422` invalid path; authentication errors.

Response fields: `pipeline_run_id`, `resume_id`, nullable `completed_at`, `predicted_class`, `class_probabilities`, nullable `model_version`, `model_type`, `is_experimental`, `is_ood`, `ood_warnings`, `pipeline_warnings`, nullable `training_sample_count`, `training_class_distribution`, `feature_values`, `feature_diagnostics`, and `limitations`.

Representative response:

```json
{
  "pipeline_run_id":104,
  "resume_id":31,
  "completed_at":"2026-11-10T10:05:00Z",
  "predicted_class":"Developing",
  "class_probabilities":{"Developing":0.72,"Job Ready":0.21,"Not Ready":0.07},
  "model_version":"0.1.0-exploratory",
  "model_type":"logistic_regression",
  "is_experimental":true,
  "is_ood":false,
  "ood_warnings":[],
  "pipeline_warnings":[],
  "training_sample_count":71,
  "training_class_distribution":{"Developing":52,"Job Ready":16,"Not Ready":3},
  "feature_values":{"skills_count":8.0},
  "feature_diagnostics":{},
  "limitations":["Illustrative model limitation."]
}
```

### 7. SHAP feature explanations

#### `GET /career-readiness/explanations`

- **Authentication:** Required.
- **Parameters/body:** None.
- **Success:** `200`, `FeatureExplanationResponse`.
- **Errors:** `404` if no completed run with explanations; `503` if saved explanation data is invalid; authentication errors.
- **Behavior:** Reads the latest saved completed run; no SHAP recomputation.

#### `GET /career-readiness/runs/{run_id}/explanations`

- **Authentication:** Required; run ownership enforced.
- **Path:** `run_id` integer.
- **Success:** `200`, same explanation response.
- **Errors:** `404` if run is not owned/found or explanations are missing; `409` if the run is not completed; `503` if stored explanation data is invalid; `422` invalid path; authentication errors.

Response fields: `pipeline_run_id`, `resume_id`, `target_class_explained`, `base_value`, `top_positive_factors`, `top_negative_factors`, `feature_contributions`, `human_readable_summary`, `waterfall_steps`, `global_importance_ranking`, and `limitations`.

Representative response:

```json
{
  "pipeline_run_id":104,
  "resume_id":31,
  "target_class_explained":"Developing",
  "base_value":0.4,
  "top_positive_factors":[{"feature_name":"skills_count","contribution":0.12}],
  "top_negative_factors":[],
  "feature_contributions":[{"feature_name":"skills_count","contribution":0.12}],
  "human_readable_summary":"Illustrative explanation summary.",
  "waterfall_steps":[],
  "global_importance_ranking":[{"feature_name":"skills_count","importance":0.2}],
  "limitations":[]
}
```

### 8. Career recommendations

#### `GET /recommendations`

- **Authentication:** Required.
- **Parameters/body:** None.
- **Success:** `200`, `CareerRecommendationsResponse`.
- **Errors:** `404` if no completed run or occupation recommendations are unavailable; `503` if saved canonical output is invalid; authentication errors.
- **Behavior:** Latest completed pipeline run; no inference.

#### `GET /recommendations/runs/{run_id}`

- **Authentication:** Required; run ownership enforced.
- **Path:** `run_id` integer.
- **Success:** `200`, same recommendation response.
- **Errors:** `404` if run is not owned/found or recommendations are absent; `409` if run is not completed; `503` invalid saved output; `422` invalid path; authentication errors.

Response fields: `pipeline_run_id`, nullable `target_occupation`, `recommendations` array, `candidate_skills` array, and nullable `skill_gap`.

Representative response:

```json
{
  "pipeline_run_id":104,
  "target_occupation":{"preferred_label":"Data Engineer"},
  "recommendations":[{"preferred_label":"Data Engineer","score":0.82}],
  "candidate_skills":[{"skill_name":"Python"}],
  "skill_gap":{"matched_skills":[],"missing_essential_skills":[]}
}
```

### 9. Learning roadmap, phases, items and resources

All endpoints below require authentication and enforce ownership of `run_id`. They read the roadmap from the completed run's `canonical_output`; they do not rerun the pipeline.

#### `GET /learning-roadmap`

- **Parameters/body:** None.
- **Success:** `200`, `LearningRoadmapResponse`.
- **Errors:** `404` if no completed run or its roadmap is missing; `409` if an explicitly requested run is not completed (not applicable to this latest-run route); `503` for invalid saved roadmap; `500` if roadmap task preparation fails; authentication errors.
- **Behavior:** Uses the latest completed run. The handler also creates any missing `LearningTask` progress rows from canonical roadmap items. Repeated reads avoid duplicate task rows by the database uniqueness constraint.

#### `GET /learning-roadmap/runs/{run_id}`

- **Path:** `run_id` integer.
- **Success:** `200`, `LearningRoadmapResponse`.
- **Errors:** `404` if run is not owned/found or roadmap is unavailable; `409` if the run is not completed; `503` invalid roadmap; `500` task persistence error; `422` invalid path; authentication errors.

#### `GET /learning-roadmap/runs/{run_id}/phases/{phase_number}`

- **Path:** `run_id` integer; `phase_number` integer from 1 through 4.
- **Success:** `200`, `RoadmapPhaseResponse`.
- **Errors:** `422` if phase number is outside 1–4 or path validation fails; `404` if the run/phase is unavailable; `409` if the run is not completed; `503` invalid saved roadmap; `500` task persistence error; authentication errors.

#### `GET /learning-roadmap/runs/{run_id}/items/{logical_item_key}`

- **Path:** `run_id` integer; `logical_item_key` string (URL-encode it).
- **Success:** `200`, `RoadmapItemResponse`.
- **Errors:** `404` for missing run/item; `409` if the run is not completed; `503` invalid roadmap; `500` task persistence error; `422` invalid path; authentication errors.

#### `GET /learning-roadmap/runs/{run_id}/resources`

- **Path:** `run_id` integer.
- **Success:** `200`, array of `RoadmapResourcesResponse`, one per item.
- **Errors:** `404` missing run/roadmap; `409` if run is not completed; `503` invalid roadmap; `500` task persistence error; `422` invalid path; authentication errors.

#### `GET /learning-roadmap/runs/{run_id}/items/{logical_item_key}/resources`

- **Path:** `run_id` integer; `logical_item_key` string (URL-encode it).
- **Success:** `200`, one `RoadmapResourcesResponse`.
- **Errors:** `404` missing run/item; `409` if run is not completed; `503` invalid roadmap; `500` task persistence error; `422` invalid path; authentication errors.

The roadmap response includes `pipeline_run_id`, nullable target occupation title/URI, nullable `total_roadmap_skills` and `total_estimated_weeks`, `phases`, and `disclaimers`. A phase has `phase_number`, `phase_name`, `description`, `estimated_weeks`, and `items`. An item combines the saved AI roadmap data with progress: `logical_item_key`, phase fields, skill name/URI, priority, `roadmap_item_data`, current status, rationale/outcome/activities/project/duration/prerequisites/completion criteria/resource categories, mutable `status`, `progress`, `task_id`, and `updated_at`.

Representative item and resource shapes:

```json
{
  "logical_item_key":"phase:1:skill:<sha256>",
  "roadmap_phase_number":1,
  "roadmap_phase_name":"Foundations",
  "skill_name":"Python",
  "skill_uri":"<ESCO URI>",
  "priority":"Critical",
  "roadmap_item_data":{"skill_name":"Python"},
  "current_status":"missing_essential",
  "importance_rationale":"Supports the target occupation.",
  "learning_outcome":"Build working knowledge.",
  "suggested_activities":["Practice an exercise."],
  "practical_project":"Build a small API.",
  "estimated_duration_weeks":"2",
  "prerequisites":[],
  "completion_criteria":"Complete the project.",
  "resource_categories":[{"category":"documentation"}],
  "status":"not_started",
  "progress":0,
  "task_id":209,
  "updated_at":"2026-11-10T10:00:00Z"
}
```

Resource endpoints return only canonical `resource_categories`, `suggested_activities`, `practical_project`, `learning_outcome`, and `completion_criteria`; they do not create external URLs.

### 10. Learning tasks

#### `GET /tasks`

- **Authentication:** Required; tasks are scoped through their owning pipeline run.
- **Query:** Optional `pipeline_run_id` positive integer.
- **Success:** `200`, array of `LearningTaskResponse`, ordered by roadmap phase and task ID.
- **Errors:** `422` for invalid query; authentication errors.
- **Fields:** `id`, `pipeline_run_id`, `logical_item_key`, roadmap phase number/name, skill name/URI, priority, `status`, `progress`, `roadmap_item_data`, `updated_at`.

#### `GET /tasks/{task_id}`

- **Authentication:** Required; task's run must belong to the user.
- **Path:** `task_id` integer.
- **Success:** `200`, `LearningTaskResponse`.
- **Errors:** `404` if task is not owned/found; `422` invalid path; authentication errors.

#### `PATCH /tasks/{task_id}`

- **Authentication:** Required; task ownership enforced through `pipeline_runs`.
- **Path:** `task_id` integer.
- **Body:** `TaskProgressUpdate`, optional `status` (`not_started`, `in_progress`, `completed`) and/or `progress` integer 0–100. At least one field must be provided. `null` values are rejected by the handler.
- **Success:** `200`, updated `LearningTaskResponse`.
- **Errors:** `400` if no fields supplied; `404` task not owned/found; `422` for invalid status, out-of-range progress, null value, or malformed request; `500` if database update fails; authentication errors.
- **Behavior:** Status and progress are stored as supplied; the API does not automatically infer one from the other.

Request:

```json
{"status":"in_progress","progress":35}
```

### 11. Dashboard and activity

#### `GET /dashboard`

- **Authentication:** Required.
- **Parameters/body:** None.
- **Success:** `200`, dashboard object with `resume_count`, `skill_gap_count`, nullable `average_match_score`, nullable `latest_resume`, and nullable `latest_skill_gap`.
- **Errors:** Authentication errors; database failures may surface as server errors.
- **Behavior:** `skill_gap_count` counts completed pipeline runs. `average_match_score` is the average completed run's overall coverage converted to a percentage. Latest resume/run may be null for a new user.

#### `GET /activity`

- **Authentication:** Required.
- **Query:** `limit`, default 20, range 1–100.
- **Success:** `200`, `{ "items": [...], "limit": integer }`. Activity item types are `resume_uploaded`, `skill_gap_analyzed`, and `task_progress_updated`. A pipeline-run activity includes status; task activity includes run ID, skill, status, and progress.
- **Errors:** `422` invalid limit; authentication errors.
- **Ordering:** Combined events are sorted newest first and truncated to the requested limit. Only tasks with progress above zero or status other than `not_started` appear.

### 12. Career Assistant

#### `POST /assistant/messages`

- **Authentication:** Required.
- **Body:** `AssistantMessageRequest`: `message`, required string length 1–4000.
- **Success:** No successful assistant response is currently implemented.
- **Errors:** `503` for every valid request because no RAG retrieval pipeline or configured local language model is available; `422` for invalid message; authentication errors.
- **Behavior:** The response explains that the assistant is not configured and returns the accepted message length. The backend does not currently answer the question, retrieve a knowledge base, or generate chat content.

Request:

```json
{"message":"What skills should I build next?"}
```

Representative current response (`503`):

```json
{
  "detail": {
    "message":"Career assistant is not configured.",
    "reason":"The repository contains a skill knowledge graph and embedding helper, but no retrieval corpus, RAG/chat pipeline, or configured local language model.",
    "accepted_message_length":32
  }
}
```

## D. Pagination and filtering

| Endpoint | Behavior |
|---|---|
| `GET /skill-gaps/history` | `limit` defaults to 20 (1–100), `offset` defaults to 0; returns total count and pagination values. |
| `GET /activity` | `limit` defaults to 20 (1–100); no offset. |
| `GET /jobs/matches` | `limit` defaults to 10 (1–50); optional owned `resume_id`. |
| `GET /tasks` | Optional `pipeline_run_id`; no limit/offset. |
| `GET /jobs`, `GET /resumes` | Owner-filtered, newest first; no pagination. |
| Other list/result endpoints | No pagination unless noted. |

Query-list parameters such as `required_skills` on `GET /skill-gaps/` are passed as repeated keys, e.g. `?required_skills=Python&required_skills=SQL`.

## E. Pipeline workflow and `pipeline_run_id`

1. Authenticate and upload a resume; retain the returned `resume.id`.
2. Start a unified analysis using `POST /skill-gaps/analyze` (or `POST /jobs/{job_id}/matches` for a saved job's target occupation).
3. Save the returned `pipeline_run_id`. Immediately inspect `status`.
4. If `status` is `completed`, use that ID for run-specific readiness, explanations, recommendations, roadmap, graph and full-result calls.
5. If `status` is `failed`, use `GET /skill-gaps/runs/{run_id}` to inspect the structured error and canonical output. Do not treat HTTP 200 alone as success.
6. To later recover an ID, call `GET /skill-gaps/history`; the history includes runs of all statuses. `GET /skill-gaps/history/{analysis_id}` returns the corresponding analysis summary.
7. Roadmap reads persist progress-task rows as needed. Update those rows through `PATCH /tasks/{task_id}` and retain `task_id` or `logical_item_key` for UI state.

The canonical AI result is saved once in `pipeline_runs.canonical_output`. Typed feature routes expose selected sections without recalculating the pipeline. The `skill_gaps` table is a summary; detailed matched/partial/missing skill data is in canonical output.

### Latest versus run-specific endpoints

| Latest available completed run | Specific run |
|---|---|
| `GET /career-readiness` | `GET /career-readiness/runs/{run_id}` |
| `GET /career-readiness/explanations` | `GET /career-readiness/runs/{run_id}/explanations` |
| `GET /recommendations` | `GET /recommendations/runs/{run_id}` |
| `GET /learning-roadmap` | `GET /learning-roadmap/runs/{run_id}` |
| `GET /jobs/matches` (latest run, optionally by resume) | No direct job-match retrieval by `run_id`; use `/skill-gaps/runs/{run_id}` for saved canonical output. |

Latest endpoints do not accept a `run_id`. For any run-specific route, the run must belong to the authenticated user and generally must be completed for typed result sections. The all-run result and history routes can also return in-progress or failed runs.

## F. Complete user journey

1. `POST /auth/register` to create the account; then `POST /auth/login` and retain the returned bearer token.
2. Call `GET /profile` and optionally `PATCH /profile`.
3. Upload a PDF with `POST /resume/upload`, including the authenticated user's `user_id`; optionally inspect `GET /resumes`.
4. Run `POST /skill-gaps/analyze` with the resume ID and target occupation, or request automatic occupation selection. Save `pipeline_run_id`, inspect `status`, and present warnings/errors appropriately.
5. Optionally create a user-owned job using `POST /jobs`, then call `POST /jobs/{job_id}/matches` with the resume ID. This creates a pipeline run for the job's target occupation; it does not apply the job's arbitrary custom skill list as independent criteria.
6. Display ESCO occupation recommendations with `GET /jobs/matches` or `GET /recommendations/runs/{run_id}`.
7. Show readiness and saved SHAP explanations from `/career-readiness/runs/{run_id}` and `/career-readiness/runs/{run_id}/explanations`.
8. Fetch `/learning-roadmap/runs/{run_id}`; roadmap items include progress fields and task IDs. Resource and phase/item endpoints are optional detail views.
9. Update progress with `PATCH /tasks/{task_id}`. Refresh tasks or the roadmap response to show the persisted progress.
10. Use `GET /dashboard` and `GET /activity` for summary views.

## G. Loading, failed runs, missing data and errors

- Treat a pipeline call as asynchronous work from the user's perspective even though the current route responds in the same HTTP request. Show a loading state while the request is pending.
- On a `200` analysis/matching response, check `status`. Only show completed predictions and recommendations when status is `completed`; for `failed`, display a safe failure state and optionally retrieve the run detail.
- Preserve `pipeline_run_id` as soon as received so the user can navigate away and return to history.
- A `404` on a latest-result endpoint usually means no completed run or that output section is unavailable. Offer the user a way to upload/analyze a resume rather than treating it as a fatal application failure.
- A `409` on a specific result route means the run exists for the user but is not completed yet.
- A `422` usually indicates invalid request data, an invalid file, or invalid path/query values. Map field validation details to the form.
- A `401`/`403` indicates missing/invalid authentication; send the user through the appropriate authentication flow.
- A `500`/`503` should be handled as server-side failure. Do not expose stack traces, internal paths, database errors, or raw exception details in the UI.
- Several response fields are nullable or conditionally absent: profile `resume_id`; dashboard latest records and average score; run occupation/readiness/error fields; readiness model metadata, OOD state and training sample count; recommendation target/skill gap; roadmap target and totals. Render empty/loading/unknown states for them.
- `resource_categories` and activities are categories/text supplied by canonical output; the API does not promise external resource links.

## H. Hidden slash aliases

The following compatibility paths are registered by route decorators but intentionally excluded from OpenAPI. Use the canonical documented paths above; aliases are noted for existing clients:

| Hidden alias | Canonical OpenAPI path |
|---|---|
| `GET /profile/` | `GET /profile` |
| `PATCH /profile/` | `PATCH /profile` |
| `GET /resumes/` | `GET /resumes` |
| `POST /jobs/` | `POST /jobs` |
| `GET /jobs/` | `GET /jobs` |

These are slash variants, not different operations. The canonical OpenAPI schema is the contract for new frontend integration.

## I. Operational endpoints

These root-level routes are also registered in OpenAPI. They do not require authentication:

| Method and path | Success response | Notes |
|---|---|---|
| `GET /` | `200` `{ "message": "Welcome to Road2Hire API", "status": "running" }` | Basic app response. |
| `GET /health` | `200` `{ "status": "healthy" }` | Process-level health response; does not verify database connectivity. |
| `GET /db-test` | `200` `{ "database": "connected" }` or `{ "database": "failed", "error": "<database error>" }` | Database probe. It reports failure in the JSON body without changing the HTTP status. Not intended as a user-facing UI endpoint. |

## Endpoint summary

| Module | Method | Path | Auth | Success |
|---|---|---|---|---|
| Authentication | POST | `/auth/register` | No | 200 |
| Authentication | POST | `/auth/login` | No | 200 |
| User profiles | GET | `/profile` | Yes | 200 |
| User profiles | PATCH | `/profile` | Yes | 200 |
| User profiles | GET | `/profile/candidate` | Yes | 200 |
| Resume management | POST | `/resume/upload` | Yes | 200 |
| Resume management | GET | `/resumes` | Yes | 200 |
| Resume management | GET | `/resume/{resume_id}/download` | Yes | 200 |
| Resume management | DELETE | `/resumes/{resume_id}` | Yes | 200 |
| Resume management | GET | `/resume/{resume_id}/analysis` | Yes | 200 |
| Skill gaps | POST | `/skill-gaps/analyze` | Yes | 200 |
| Skill gaps | GET | `/skill-gaps/` | Yes | 200 |
| Skill gaps | GET | `/skill-gaps/history` | Yes | 200 |
| Skill gaps | GET | `/skill-gaps/history/{analysis_id}` | Yes | 200 |
| Skill gaps | GET | `/skill-gaps/runs/{run_id}` | Yes | 200 |
| Skill gaps | GET | `/skill-gaps/runs/{run_id}/priorities` | Yes | 200 |
| Skill gaps | GET | `/skill-gaps/runs/{run_id}/knowledge-graph` | Yes | 200 |
| Job matching | POST | `/jobs` | Yes | 201 |
| Job matching | GET | `/jobs` | Yes | 200 |
| Job matching | GET | `/jobs/{job_id}` | Yes | 200 |
| Job matching | GET | `/jobs/matches` | Yes | 200 |
| Job matching | POST | `/jobs/{job_id}/matches` | Yes | 200 |
| Career readiness | GET | `/career-readiness` | Yes | 200 |
| Career readiness | GET | `/career-readiness/runs/{run_id}` | Yes | 200 |
| SHAP explanations | GET | `/career-readiness/explanations` | Yes | 200 |
| SHAP explanations | GET | `/career-readiness/runs/{run_id}/explanations` | Yes | 200 |
| Recommendations | GET | `/recommendations` | Yes | 200 |
| Recommendations | GET | `/recommendations/runs/{run_id}` | Yes | 200 |
| Learning roadmap | GET | `/learning-roadmap` | Yes | 200 |
| Learning roadmap | GET | `/learning-roadmap/runs/{run_id}` | Yes | 200 |
| Learning roadmap | GET | `/learning-roadmap/runs/{run_id}/phases/{phase_number}` | Yes | 200 |
| Learning roadmap | GET | `/learning-roadmap/runs/{run_id}/items/{logical_item_key}` | Yes | 200 |
| Learning roadmap | GET | `/learning-roadmap/runs/{run_id}/resources` | Yes | 200 |
| Learning roadmap | GET | `/learning-roadmap/runs/{run_id}/items/{logical_item_key}/resources` | Yes | 200 |
| Learning tasks | GET | `/tasks` | Yes | 200 |
| Learning tasks | GET | `/tasks/{task_id}` | Yes | 200 |
| Learning tasks | PATCH | `/tasks/{task_id}` | Yes | 200 |
| Dashboard/activity | GET | `/dashboard` | Yes | 200 |
| Dashboard/activity | GET | `/activity` | Yes | 200 |
| Career Assistant | POST | `/assistant/messages` | Yes | 503 (current implementation) |
| Operations | GET | `/` | No | 200 |
| Operations | GET | `/health` | No | 200 |
| Operations | GET | `/db-test` | No | 200 |

## Frontend integration checklist

- [ ] Configure the API base URL per environment; do not hardcode secrets.
- [ ] Send `Authorization: Bearer <token>` on every authenticated request.
- [ ] Handle `401`/`403` globally and never log token values.
- [ ] Upload resumes with `FormData`, include `user_id`, and validate PDF type/5 MiB limit before submission.
- [ ] Retain the returned `pipeline_run_id` and branch UI behavior on its `status`, not just HTTP status.
- [ ] Use run-specific endpoints for stable historical views; latest endpoints may select a newer completed run later.
- [ ] Distinguish saved-job target-occupation matching from custom job skill evaluation; the latter is not implemented.
- [ ] Expect nullable and optional result fields; avoid assuming a profile, completed run, prediction, explanation, or roadmap exists.
- [ ] Use resource categories and activity/project text as returned; do not manufacture resource URLs.
- [ ] Treat roadmap GETs as potentially writing initial task-progress rows.
- [ ] Validate task status/progress client-side but still handle backend `400`, `404`, `422`, and `500`.
- [ ] Present Career Assistant as unavailable (`503`) until a chat/RAG implementation exists.
- [ ] Confirm CORS or use a same-origin proxy for browser-based cross-origin requests.

## OpenAPI verification

This guide's canonical operation paths and request media types were checked against `app.openapi()` from the current `Backend/Main.py`. Hidden slash aliases are separately identified because `include_in_schema=False` excludes them from OpenAPI. To inspect the live contract, use `/openapi.json` or `/docs`.
