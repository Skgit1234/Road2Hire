# Road2Hire M1 integration contracts

This document describes the active source in this worktree. It is based on
static inspection of `Backend/Main.py`, registered routers, schemas, processing
modules, and `Frontend/lib/api-client.ts`; it does not claim live behavior.

## API configuration and cross-origin access

The frontend reads `NEXT_PUBLIC_API_BASE_URL`, falling back to
`http://127.0.0.1:8000`. Protected API calls send
`Authorization: Bearer <access_token>`. The current browser session is held in
memory and is lost on reload.

`Backend/Main.py` registers the auth, profile, resume, skill-gap,
career-insights, task, and dashboard routers. CORS allows origins
`http://localhost:3000` and `http://127.0.0.1:3000`, methods GET, POST, PATCH,
DELETE, and OPTIONS, and headers Authorization, Content-Type, and Accept.
Credentials are disabled.

## Registered endpoints

The following endpoints are registered in the active application. Unless
indicated otherwise, protected endpoints require a bearer token and scope data
to its authenticated user.

| Method and path | Contract | Authentication |
| --- | --- | --- |
| `GET /` | Welcome message and running status. | None |
| `GET /health` | `{"status":"healthy"}`. | None |
| `POST /auth/register` | JSON `{name, email, password}`; returns `{id, name, email}`. | None |
| `POST /auth/login` | JSON `{email, password}`; returns `{access_token, token_type:"bearer"}`. | None |
| `GET /profile` | Returns `{id, name, email}`. | Bearer token |
| `PATCH /profile` | JSON with optional `name` and/or `email`; returns profile. | Bearer token |
| `POST /resume/upload` | Multipart `file` and optional integer `user_id`; returns `{message, resume}` with `id`, `user_id`, `original_name`, `stored_name`, and `uploaded_at`. `file_path` is excluded by `ResumeUploadResponse`. | Bearer token; if `user_id` is supplied it must equal the authenticated user's ID (otherwise 403). |
| `GET /resumes` | Authenticated user's resume list; each record has `id`, `user_id`, `original_name`, `stored_name`, `uploaded_at`, and `download_url`. | Bearer token |
| `DELETE /resumes/{resume_id}` | Returns `{message, resume_id}` for an owned resume. | Bearer token |
| `GET /resume/{resume_id}/download` | Streams the owned PDF. | Bearer token |
| `GET /resume/{resume_id}/analysis` | Returns resume metadata, extracted text sections, detected section names, keyword-extracted skills, count, and processing method. | Bearer token |
| `GET /skill-gaps/?resume_id=…&target_role=…&required_skills=…` | `required_skills` is repeatable. Returns saved/computed match arrays, percentage score, timestamp, and `cached`. | Bearer token; resume ownership checked |
| `GET /skill-gaps/history?limit=…&offset=…` | Returns `{items, total, limit, offset}` for the authenticated user. | Bearer token |
| `GET /skill-gaps/history/{analysis_id}` | Returns one owned skill-gap result. | Bearer token |
| `GET /career-readiness` | Latest score and contributing skills, or nullable score and message when there is no analysis. | Bearer token |
| `GET /learning-roadmap` | Latest analysis/role, tasks and resource availability. With no analysis, returns null analysis/role and no tasks. | Bearer token |
| `PATCH /tasks/{task_id}` | JSON optional `status` (`not_started`, `in_progress`, `completed`) and/or integer `progress` from 0 to 100; returns the updated task progress. | Bearer token; task ownership checked |
| `GET /dashboard` | Counts, average match score, and nullable latest resume and skill-gap summary. | Bearer token |
| `GET /activity?limit=20` | `{items, limit}` containing recent resume, skill-gap, and task-progress activity. | Bearer token |

Jobs matching (`/jobs/matches`) and Career Assistant (`/assistant/messages`)
are planned or unavailable: neither endpoint is registered in the active
`Backend/Main.py` routers. They must not be treated as implemented contracts.

FastAPI validation may return 422; routes also raise endpoint-specific errors,
including 400, 401, 403, 404, 409, 413, and 500. Several handlers return dynamic
dictionaries without explicit Pydantic response models, so their response shapes are
not fully represented in OpenAPI. Follow-up: define and attach response models for
these dynamic endpoints; this is not implemented in this integration audit. Example
bodies below are illustrative only; they are not live response captures.

