import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from Api import career_insights, jobs, skill_gaps, tasks
from Models import Job, LearningTask, PipelineRun, Resume
from Schemas.assistant import AssistantMessageRequest
from Schemas.job import JobCreate, JobMatchRequest
from Schemas.skill_gap import SkillGapAnalysisRequest
from Schemas.task import TaskProgressUpdate

from test_backend_api_integration import _run


def test_job_missing_id_and_database_failure_are_reported(
    fake_session,
    test_user,
):
    db = fake_session()
    with pytest.raises(HTTPException) as missing:
        jobs.get_job(404, db, test_user)
    assert missing.value.status_code == 404

    def fail_commit():
        raise SQLAlchemyError("database detail")

    db.commit = fail_commit
    with pytest.raises(HTTPException) as failure:
        jobs.create_job(
            JobCreate(
                title="Data Engineer",
                description="Build data systems.",
                target_occupation="Data Engineer",
            ),
            db,
            test_user,
        )
    assert failure.value.status_code == 500
    assert failure.value.detail == "Could not save job"
    assert db.rollback_count == 1


def test_skill_gap_analysis_rejects_unowned_resume_and_pipeline_errors(
    fake_session,
    test_user,
    monkeypatch,
):
    foreign_resume = Resume(
        id=11,
        user_id=2,
        file_path="not-used.pdf",
    )
    db = fake_session({Resume: [foreign_resume]})
    request = SkillGapAnalysisRequest(
        resume_id=foreign_resume.id,
        target_occupation="Data Engineer",
    )

    with pytest.raises(HTTPException) as missing:
        skill_gaps.analyze_skill_gap(request, db, test_user)
    assert missing.value.status_code == 404

    owned_resume = Resume(id=12, user_id=test_user.id, file_path="not-used.pdf")
    db = fake_session({Resume: [owned_resume]})
    monkeypatch.setattr(
        skill_gaps,
        "run_pipeline_for_resume",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("internal detail")),
    )
    with pytest.raises(HTTPException) as failed:
        skill_gaps.analyze_skill_gap(
            SkillGapAnalysisRequest(
                resume_id=owned_resume.id,
                target_occupation="Data Engineer",
            ),
            db,
            test_user,
        )
    assert failed.value.status_code == 500
    assert failed.value.detail == "Could not run skill-gap analysis"


def test_readiness_and_explanations_report_missing_saved_data(
    fake_session,
    test_user,
):
    run_without_results = _run(canonical_output={"warnings": []})
    db = fake_session({PipelineRun: [run_without_results]})

    with pytest.raises(HTTPException) as readiness:
        career_insights.get_career_readiness_for_run(
            run_without_results.id,
            db,
            test_user,
        )
    assert readiness.value.status_code == 404

    with pytest.raises(HTTPException) as explanations:
        career_insights.get_feature_explanations_for_run(
            run_without_results.id,
            db,
            test_user,
        )
    assert explanations.value.status_code == 404

    running = _run(
        run_id=8,
        status="running",
        canonical_output={"readiness": {}, "explanations": {}},
    )
    db = fake_session({PipelineRun: [running]})
    with pytest.raises(HTTPException) as incomplete:
        career_insights.get_career_readiness_for_run(running.id, db, test_user)
    assert incomplete.value.status_code == 409


def test_recommendations_and_roadmap_report_missing_saved_data(
    fake_session,
    test_user,
):
    run = _run(canonical_output={"readiness": {}})
    db = fake_session({PipelineRun: [run]})

    with pytest.raises(HTTPException) as recommendations:
        career_insights.get_recommendations_for_run(run.id, db, test_user)
    assert recommendations.value.status_code == 404

    with pytest.raises(HTTPException) as roadmap:
        career_insights.get_learning_roadmap_for_run(run.id, db, test_user)
    assert roadmap.value.status_code == 404

    with pytest.raises(HTTPException) as phase:
        career_insights.get_roadmap_phase(run.id, 5, db, test_user)
    assert phase.value.status_code == 422


def test_learning_task_progress_rejects_invalid_or_empty_updates(
    fake_session,
    test_user,
):
    db = fake_session()

    with pytest.raises(HTTPException) as empty:
        tasks.update_task_progress(1, TaskProgressUpdate(), db, test_user)
    assert empty.value.status_code == 400

    with pytest.raises(HTTPException) as null_value:
        tasks.update_task_progress(
            1,
            TaskProgressUpdate(progress=None),
            db,
            test_user,
        )
    assert null_value.value.status_code == 422

    with pytest.raises(ValidationError):
        TaskProgressUpdate(progress=101)


def test_career_assistant_authentication_and_request_validation(
    api_client,
    sqlite_session,
    auth_headers,
):
    from Models import User

    user = User(
        name="Assistant User",
        email="assistant@example.test",
        password_hash="unused",
    )
    sqlite_session.add(user)
    sqlite_session.commit()
    headers = auth_headers(user.email)

    invalid_request = api_client.post(
        "/assistant/messages",
        headers=headers,
        json={"message": ""},
    )
    assert invalid_request.status_code == 422

    invalid_token = api_client.post(
        "/assistant/messages",
        headers={"Authorization": "Bearer invalid"},
        json={"message": "Help me plan my career"},
    )
    assert invalid_token.status_code == 401

    accepted_request = api_client.post(
        "/assistant/messages",
        headers=headers,
        json={"message": "Help me plan my career"},
    )
    assert accepted_request.status_code == 503
    assert accepted_request.json()["detail"]["message"] == (
        "Career assistant is not configured."
    )

    with pytest.raises(ValidationError):
        AssistantMessageRequest(message="x" * 4001)


def test_job_match_endpoint_does_not_run_for_another_users_job(
    fake_session,
    test_user,
):
    foreign_job = Job(
        id=1,
        user_id=2,
        title="Private role",
        description="Private details",
        target_occupation="Private role",
        required_skills=[],
    )
    db = fake_session({Job: [foreign_job]})

    with pytest.raises(HTTPException) as missing:
        jobs.match_resume_to_job(
            foreign_job.id,
            JobMatchRequest(resume_id=1),
            db,
            test_user,
        )
    assert missing.value.status_code == 404


def test_task_ownership_misses_foreign_run(
    fake_session,
    test_user,
):
    foreign_run = _run(run_id=40, user_id=2)
    task = LearningTask(
        id=41,
        pipeline_run_id=foreign_run.id,
        logical_item_key="item",
        roadmap_phase_number=1,
        skill_name="Private",
        status="not_started",
        progress=0,
        roadmap_item_data={},
    )
    db = fake_session({PipelineRun: [foreign_run], LearningTask: [task]})

    with pytest.raises(HTTPException) as missing:
        tasks.get_learning_task(task.id, db, test_user)
    assert missing.value.status_code == 404
