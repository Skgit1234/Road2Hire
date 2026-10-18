import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from Api.profile import get_current_user
from Core.database import get_db
from Models.learning_task import LearningTask
from Models.user import User
from Schemas.task import TaskProgressUpdate


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tasks", tags=["Learning Tasks"])


@router.patch("/{task_id}")
def update_task_progress(
    task_id: int,
    details: TaskProgressUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    updates = details.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No task progress fields provided")
    if any(value is None for value in updates.values()):
        raise HTTPException(status_code=422, detail="Task progress fields cannot be null")

    task = db.query(LearningTask).filter(
        LearningTask.id == task_id,
        LearningTask.user_id == user.id,
    ).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    progress = updates.get("progress", task.progress)
    status = updates.get("status")

    if status is None:
        if "progress" not in updates:
            raise HTTPException(status_code=400, detail="No task progress fields provided")
        status = (
            "not_started"
            if progress == 0
            else "completed"
            if progress == 100
            else "in_progress"
        )
    elif status == "completed":
        if "progress" in updates and progress != 100:
            raise HTTPException(
                status_code=422,
                detail="Completed tasks must have 100 percent progress",
            )
        progress = 100
    elif status == "not_started":
        if "progress" in updates and progress != 0:
            raise HTTPException(
                status_code=422,
                detail="Not-started tasks must have 0 percent progress",
            )
        progress = 0
    elif progress == 100:
        raise HTTPException(
            status_code=422,
            detail="Tasks at 100 percent progress must be completed",
        )

    task.progress = progress
    task.status = status

    try:
        db.commit()
        db.refresh(task)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Could not update learning task %s", task_id)
        raise HTTPException(
            status_code=500,
            detail="Could not update task progress",
        ) from exc

    return {
        "id": task.id,
        "skill_gap_id": task.skill_gap_id,
        "skill_name": task.skill_name,
        "status": task.status,
        "progress": task.progress,
        "updated_at": task.updated_at,
    }
