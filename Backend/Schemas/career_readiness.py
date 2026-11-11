from datetime import datetime
from typing import Any

from pydantic import BaseModel


class CareerReadinessPredictionResponse(BaseModel):
    pipeline_run_id: int
    resume_id: int
    completed_at: datetime | None
    predicted_class: str
    class_probabilities: dict[str, float]
    model_version: str | None
    model_type: str | None
    is_experimental: bool | None
    is_ood: bool | None
    ood_warnings: list[str]
    pipeline_warnings: list[str]
    training_sample_count: int | None
    training_class_distribution: dict[str, int]
    feature_values: dict[str, float]
    feature_diagnostics: dict[str, Any]
    limitations: list[str]
