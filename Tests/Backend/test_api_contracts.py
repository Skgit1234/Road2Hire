"""Database-independent FastAPI contract tests using dependency overrides."""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPOSITORY_ROOT / "Backend"
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(BACKEND_ROOT))

# Importing Main constructs an engine but does not connect. Tests replace the
# request database dependency with an in-memory fake before sending requests.
_previous_database_url = os.environ.get("DATABASE_URL")
_previous_secret_key = os.environ.get("SECRET_KEY")
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "database-independent-test-key-for-tests-only-2026"

from Api import jobs as jobs_api  # noqa: E402
from Api import resume as resume_api  # noqa: E402
from Api.profile import get_current_user  # noqa: E402
from Core.database import get_db  # noqa: E402
from Main import app  # noqa: E402

if _previous_database_url is None:
    os.environ.pop("DATABASE_URL", None)
else:
    os.environ["DATABASE_URL"] = _previous_database_url
if _previous_secret_key is None:
    os.environ.pop("SECRET_KEY", None)
else:
    os.environ["SECRET_KEY"] = _previous_secret_key


class EmptyQuery:
    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def first(self):
        return None

    def all(self):
        return []

    def count(self):
        return 0

    def offset(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def scalar(self):
        return None


class EmptyDatabase:
    def query(self, *_args, **_kwargs):
        return EmptyQuery()

    def add(self, _item):
        pass

    def flush(self):
        pass

    def commit(self):
        pass

    def refresh(self, _item):
        pass

    def rollback(self):
        pass


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = EmptyDatabase
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def authenticate_as(client):
    user = SimpleNamespace(id=7, name="Test User", email="test@example.test")
    app.dependency_overrides[get_current_user] = lambda: user
    return user


def test_registered_routes_and_openapi_upload_schema(client):
    schema = app.openapi()
    paths = schema["paths"]
    expected = {
        ("post", "/auth/register"),
        ("post", "/auth/login"),
        ("get", "/profile"),
        ("patch", "/profile"),
        ("post", "/resume/upload"),
        ("get", "/resumes"),
        ("delete", "/resumes/{resume_id}"),
        ("get", "/resume/{resume_id}/analysis"),
        ("get", "/resume/{resume_id}/download"),
        ("get", "/skill-gaps/"),
        ("post", "/skill-gaps/analyze"),
        ("get", "/skill-gaps/history"),
        ("get", "/skill-gaps/history/{analysis_id}"),
        ("get", "/skill-gaps/runs/{run_id}"),
        ("get", "/career-readiness"),
        ("get", "/career-readiness/runs/{run_id}"),
        ("get", "/recommendations/runs/{run_id}"),
        ("get", "/learning-roadmap"),
        ("get", "/learning-roadmap/runs/{run_id}"),
        ("patch", "/tasks/{task_id}"),
        ("get", "/dashboard"),
        ("get", "/activity"),
    }
    register = paths["/auth/register"]["post"]
    assert register["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith("/UserCreate")
    assert register["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/UserResponse")
    assert set(schema["components"]["schemas"]["UserCreate"]["properties"]) == {"name", "email", "password"}
    assert set(schema["components"]["schemas"]["UserResponse"]["properties"]) == {"id", "name", "email"}
    assert "password" not in schema["components"]["schemas"]["UserResponse"]["properties"]
    registered = {
        (method, path)
        for path, operations in paths.items()
        for method in operations
    }
    assert expected <= registered
    assert "/jobs/matches" in paths
    assert "/assistant/messages" in paths

    upload = paths["/resume/upload"]["post"]
    assert "multipart/form-data" in upload["requestBody"]["content"]
    assert upload["security"]
    for schema_name in ("ResumeResponse", "ResumeUploadResponse"):
        assert "file_path" not in schema["components"]["schemas"][schema_name]["properties"]


def test_protected_profile_rejects_missing_and_invalid_bearer_tokens(client):
    missing = client.get("/profile")
    invalid = client.get("/profile", headers={"Authorization": "Bearer invalid"})
    assert missing.status_code == 401
    assert invalid.status_code == 401


def test_resume_upload_rejects_missing_authentication_and_mismatched_user_id(client):
    missing_auth = client.post(
        "/resume/upload",
        files={"file": ("resume.pdf", b"%PDF-test", "application/pdf")},
    )
    invalid_auth = client.post(
        "/resume/upload",
        headers={"Authorization": "Bearer invalid"},
        files={"file": ("resume.pdf", b"%PDF-test", "application/pdf")},
    )
    assert missing_auth.status_code == 401
    assert invalid_auth.status_code == 401

    authenticate_as(client)
    response = client.post(
        "/resume/upload",
        data={"user_id": "8"},
        files={"file": ("resume.pdf", b"%PDF-test", "application/pdf")},
    )
    assert response.status_code == 403


def test_resume_upload_validates_file_type_signature_size_and_required_file(client):
    authenticate_as(client)
    unsupported = client.post(
        "/resume/upload",
        files={"file": ("resume.docx", b"document", "application/pdf")},
    )
    invalid_content_type = client.post(
        "/resume/upload",
        files={"file": ("resume.pdf", b"%PDF-test", "application/octet-stream")},
    )
    bad_signature = client.post(
        "/resume/upload",
        files={"file": ("resume.pdf", b"not a PDF", "application/pdf")},
    )
    too_large = client.post(
        "/resume/upload",
        files={"file": ("resume.pdf", b"%PDF-" + b"x" * (5 * 1024 * 1024), "application/pdf")},
    )
    missing = client.post("/resume/upload")
    assert unsupported.status_code == 400
    assert invalid_content_type.status_code == 400
    assert bad_signature.status_code == 400
    assert too_large.status_code == 413
    assert missing.status_code == 422


def test_upload_response_serialization_excludes_server_path(client, monkeypatch, tmp_path):
    user = authenticate_as(client)
    internal_path = str(tmp_path / "private-resume.pdf")
    monkeypatch.setattr(resume_api, "save_resume_file", lambda _contents: ("generated.pdf", internal_path))

    class UploadDatabase(EmptyDatabase):
        def add(self, item):
            item.id = 42
            item.uploaded_at = datetime.now(timezone.utc)

    app.dependency_overrides[get_db] = UploadDatabase
    response = client.post(
        "/resume/upload",
        files={"file": ("resume.pdf", b"%PDF-test", "application/pdf")},
    )
    assert response.status_code == 200
    assert response.json()["resume"]["user_id"] == user.id
    assert "file_path" not in response.json()["resume"]
    assert internal_path not in response.text


def test_upload_storage_errors_return_generic_response(client, monkeypatch):
    authenticate_as(client)

    def fail_storage(_contents):
        raise OSError("sensitive filesystem detail")

    monkeypatch.setattr(resume_api, "save_resume_file", fail_storage)
    response = client.post(
        "/resume/upload",
        files={"file": ("resume.pdf", b"%PDF-test", "application/pdf")},
    )
    assert response.status_code == 500
    assert "sensitive filesystem detail" not in response.text


@pytest.mark.parametrize("error_type", [ValueError, TypeError])
def test_resume_analysis_errors_return_generic_response(client, monkeypatch, tmp_path, error_type):
    authenticate_as(client)
    resume_path = tmp_path / "resume.pdf"
    resume_path.write_bytes(b"%PDF-test")
    resume = SimpleNamespace(
        id=42,
        user_id=7,
        file_path=str(resume_path),
        original_name="resume.pdf",
    )

    class AnalysisQuery(EmptyQuery):
        def first(self):
            return resume

    class AnalysisDatabase(EmptyDatabase):
        def query(self, *_args, **_kwargs):
            return AnalysisQuery()

    app.dependency_overrides[get_db] = AnalysisDatabase

    def fail_processing(_file_path):
        raise error_type("sensitive parser detail at /private/resume.pdf")

    monkeypatch.setattr(resume_api, "get_resume_file_path", lambda path: Path(path))
    monkeypatch.setattr(resume_api, "process_resume", fail_processing)
    response = client.get("/resume/42/analysis")

    assert response.status_code == 422
    assert response.json() == {"detail": "Could not analyze this resume"}
    assert "sensitive parser detail" not in response.text
    assert "/private/resume.pdf" not in response.text


@pytest.mark.parametrize(("method", "path", "expected_status"), [
    ("get", "/resumes", 200),
    ("get", "/resume/999/download", 404),
    ("get", "/resume/999/analysis", 404),
    ("delete", "/resumes/999", 404),
])
def test_private_resume_routes_filter_by_authenticated_owner(client, method, path, expected_status):
    user = authenticate_as(client)

    class OwnershipQuery(EmptyQuery):
        criteria = ()

        def filter(self, *criteria):
            self.criteria = criteria
            return self

    query = OwnershipQuery()

    class OwnershipDatabase(EmptyDatabase):
        def query(self, *_args, **_kwargs):
            return query

    app.dependency_overrides[get_db] = OwnershipDatabase
    response = getattr(client, method)(path)
    assert response.status_code == expected_status
    assert any(
        getattr(getattr(clause, "right", None), "value", None) == user.id
        for clause in query.criteria
    )

@pytest.mark.parametrize(("method", "path"), [
    ("get", "/resume/42/download"),
    ("get", "/resume/42/analysis"),
    ("get", "/skill-gaps/?resume_id=42&target_role=Engineer&required_skills=Python"),
])
def test_resume_processing_rejects_paths_outside_upload_directory(
    client, tmp_path, method, path
):
    authenticate_as(client)
    outside_path = str(tmp_path / "outside.pdf")
    resume = SimpleNamespace(
        id=42,
        user_id=7,
        file_path=outside_path,
        original_name="resume.pdf",
    )

    class TamperedPathQuery(EmptyQuery):
        def first(self):
            return resume

    class TamperedPathDatabase(EmptyDatabase):
        def query(self, *_args, **_kwargs):
            return TamperedPathQuery()

    app.dependency_overrides[get_db] = TamperedPathDatabase
    response = getattr(client, method)(path)

    assert response.status_code == 404
    assert response.json() == {"detail": "Resume file not found"}
    assert outside_path not in response.text
def test_database_diagnostic_route_is_not_exposed(client):
    response = client.get("/db-test")
    assert response.status_code == 404
    assert "database exception" not in response.text.lower()


@pytest.mark.parametrize("origin", ["http://localhost:3000", "http://127.0.0.1:3000", "http://127.0.0.1:3001"])
@pytest.mark.parametrize("method", ["GET", "POST", "PATCH", "DELETE", "OPTIONS"])
def test_cors_preflight_allows_configured_origins_methods_and_headers(client, origin, method):
    response = client.options(
        "/profile",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": "authorization,content-type,accept",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    allowed_methods = response.headers["access-control-allow-methods"]
    assert all(value in allowed_methods for value in ["GET", "POST", "PATCH", "DELETE", "OPTIONS"])
    allowed_headers = response.headers["access-control-allow-headers"].lower()
    assert all(value in allowed_headers for value in ["authorization", "content-type", "accept"])

def test_assistant_returns_documented_unavailable_response(client):
    authenticate_as(client)
    message = "Help me prepare for a Python interview."

    response = client.post("/assistant/messages", json={"message": message})

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "message": "Career assistant is not configured.",
            "reason": (
                "The repository contains a skill knowledge graph and embedding "
                "helper, but no retrieval corpus, RAG/chat pipeline, or "
                "configured local language model."
            ),
            "accepted_message_length": len(message),
        }
    }


def test_assistant_requires_authentication(client):
    response = client.post(
        "/assistant/messages",
        json={"message": "Help me prepare for an interview."},
    )

    assert response.status_code == 401


def test_job_matching_requires_authentication_and_hides_unowned_jobs(client):
    payload = {"resume_id": 42}
    unauthenticated = client.post("/jobs/9/matches", json=payload)
    assert unauthenticated.status_code == 401

    authenticate_as(client)
    # The database-independent fake returns no job for this user's ownership
    # scoped lookup, so the pipeline is never invoked.
    unowned = client.post("/jobs/9/matches", json=payload)
    assert unowned.status_code == 404
    assert unowned.json() == {"detail": "Job not found"}


def _job_matching_fixtures(run_status="completed"):
    now = datetime.now(timezone.utc)
    job = SimpleNamespace(
        id=9,
        user_id=7,
        title="Backend Engineer",
        description="Build and maintain backend services.",
        target_occupation="Software Developer",
        required_skills=[
            {"skill_name": "Python", "importance": "essential", "canonical_uri": None},
            {"skill_name": "PostgreSQL", "importance": "optional", "canonical_uri": "https://example.test/esco/postgresql"},
        ],
        created_at=now,
        updated_at=now,
    )
    resume = SimpleNamespace(
        id=42,
        user_id=7,
        original_name="candidate.pdf",
        stored_name="stored-candidate.pdf",
        file_path="/private/uploads/stored-candidate.pdf",
        uploaded_at=now,
    )
    run = SimpleNamespace(
        id=123,
        status=run_status,
        selection_mode="explicit",
        target_occupation_uri="https://example.test/esco/occupation/software-developer",
        target_occupation_title="Software Developer",
        overall_skill_coverage_score=0.75 if run_status == "completed" else None,
        essential_skill_coverage_score=1.0 if run_status == "completed" else None,
        optional_skill_coverage_score=0.0 if run_status == "completed" else None,
        readiness_class="developing" if run_status == "completed" else None,
        is_ood=False,
        canonical_output={
            "skills": {
                "extracted_skills": [
                    {"skill": "Python", "source_sections": ["experience"]},
                    {"skill": "PostgreSQL", "source_sections": ["projects"]},
                ],
                "esco_mappings": [
                    {"skill": "Python", "ESCO_Skill_Id": "https://example.test/esco/python"},
                    {"skill": "PostgreSQL", "ESCO_Skill_Id": "https://example.test/esco/postgresql"},
                ],
            }
        },
        error_code="PIPELINE_EXECUTION_ERROR" if run_status == "failed" else None,
        error_stage="pipeline_execution" if run_status == "failed" else None,
        error_message="Pipeline execution failed." if run_status == "failed" else None,
        created_at=now,
        completed_at=now if run_status == "completed" else None,
    )
    return job, resume, run


class MatchQuery(EmptyQuery):
    def __init__(self, result):
        self.result = result

    def first(self):
        return self.result


class JobResumeDatabase(EmptyDatabase):
    def __init__(self, job, resume):
        self.results = iter((job, resume))
        self.rollback_called = False

    def query(self, *_args, **_kwargs):
        return MatchQuery(next(self.results))

    def rollback(self):
        self.rollback_called = True


def test_job_matching_returns_pipeline_and_job_specific_result(client, monkeypatch):
    user = authenticate_as(client)
    job, resume, run = _job_matching_fixtures()
    database = JobResumeDatabase(job, resume)
    app.dependency_overrides[get_db] = lambda: database
    pipeline_calls = []
    matching_calls = []
    expected_matching = {
        "job_id": 9,
        "pipeline_run_id": 123,
        "status": "completed",
        "requirements": [
            {"skill_name": "Python", "importance": "essential", "matched": True},
        ],
        "scores": {"essential": 1.0, "optional": 0.0, "overall": 0.75},
    }

    def pipeline_stub(*, user, resume, target_occupation):
        pipeline_calls.append((user, resume, target_occupation))
        return run

    def matching_stub(candidate_skills, requirements, **kwargs):
        matching_calls.append((candidate_skills, requirements, kwargs))
        return expected_matching

    monkeypatch.setattr(jobs_api, "run_pipeline_for_resume", pipeline_stub)
    monkeypatch.setattr(jobs_api, "match_job_requirements", matching_stub)

    response = client.post("/jobs/9/matches", json={"resume_id": 42})

    assert response.status_code == 200
    body = response.json()
    assert body["job"]["id"] == 9
    assert body["run"]["id"] == 123
    assert body["matching_basis"] == (
        "Occupation-based analysis comes from the unified pipeline target ESCO occupation. "
        "Job-specific analysis separately compares pipeline-extracted candidate skills "
        "with this job's stored requirements."
    )
    assert body["job_specific_required_skills_applied"] is True
    assert body["job_specific_matching"] == expected_matching

    assert len(pipeline_calls) == 1
    pipeline_user, pipeline_resume, target_occupation = pipeline_calls[0]
    assert pipeline_user.id == user.id
    assert pipeline_resume.id == resume.id
    assert pipeline_resume.user_id == user.id
    assert target_occupation == job.target_occupation
    assert database.rollback_called

    assert len(matching_calls) == 1
    candidate_skills, requirements, matching_kwargs = matching_calls[0]
    assert candidate_skills == run.canonical_output["skills"]["extracted_skills"]
    assert requirements == job.required_skills
    assert matching_kwargs == {
        "job_id": 9,
        "pipeline_run_id": 123,
        "candidate_mappings": run.canonical_output["skills"]["esco_mappings"],
    }


def test_job_matching_failed_pipeline_returns_run_without_job_match(client, monkeypatch):
    authenticate_as(client)
    job, resume, run = _job_matching_fixtures(run_status="failed")
    app.dependency_overrides[get_db] = lambda: JobResumeDatabase(job, resume)
    pipeline_calls = []
    matching_calls = []

    monkeypatch.setattr(
        jobs_api,
        "run_pipeline_for_resume",
        lambda **kwargs: pipeline_calls.append(kwargs) or run,
    )
    monkeypatch.setattr(
        jobs_api,
        "match_job_requirements",
        lambda *args, **kwargs: matching_calls.append((args, kwargs)),
    )

    response = client.post("/jobs/9/matches", json={"resume_id": 42})

    assert response.status_code == 200
    body = response.json()
    assert body["run"]["id"] == 123
    assert body["run"]["status"] == "failed"
    assert body["job_specific_matching"] is None
    assert body["job_specific_required_skills_applied"] is False
    assert len(pipeline_calls) == 1
    assert matching_calls == []


def test_job_matching_rejects_resume_not_owned_by_authenticated_user(client, monkeypatch):
    authenticate_as(client)
    job, _resume, _run = _job_matching_fixtures()
    app.dependency_overrides[get_db] = lambda: JobResumeDatabase(job, None)
    pipeline_calls = []
    monkeypatch.setattr(
        jobs_api,
        "run_pipeline_for_resume",
        lambda **kwargs: pipeline_calls.append(kwargs),
    )

    response = client.post("/jobs/9/matches", json={"resume_id": 42})

    assert response.status_code == 404
    assert response.json() == {"detail": "Resume not found"}
    assert pipeline_calls == []

@pytest.mark.parametrize(
    ("payload", "expected_status", "expected_detail"),
    [
        ({}, 400, "No task progress fields provided"),
        ({"progress": None}, 422, "Task progress fields cannot be null"),
        ({"status": None}, 422, "Task progress fields cannot be null"),
    ],
)
def test_task_progress_rejects_empty_or_null_updates(
    client, payload, expected_status, expected_detail
):
    authenticate_as(client)

    response = client.patch("/tasks/42", json=payload)

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}
