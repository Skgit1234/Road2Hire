from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from Core.database import Base


class LearningTask(Base):
    __tablename__ = "learning_tasks"

    id = Column(Integer, primary_key=True)
    pipeline_run_id = Column(
        Integer,
        ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    logical_item_key = Column(String(255), nullable=False)
    roadmap_phase_number = Column(Integer, nullable=False)
    roadmap_phase_name = Column(String(120), nullable=True)
    skill_name = Column(String(255), nullable=False)
    skill_uri = Column(String(512), nullable=True)
    priority = Column(String(20), nullable=True)
    status = Column(String(20), nullable=False, server_default="not_started")
    progress = Column(Integer, nullable=False, server_default="0")
    roadmap_item_data = Column(JSONB, nullable=False, server_default="{}")
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('not_started', 'in_progress', 'completed')",
            name="ck_learning_tasks_status",
        ),
        CheckConstraint(
            "progress >= 0 AND progress <= 100",
            name="ck_learning_tasks_progress",
        ),
        CheckConstraint(
            "roadmap_phase_number >= 1 AND roadmap_phase_number <= 4",
            name="ck_learning_tasks_roadmap_phase_number",
        ),
        UniqueConstraint(
            "pipeline_run_id",
            "logical_item_key",
            name="uq_learning_task_pipeline_run_logical_item",
        ),
        Index("ix_learning_tasks_status", "status"),
        Index("ix_learning_tasks_skill_name", "skill_name"),
    )

    pipeline_run = relationship("PipelineRun", back_populates="learning_tasks")
