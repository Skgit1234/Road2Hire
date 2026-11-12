from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship

from Core.database import Base


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    original_name = Column(String(255), nullable=False)
    stored_name = Column(String(40), nullable=False, unique=True)
    file_path = Column(String(1024), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "id", name="uq_resumes_user_id_id"),
    )

    user = relationship("User", back_populates="resumes")
    candidate_profile = relationship(
        "CandidateProfile",
        back_populates="resume",
        uselist=False,
    )
    pipeline_runs = relationship(
        "PipelineRun",
        foreign_keys="[PipelineRun.resume_id]",
        back_populates="resume",
    )
