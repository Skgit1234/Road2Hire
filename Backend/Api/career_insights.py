import csv
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from Api.profile import get_current_user
from Core.database import get_db
from Models.learning_task import LearningTask
from Models.skill_gap import SkillGap
from Models.user import User


logger = logging.getLogger(__name__)
router = APIRouter(tags=["Career Insights"])
LEARNING_RESOURCES_PATH = (
    Path(__file__).resolve().parents[2]
    / "Datasets"
    / "Learning_Resources"
    / "Processed"
    / "Learning_Resources.csv"
)
CAREER_READINESS_FORMULA = (
    "Use the most recent saved skill-gap match_score. The existing skill-gap "
    "pipeline calculates it as round(matched_required_skills / "
    "total_required_skills, 2) * 100."
)


def _load_learning_resources() -> tuple[dict[str, list[dict]], int]:
    if not LEARNING_RESOURCES_PATH.is_file():
        logger.error("Learning-resource dataset is missing: %s", LEARNING_RESOURCES_PATH)
        raise HTTPException(
            status_code=503,
            detail="Learning-resource dataset is unavailable",
        )

    resources: dict[str, list[dict]] = {}
    row_count = 0

    try:
        with LEARNING_RESOURCES_PATH.open(
            encoding="utf-8-sig",
            newline="",
        ) as resource_file:
            for row in csv.DictReader(resource_file):
                row_count += 1
                skill_name = (row.get("Skill_Name") or "").strip()
                course_title = (row.get("Course_Title") or "").strip()
                if not skill_name or not course_title:
                    continue

                resource = {
                    "resource_id": (row.get("Resource_Id") or "").strip(),
                    "skill_name": skill_name,
                    "category": (row.get("Category") or "").strip() or None,
                    "provider": (row.get("Provider") or "").strip() or None,
                    "course_title": course_title,
                    "difficulty": (row.get("Difficulty") or "").strip() or None,
                    "duration_hours": (
                        (row.get("Duration_Hours") or "").strip() or None
                    ),
                    "certificate": (row.get("Certificate") or "").strip() or None,
                    "course_url": (row.get("Course_URL") or "").strip() or None,
                }
                resources.setdefault(skill_name.casefold(), []).append(resource)
    except (OSError, UnicodeError, csv.Error) as exc:
        logger.exception("Could not read the learning-resource dataset")
        raise HTTPException(
            status_code=503,
            detail="Learning-resource dataset could not be read",
        ) from exc

    return resources, row_count


def _latest_skill_gap(db: Session, user_id: int) -> SkillGap | None:
    return (
        db.query(SkillGap)
        .filter(SkillGap.user_id == user_id)
        .order_by(SkillGap.created_at.desc(), SkillGap.id.desc())
        .first()
    )


@router.get(
    "/career-readiness",
    description=CAREER_READINESS_FORMULA,
)
def get_career_readiness(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    analysis = _latest_skill_gap(db, user.id)
    if analysis is None:
        return {
            "score": None,
            "formula": CAREER_READINESS_FORMULA,
            "analysis_id": None,
            "target_role": None,
            "message": "Run a skill-gap analysis to calculate a readiness score.",
        }

    return {
        "score": round(float(analysis.match_score), 2),
        "formula": CAREER_READINESS_FORMULA,
        "analysis_id": analysis.id,
        "target_role": analysis.target_role,
        "matched_skills": analysis.matched_skills,
        "required_skills": analysis.required_skills,
        "missing_skills": analysis.missing_skills,
        "created_at": analysis.created_at,
    }


@router.get("/learning-roadmap")
def get_learning_roadmap(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    analysis = _latest_skill_gap(db, user.id)
    if analysis is None:
        return {
            "analysis_id": None,
            "target_role": None,
            "tasks": [],
            "resource_availability": "awaiting_skill_gap_analysis",
        }

    if not isinstance(analysis.missing_skills, list) or any(
        not isinstance(skill, str) for skill in analysis.missing_skills
    ):
        logger.error("Skill-gap analysis %s has invalid missing-skills data", analysis.id)
        raise HTTPException(
            status_code=500,
            detail="Saved skill-gap data is invalid",
        )

    missing_skills = sorted(
        {skill.strip() for skill in analysis.missing_skills if skill.strip()},
        key=str.casefold,
    )

    try:
        tasks_by_skill = {
            task.skill_name.casefold(): task
            for task in db.query(LearningTask)
            .filter(
                LearningTask.user_id == user.id,
                LearningTask.skill_gap_id == analysis.id,
            )
            .all()
        }
        for skill_name in missing_skills:
            if skill_name.casefold() not in tasks_by_skill:
                task = LearningTask(
                    user_id=user.id,
                    skill_gap_id=analysis.id,
                    skill_name=skill_name,
                )
                db.add(task)
                tasks_by_skill[skill_name.casefold()] = task
        db.flush()
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.exception("Concurrent learning-roadmap task creation failed")
        raise HTTPException(
            status_code=409,
            detail="Learning roadmap changed concurrently; retry the request",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Could not persist learning-roadmap tasks")
        raise HTTPException(
            status_code=500,
            detail="Could not prepare the learning roadmap",
        ) from exc

    task_rows = (
        db.query(LearningTask)
        .filter(
            LearningTask.user_id == user.id,
            LearningTask.skill_gap_id == analysis.id,
        )
        .all()
    )
    resource_index, resource_row_count = _load_learning_resources()
    tasks = [
        {
            "id": task.id,
            "skill_name": task.skill_name,
            "status": task.status,
            "progress": task.progress,
            "resources": resource_index.get(task.skill_name.casefold(), []),
        }
        for task in task_rows
        if task.skill_name.casefold() in {skill.casefold() for skill in missing_skills}
    ]
    has_matching_resources = any(task["resources"] for task in tasks)

    if has_matching_resources:
        resource_availability = "available"
    elif resource_row_count:
        resource_availability = "no_matching_resources"
    else:
        resource_availability = "dataset_empty"

    return {
        "analysis_id": analysis.id,
        "target_role": analysis.target_role,
        "tasks": tasks,
        "resource_availability": resource_availability,
    }
