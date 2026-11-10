from sqlalchemy import Column, DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from Core.database import Base


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    resume_id = Column(
        Integer,
        ForeignKey("resumes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    skills = Column(JSONB, nullable=False, default=list)
    education = Column(JSONB, nullable=False, default=list)
    experience = Column(JSONB, nullable=False, default=list)
    projects = Column(JSONB, nullable=False, default=list)
    certifications = Column(JSONB, nullable=False, default=list)

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user = relationship("User", back_populates="candidate_profile")
    resume = relationship("Resume", back_populates="candidate_profile")
