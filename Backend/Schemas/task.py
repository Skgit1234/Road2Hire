from typing import Literal

from pydantic import BaseModel, Field


class TaskProgressUpdate(BaseModel):
    status: Literal["not_started", "in_progress", "completed"] | None = None
    progress: int | None = Field(default=None, ge=0, le=100)
