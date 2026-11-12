from datetime import datetime

from pydantic import BaseModel


class ResumeResponse(BaseModel):
    id: int
    user_id: int
    original_name: str
    stored_name: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


class ResumeUploadResponse(BaseModel):
    message: str
    resume: ResumeResponse
