import pytest
from fastapi import HTTPException
from datetime import datetime, timezone

from sqlalchemy.orm import configure_mappers

from Api import career_insights, dashboard, jobs, skill_gaps, tasks
from Models import Job, LearningTask, PipelineRun, Resume, SkillGap, User
from Schemas.job import JobCreate, JobMatchRequest
from Schemas.skill_gap import SkillGapAnalysisRequest
from Schemas.task import TaskProgressUpdate
from Services.roadmap_utils import logical_item_key


def _canonical_output():
    item = {
        "skill_name": "Python",
        "esco_uri": "https://example.test/skill/python",
        "current_status": "missing_essential",
        "priority": "Critical",
        "importance_rationale": "Required for the target role.",
        "learning_outcome": "Write production Python.",
        "suggested_activities": ["Complete a practice exercise."],
        "practical_project": "Build a small API.",
        "estimated_duration_weeks": "2",
        "prerequisites": [],
        "completion_criteria": "Pass the project checks.",
        "resource_categories": [{"category": "documentation"}],
    }
    return {
        "warnings": ["Experimental prediction."],
        "skills": {"extracted_skills": [{"skill_name": "SQL"}]},
        "occupation_recommendations": [{"preferred_label": "Data Engineer"}],
        "target_occupation": {"preferred_label": "Data Engineer"},
        "skill_gap": {"matched_skills": [], "missing_essential_skills": ["Python"]},
        "readiness": {
            "predicted_class": "Developing",
            "class_probabilities": {"Developing": 0.8, "Job Ready": 0.2},
            "model_version": "test-version",
            "model_type": "LogisticRegression",
            "is_experimental": True,
            "is_ood": False,
            "ood_warnings": [],
            "training_sample_count": 71,
            "training_class_distribution": {"Developing": 50, "Job Ready": 21},
            "feature_values": {"skill_overlap_ratio": 0.5},
            "feature_diagnostics": {"valid": True},
            "limitations": ["Experimental model."],
        },
        "explanations": {
            "target_class_explained": "Developing",
            "base_value": 0.4,
            "top_positive_factors": [{"feature_name": "SQL"}],
            "top_negative_factors": [],
            "feature_contributions": [{"feature_name": "SQL", "contribution": 0.2}],
            "human_readable_summary": "SQL improved the prediction.",
            "waterfall_steps": [],
            "global_importance_ranking": [{"feature_name": "SQL", "importance": 0.2}],
            "limitations": ["Not employment probability."],
        },
        "learning_roadmap": {
            "target_occupation_title": "Data Engineer",
            "target_occupation_uri": "https://example.test/occupation/data-engineer",
            "total_roadmap_skills": 1,
            "total_estimated_weeks": "2 weeks",
            "phases": [
                {
                    "phase_number": 1,
                    "phase_name": "Foundations",
                    "description": "Build foundational skills.",
                    "estimated_weeks": "2 weeks",
                    "items": [item],
                }
            ],
            "disclaimers": ["Personalized learning suggestions."],
        },
    }


def _run(
    run_id=7,
    user_id=1,
    resume_id=11,
    status="completed",
    canonical_output=None,
):
    now = datetime.now(timezone.utc)
    return PipelineRun(
        id=run_id,
        user_id=user_id,
        resume_id=resume_id,
        status=status,
        selection_mode="explicit",
        overall_skill_coverage_score=0.75,
        essential_skill_coverage_score=0.8,
        optional_skill_coverage_score=0.6,
        readiness_class="Developing",
        is_ood=False,
        canonical_output=canonical_output or _canonical_output(),
        created_at=now,
        completed_at=now if status == "completed" else None,
    )


def test_model_registration_and_router_paths():
    from Main import app

    configure_mappers()
    assert {
        "users",
        "resumes",
        "candidate_profiles",
        "pipeline_runs",
        "skill_gaps",
        "learning_tasks",
        "jobs",
    }.issubset(PipelineRun.metadata.tables)
    assert "user_id" not in SkillGap.__table__.c
    assert "resume_id" not in SkillGap.__table__.c
    assert "user_id" not in LearningTask.__table__.c
    assert "skill_gap_id" not in LearningTask.__table__.c

    paths = app.openapi()["paths"]
    assert {
        "/jobs",
        "/profile/candidate",
        "/skill-gaps/analyze",
        "/skill-gaps/history",
        "/career-readiness",
        "/career-readiness/explanations",
        "/recommendations",
        "/learning-roadmap",
        "/tasks/{task_id}",
        "/dashboard",
        "/activity",
    }.issubset(paths)
    assert paths["/jobs"]["post"]["security"]
    assert paths["/learning-roadmap"]["get"]["security"]
    assert paths["/profile/candidate"]["get"]["security"]


