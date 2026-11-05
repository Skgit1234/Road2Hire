from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)

from Core.database import Base


class LearningTask(Base):
    __tablename__ = "learning_tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_gap_id = Column(
        Integer,
        ForeignKey("skill_gaps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_name = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, server_default="not_started")
    progress = Column(Integer, nullable=False, server_default="0")
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
        UniqueConstraint(
            "skill_gap_id",
            "skill_name",
            name="uq_learning_task_skill",
        ),
    )