### Illustrative upload example

Request (bearer header omitted from this snippet):

```http
POST /resume/upload
Content-Type: multipart/form-data
```

Illustrative response body:

```json
{
  "message": "Resume uploaded successfully",
  "resume": {
    "id": 12,
    "user_id": 4,
    "original_name": "resume.pdf",
    "stored_name": "<generated-name>.pdf",
    "uploaded_at": "<server timestamp>"
  }
}
```

The upload validates a `.pdf` filename, `application/pdf` content type,
filename length (maximum 255 characters), size (maximum 5 MiB), and `%PDF-`
signature. The optional `user_id` is checked against the authenticated user;
the record always uses that authenticated user's ID.

## Resume processing: current and planned

The current analysis route uses the local PDF processing baseline:

1. PyMuPDF extracts text from PDF pages. A PDF without extractable text returns
   422 because OCR is not implemented.
2. `section_detector.py` detects known section headings using rules and groups
   text under detected sections.
3. `skill_extractor.py` finds vocabulary and alias matches in eligible
   sections. This is keyword-based extraction, not verified structured fact
   extraction.

Analysis runs on request and is not itself saved as a distinct analysis record.
Skill-gap results are saved and may be reused for matching inputs. Neither
processing path invokes an embedding model, LLM, or RAG service.

The frontend's `resume-extraction-contract.ts` describes a richer planned
structured extraction contract with evidence, confidence, field states,
warnings, provenance, and structured contact, education, experience, and
project fields. The current backend analysis response does not implement those
fields. Do not present keyword matches as verified structured resume facts.

The Career Assistant page is a browser-only demonstration with predefined
responses; it makes no assistant API call. A RAG-based Career Assistant is
planned and unavailable; no assistant route is registered or called by the
current API client.

The dashboard page and the skill-gap page also contain explicitly labeled
sample previews. Live account summaries and submitted skill-gap requests use
the backend API client. The resume API client currently supports upload,
listing, and analysis only. Although the backend provides authenticated
download and delete routes, the frontend has no API-client functions or UI
actions for those operations.

## Database diagnostic route

`GET /db-test` is not registered. The unused diagnostic route was removed
because it was unauthenticated and returned raw database exception text. The
`GET /health` endpoint remains available as a process liveness check and does
not query the database.

`Backend/Core/database.py` requires `DATABASE_URL` during import. The current
`Backend/alembic/env.py` uses that value and does not read `ALEMBIC_TEST_URL`;
the blank URL in `alembic.ini` is not an alternate connection source.

All four migration files are present in this candidate. Their linear revision chain is
`a2ba68957958` (users) -> `65a1c0d4b2e8` (resumes) ->
`e629ccef0ddf` (skill gaps) -> `c1d47f2a8b60` (learning tasks).
The users root migration creates the users table and its ID and unique-email
indexes. The three downstream migrations create their tables, foreign keys,
indexes, and constraints. Each file matches the verified source ref
`origin/8-m1_backend-set-up` at `1cc5b60524e10b5d783bcff0d972ddf410b3843f`.
Alembic `heads` and `history` checks discovered one head at
`c1d47f2a8b60`; these were static discovery checks and did not connect to a
database or execute migration operations.

Backend/Core/database.py requires DATABASE_URL at import. This candidate
has no Backend/.env, and no DATABASE_URL or ALEMBIC_TEST_URL is set in
the current process. The original database's owner-reported revision and
users-table state do not establish the identity or state of an isolated test
database. PostgreSQL upgrade, downgrade, re-upgrade, and schema verification
remain blocked until a dedicated disposable PostgreSQL target is configured
and positively verified as isolated and empty. No credentials belong in this
document.

## Static verification boundary

The latest focused command
`python -m pytest Tests/Backend/test_api_contracts.py -q -p no:cacheprovider`
passed **26 tests** using an existing isolated Python environment. These are static
route/OpenAPI checks and in-process tests with dependency overrides; they do not
connect to PostgreSQL. No server was started and no migration was run.

Live database connectivity and persistence have not been verified. The local PDF
processing path has not been validated against live service infrastructure, and
AI/RAG integration remains unverified and unavailable: the active processing route
uses local extraction and keyword matching, while the Career Assistant has no
registered backend route. These checks do not establish live database or AI/RAG
behavior.