def test_job_creation_and_retrieval(fake_session, test_user):
    db = fake_session()
    payload = JobCreate(
        title="Data Engineer",
        description="Build data systems.",
        target_occupation="data engineer",
        required_skills=[{"skill_name": "Python", "importance": "essential"}],
    )

    created = jobs.create_job(payload, db, test_user)
    listed = jobs.list_jobs(db, test_user)
    retrieved = jobs.get_job(created.id, db, test_user)

    assert created.title == "Data Engineer"
    assert created.required_skills[0]["skill_name"] == "Python"
    assert listed == [created]
    assert retrieved.id == created.id
    with pytest.raises(HTTPException) as missing:
        jobs.get_job(created.id + 100, db, test_user)
    assert missing.value.status_code == 404


def test_job_matching_uses_saved_job_and_resume_ownership(
    fake_session,
    test_user,
    monkeypatch,
):
    run = _run()
    job = Job(
        id=3,
        user_id=test_user.id,
        title="Data Engineer",
        description="Build data systems.",
        target_occupation="Data Engineer",
        required_skills=[{"skill_name": "Python"}],
        created_at=run.created_at,
        updated_at=run.created_at,
    )
    resume = Resume(id=11, user_id=test_user.id, file_path="resume.pdf")
    db = fake_session({Job: [job], Resume: [resume]})
    monkeypatch.setattr(
        jobs,
        "run_pipeline_for_resume",
        lambda **_kwargs: run,
    )

    response = jobs.match_resume_to_job(
        job.id,
        JobMatchRequest(resume_id=resume.id),
        db,
        test_user,
    )

    assert response.job.id == job.id
    assert response.run.id == run.id
    assert response.job_specific_required_skills_applied is True
    assert response.job_specific_matching["status"] == "completed"


def test_skill_gap_analysis_and_history(
    fake_session,
    test_user,
    monkeypatch,
):
    resume = Resume(id=11, user_id=test_user.id, file_path="resume.pdf")
    run = _run()
    db = fake_session({Resume: [resume], PipelineRun: [run]})
    monkeypatch.setattr(
        skill_gaps,
        "run_pipeline_for_resume",
        lambda **_kwargs: run,
    )

    analysis = skill_gaps.analyze_skill_gap(
        SkillGapAnalysisRequest(
            resume_id=resume.id,
            target_occupation="Data Engineer",
        ),
        db,
        test_user,
    )
    history = skill_gaps.get_skill_gap_history(
        limit=20,
        offset=0,
        db=db,
        user=test_user,
    )
    graph = skill_gaps.get_run_knowledge_graph(run.id, db, test_user)

    assert analysis.pipeline_run_id == run.id
    assert analysis.skill_gap == run.canonical_output["skill_gap"]
    assert history.total == 1
    assert history.items[0].id == run.id
    assert graph.pipeline_run_id == run.id


def test_career_readiness_latest_and_run_specific(fake_session, test_user):
    run = _run()
    db = fake_session({PipelineRun: [run]})

    latest = career_insights.get_career_readiness(db, test_user)
    specific = career_insights.get_career_readiness_for_run(run.id, db, test_user)

    assert latest.predicted_class == "Developing"
    assert latest.training_sample_count == 71
    assert latest.is_experimental is True
    assert specific.pipeline_run_id == run.id


def test_shap_explanations_latest_and_run_specific(fake_session, test_user):
    run = _run()
    db = fake_session({PipelineRun: [run]})

    latest = career_insights.get_latest_feature_explanations(db, test_user)
    specific = career_insights.get_feature_explanations_for_run(
        run.id,
        db,
        test_user,
    )

    assert latest.target_class_explained == "Developing"
    assert latest.feature_contributions[0]["feature_name"] == "SQL"
    assert latest.global_importance_ranking[0]["importance"] == 0.2
    assert specific.pipeline_run_id == run.id


