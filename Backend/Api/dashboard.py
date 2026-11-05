from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from Api.profile import get_current_user
from Core.database import get_db
from Models.resume import Resume
from Models.learning_task import LearningTask
from Models.skill_gap import SkillGap
from Models.user import User


router = APIRouter(tags=["Dashboard"])


@router.get("/dashboard")
def get_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    resume_count = db.query(func.count(Resume.id)).filter(
        Resume.user_id == user.id
    ).scalar()
    skill_gap_count = db.query(func.count(SkillGap.id)).filter(
        SkillGap.user_id == user.id
    ).scalar()
    average_match_score = db.query(func.avg(SkillGap.match_score)).filter(
        SkillGap.user_id == user.id
    ).scalar()
    latest_resume = (
        db.query(Resume)
        .filter(Resume.user_id == user.id)
        .order_by(Resume.uploaded_at.desc(), Resume.id.desc())
        .first()
    )
    latest_skill_gap = (
        db.query(SkillGap)
        .filter(SkillGap.user_id == user.id)
        .order_by(SkillGap.created_at.desc(), SkillGap.id.desc())
        .first()
    )

    return {
        "resume_count": resume_count or 0,
        "skill_gap_count": skill_gap_count or 0,
        "average_match_score": (
            round(float(average_match_score), 2)
            if average_match_score is not None
            else None
        ),
        "latest_resume": (
            {
                "id": latest_resume.id,
                "original_name": latest_resume.original_name,
                "uploaded_at": latest_resume.uploaded_at,
            }
            if latest_resume
            else None
        ),
        "latest_skill_gap": (
            {
                "id": latest_skill_gap.id,
                "resume_id": latest_skill_gap.resume_id,
                "target_role": latest_skill_gap.target_role,
                "match_score": latest_skill_gap.match_score,
                "created_at": latest_skill_gap.created_at,
            }
            if latest_skill_gap
            else None
        ),
    }


@router.get("/activity")
def get_recent_activity(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    resumes = (
        db.query(Resume)
        .filter(Resume.user_id == user.id)
        .order_by(Resume.uploaded_at.desc(), Resume.id.desc())
        .limit(limit)
        .all()
    )
    skill_gaps = (
        db.query(SkillGap)
        .filter(SkillGap.user_id == user.id)
        .order_by(SkillGap.created_at.desc(), SkillGap.id.desc())
        .limit(limit)
        .all()
    )

    items = [
        {
            "type": "resume_uploaded",
            "id": resume.id,
            "timestamp": resume.uploaded_at,
            "resume_name": resume.original_name,
        }
        for resume in resumes
    ]
    items.extend(
        {
            "type": "skill_gap_analyzed",
            "id": analysis.id,
            "timestamp": analysis.created_at,
            "resume_id": analysis.resume_id,
            "target_role": analysis.target_role,
            "match_score": analysis.match_score,
        }
        for analysis in skill_gaps
    )
    progressed_tasks = (
        db.query(LearningTask)
        .filter(
            LearningTask.user_id == user.id,
            or_(
                LearningTask.progress > 0,
                LearningTask.status != "not_started",
            ),
        )
        .order_by(LearningTask.updated_at.desc(), LearningTask.id.desc())
        .limit(limit)
        .all()
    )
    items.extend(
        {
            "type": "task_progress_updated",
            "id": task.id,
            "timestamp": task.updated_at,
            "skill_gap_id": task.skill_gap_id,
            "skill_name": task.skill_name,
            "status": task.status,
            "progress": task.progress,
        }
        for task in progressed_tasks
    )
    items.sort(key=lambda item: (item["timestamp"], item["id"]), reverse=True)

    return {"items": items[:limit], "limit": limit}
