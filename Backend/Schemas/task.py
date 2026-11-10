from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TaskProgressUpdate(BaseModel):
    status: Literal["not_started", "in_progress", "completed"] | None = None
    progress: int | None = Field(default=None, ge=0, le=100)


class LearningTaskResponse(BaseModel):
    id: int
    pipeline_run_id: int
    logical_item_key: str
    roadmap_phase_number: int
    roadmap_phase_name: str | None
    skill_name: str
    skill_uri: str | None
    priority: str | None
    status: Literal["not_started", "in_progress", "completed"]
    progress: int = Field(ge=0, le=100)
    roadmap_item_data: dict
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
