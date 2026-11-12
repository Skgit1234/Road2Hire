import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from Api.profile import get_current_user
from Core.database import get_db
from Models.learning_task import LearningTask
from Models.pipeline_run import PipelineRun
from Models.user import User
from Schemas.task import LearningTaskResponse, TaskProgressUpdate


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tasks", tags=["Learning Tasks"])


@router.get("", response_model=list[LearningTaskResponse])
def list_learning_tasks(
    pipeline_run_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = (
        db.query(LearningTask)
        .join(PipelineRun, LearningTask.pipeline_run_id == PipelineRun.id)
        .filter(PipelineRun.user_id == user.id)
    )
    if pipeline_run_id is not None:
        query = query.filter(LearningTask.pipeline_run_id == pipeline_run_id)
    return query.order_by(
        LearningTask.roadmap_phase_number,
        LearningTask.id,
    ).all()


@router.get("/{task_id}", response_model=LearningTaskResponse)
def get_learning_task(
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    task = _owned_task(db, task_id, user.id)
    return task


@router.patch("/{task_id}", response_model=LearningTaskResponse)
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

    task = _owned_task(db, task_id, user.id)
    for field, value in updates.items():
        setattr(task, field, value)

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

    return task


def _owned_task(db: Session, task_id: int, user_id: int) -> LearningTask:
    task = (
        db.query(LearningTask)
        .join(PipelineRun, LearningTask.pipeline_run_id == PipelineRun.id)
        .filter(
            LearningTask.id == task_id,
            PipelineRun.user_id == user_id,
        )
        .first()
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