def test_recommendations_roadmap_phases_items_and_resources(
    fake_session,
    test_user,
):
    run = _run()
    item = _canonical_output()["learning_roadmap"]["phases"][0]["items"][0]
    task = LearningTask(
        id=21,
        pipeline_run_id=run.id,
        logical_item_key=logical_item_key(
            1, item["skill_name"], item["esco_uri"]
        ),
        roadmap_phase_number=1,
        roadmap_phase_name="Foundations",
        skill_name="Python",
        skill_uri=item["esco_uri"],
        priority="Critical",
        status="not_started",
        progress=0,
        roadmap_item_data=item,
        updated_at=run.created_at,
    )
    db = fake_session({PipelineRun: [run], LearningTask: [task]})

    recommendations = career_insights.get_latest_recommendations(db, test_user)
    roadmap = career_insights.get_latest_learning_roadmap(db, test_user)
    specific_recommendations = career_insights.get_recommendations_for_run(
        run.id,
        db,
        test_user,
    )
    specific_roadmap = career_insights.get_learning_roadmap_for_run(
        run.id,
        db,
        test_user,
    )
    key = roadmap.phases[0].items[0].logical_item_key
    phase = career_insights.get_roadmap_phase(run.id, 1, db, test_user)
    item = career_insights.get_roadmap_item(run.id, key, db, test_user)
    all_resources = career_insights.get_roadmap_resources(run.id, db, test_user)
    resources = career_insights.get_roadmap_item_resources(
        run.id,
        key,
        db,
        test_user,
    )

    assert recommendations.recommendations[0]["preferred_label"] == "Data Engineer"
    assert specific_recommendations.pipeline_run_id == run.id
    assert roadmap.phases[0].items[0].progress == 0
    assert specific_roadmap.pipeline_run_id == run.id
    assert phase.items[0].task_id == roadmap.phases[0].items[0].task_id
    assert item.roadmap_item_data["practical_project"] == "Build a small API."
    assert all_resources[0].resource_categories == [{"category": "documentation"}]
    assert resources.resource_categories == [{"category": "documentation"}]
    assert len(db.rows[LearningTask]) == 1


def test_learning_task_progress_updates_are_owned_and_persisted(
    fake_session,
    test_user,
):
    run = _run()
    task = LearningTask(
        id=20,
        pipeline_run_id=run.id,
        logical_item_key="phase:1:skill:test",
        roadmap_phase_number=1,
        roadmap_phase_name="Foundations",
        skill_name="Python",
        priority="Critical",
        status="not_started",
        progress=0,
        roadmap_item_data={"skill_name": "Python"},
        updated_at=datetime.now(timezone.utc),
    )
    db = fake_session({PipelineRun: [run], LearningTask: [task]})

    updated = tasks.update_task_progress(
        task.id,
        TaskProgressUpdate(progress=45, status="in_progress"),
        db,
        test_user,
    )

    assert updated.progress == 45
    assert updated.status == "in_progress"
    assert db.rollback_count == 0


def test_job_run_and_task_access_is_scoped_to_owner(fake_session, test_user):
    foreign_run = _run(run_id=90, user_id=2)
    foreign_job = Job(
        id=91,
        user_id=2,
        title="Private job",
        description="Private description.",
        target_occupation="private role",
        required_skills=[],
    )
    foreign_task = LearningTask(
        id=92,
        pipeline_run_id=foreign_run.id,
        logical_item_key="phase:1:skill:private",
        roadmap_phase_number=1,
        skill_name="Private skill",
        status="not_started",
        progress=0,
        roadmap_item_data={},
    )
    db = fake_session(
        {
            PipelineRun: [foreign_run],
            Job: [foreign_job],
            LearningTask: [foreign_task],
        }
    )

    with pytest.raises(HTTPException) as job_error:
        jobs.get_job(foreign_job.id, db, test_user)
    with pytest.raises(HTTPException) as run_error:
        career_insights.get_career_readiness_for_run(
            foreign_run.id,
            db,
            test_user,
        )
    with pytest.raises(HTTPException) as task_error:
        tasks.get_learning_task(foreign_task.id, db, test_user)

    assert job_error.value.status_code == 404
    assert run_error.value.status_code == 404
    assert task_error.value.status_code == 404


def test_dashboard_and_activity_use_run_owned_tasks(fake_session, test_user):
    run = _run()
    resume = Resume(
        id=run.resume_id,
        user_id=test_user.id,
        original_name="resume.pdf",
        uploaded_at=run.created_at,
    )
    task = LearningTask(
        id=20,
        pipeline_run_id=run.id,
        logical_item_key="phase:1:skill:test",
        roadmap_phase_number=1,
        skill_name="Python",
        status="in_progress",
        progress=40,
        roadmap_item_data={"skill_name": "Python"},
        updated_at=run.created_at,
    )
    db = fake_session(
        {
            PipelineRun: [run],
            Resume: [resume],
            LearningTask: [task],
        }
    )

    summary = dashboard.get_dashboard(db, test_user)
    activity = dashboard.get_recent_activity(limit=20, db=db, user=test_user)

    assert summary["skill_gap_count"] == 1
    assert summary["latest_skill_gap"]["id"] == run.id
    assert summary["average_match_score"] == 75
    task_events = [event for event in activity["items"] if event["type"] == "task_progress_updated"]
    assert task_events[0]["pipeline_run_id"] == run.id
