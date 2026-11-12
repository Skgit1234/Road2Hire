from typing import Any

from pydantic import BaseModel


class FeatureExplanationResponse(BaseModel):
    pipeline_run_id: int
    resume_id: int
    target_class_explained: str
    base_value: float
    top_positive_factors: list[dict[str, Any]]
    top_negative_factors: list[dict[str, Any]]
    feature_contributions: list[dict[str, Any]]
    human_readable_summary: str
    waterfall_steps: list[dict[str, Any]]
    global_importance_ranking: list[dict[str, Any]]
    limitations: list[str]
