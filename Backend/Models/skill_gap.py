from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from Core.database import Base


class SkillGap(Base):
    __tablename__ = "skill_gaps"

    id = Column(Integer, primary_key=True)
    pipeline_run_id = Column(
        Integer,
        ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_occupation_uri = Column(String(512), nullable=False, index=True)
    target_occupation_title = Column(String(255), nullable=False)
    overall_skill_coverage_score = Column(Float, nullable=False)
    essential_skill_coverage_score = Column(Float, nullable=False)
    optional_skill_coverage_score = Column(Float, nullable=False)
    matched_skill_count = Column(Integer, nullable=False, server_default="0")
    missing_essential_skill_count = Column(Integer, nullable=False, server_default="0")
    missing_optional_skill_count = Column(Integer, nullable=False, server_default="0")
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "overall_skill_coverage_score >= 0.0 AND overall_skill_coverage_score <= 1.0",
            name="ck_skill_gaps_overall_score_range",
        ),
        CheckConstraint(
            "essential_skill_coverage_score >= 0.0 AND essential_skill_coverage_score <= 1.0",
            name="ck_skill_gaps_essential_score_range",
        ),
        CheckConstraint(
            "optional_skill_coverage_score >= 0.0 AND optional_skill_coverage_score <= 1.0",
            name="ck_skill_gaps_optional_score_range",
        ),
        CheckConstraint(
            "matched_skill_count >= 0",
            name="ck_skill_gaps_matched_skill_count_non_negative",
        ),
        CheckConstraint(
            "missing_essential_skill_count >= 0",
            name="ck_skill_gaps_missing_essential_count_non_negative",
        ),
        CheckConstraint(
            "missing_optional_skill_count >= 0",
            name="ck_skill_gaps_missing_optional_count_non_negative",
        ),
        UniqueConstraint("pipeline_run_id", name="uq_skill_gaps_pipeline_run_id"),
    )

    pipeline_run = relationship("PipelineRun", back_populates="skill_gap")
