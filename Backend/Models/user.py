from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from Core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    candidate_profile = relationship(
        "CandidateProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    pipeline_runs = relationship(
        "PipelineRun",
        foreign_keys="[PipelineRun.user_id]",
        back_populates="user",
        cascade="all, delete-orphan",
    )