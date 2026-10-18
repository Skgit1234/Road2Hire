
from datetime import datetime, timezone

from sqlalchemy import (
    Column, DateTime, ForeignKey, Integer,
    Float, String, JSON, UniqueConstraint
)

from Core.database import Base


class SkillGap(Base):
    __tablename__ = "skill_gaps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    resume_id = Column(
        Integer, ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    target_role = Column(String(150), nullable=False)
    requirements_hash = Column(String(64), nullable=False)
    required_skills = Column(JSON, nullable=False)
    matched_skills = Column(JSON, nullable=False)
    missing_skills = Column(JSON, nullable=False)
    match_score = Column(Float, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "resume_id",
            "target_role",
            "requirements_hash",
            name="uq_skill_gap_analysis"
        ),
    )
