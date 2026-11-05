from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from Core.database import Base

from fastapi import Depends
from sqlalchemy.orm import Session

from Core.database import get_db
from Api.profile import get_current_user
from Models.user import User



class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_name = Column(String(255), nullable=False)
    stored_name = Column(String(40), nullable=False, unique=True)
    file_path = Column(String(1024), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
