from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from Core.database import Base


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    resume_id = Column(
        Integer,
        nullable=False,
    )

    target_occupation_uri = Column(String(512), nullable=True)
    target_occupation_title = Column(String(255), nullable=True)
    selection_mode = Column(String(20), nullable=False, server_default="explicit")
    status = Column(String(20), nullable=False, server_default="pending")
    pipeline_version = Column(String(30), nullable=False, server_default="3.0.0")
    schema_version = Column(String(20), nullable=False, server_default="1.0.0")
    overall_skill_coverage_score = Column(Float, nullable=True)
    essential_skill_coverage_score = Column(Float, nullable=True)
    optional_skill_coverage_score = Column(Float, nullable=True)
    readiness_class = Column(String(50), nullable=True)
    is_ood = Column(Boolean, nullable=False, server_default="false")
    canonical_output = Column(JSONB, nullable=False, server_default="{}")
    error_code = Column(String(100), nullable=True)
    error_stage = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
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
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "resume_id"],
            ["resumes.user_id", "resumes.id"],
            name="fk_pipeline_runs_resume_owner",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="ck_pipeline_runs_status",
        ),
        CheckConstraint(
            "selection_mode IN ('explicit', 'auto_selected')",
            name="ck_pipeline_runs_selection_mode",
        ),
        CheckConstraint(
            "overall_skill_coverage_score IS NULL OR (overall_skill_coverage_score >= 0.0 AND overall_skill_coverage_score <= 1.0)",
            name="ck_pipeline_runs_overall_score_range",
        ),
        CheckConstraint(
            "essential_skill_coverage_score IS NULL OR (essential_skill_coverage_score >= 0.0 AND essential_skill_coverage_score <= 1.0)",
            name="ck_pipeline_runs_essential_score_range",
        ),
        CheckConstraint(
            "optional_skill_coverage_score IS NULL OR (optional_skill_coverage_score >= 0.0 AND optional_skill_coverage_score <= 1.0)",
            name="ck_pipeline_runs_optional_score_range",
        ),
        Index("ix_pipeline_runs_user_created", "user_id", "created_at"),
        Index("ix_pipeline_runs_resume", "resume_id"),
        Index("ix_pipeline_runs_status", "status"),
        Index("ix_pipeline_runs_target_occupation_uri", "target_occupation_uri"),
        Index("ix_pipeline_runs_completed_at", "completed_at"),
    )

    user = relationship("User", foreign_keys=[user_id], back_populates="pipeline_runs")
    resume = relationship("Resume", foreign_keys=[resume_id], back_populates="pipeline_runs")
    skill_gap = relationship(
        "SkillGap",
        back_populates="pipeline_run",
        uselist=False,
        cascade="all, delete-orphan",
    )
    learning_tasks = relationship(
        "LearningTask",
        back_populates="pipeline_run",
        cascade="all, delete-orphan",
    )
