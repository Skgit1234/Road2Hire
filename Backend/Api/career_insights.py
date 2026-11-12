import logging
import math
from typing import Any, NoReturn

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from Api.profile import get_current_user
from Core.database import get_db
from Models.learning_task import LearningTask
from Models.pipeline_run import PipelineRun
from Models.user import User
from Services.roadmap_utils import logical_item_key
from Schemas.career_readiness import CareerReadinessPredictionResponse
from Schemas.feature_explanation import FeatureExplanationResponse
from Schemas.roadmap import (
    CareerRecommendationsResponse,
    LearningRoadmapResponse,
    RoadmapItemResponse,
    RoadmapPhaseResponse,
    RoadmapResourcesResponse,
)


logger = logging.getLogger(__name__)
router = APIRouter(tags=["Career Insights"])


@router.get(
    "/career-readiness",
    response_model=CareerReadinessPredictionResponse,
)
def get_career_readiness(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    run = (
        db.query(PipelineRun)
        .filter(
            PipelineRun.user_id == user.id,
            PipelineRun.status == "completed",
            PipelineRun.canonical_output.contains({"readiness": {}}),
        )
        .order_by(
            PipelineRun.completed_at.desc().nullslast(),
            PipelineRun.created_at.desc(),
            PipelineRun.id.desc(),
        )
        .first()
    )
    if run is None:
        raise HTTPException(
            status_code=404,
            detail="No completed pipeline run is available",
        )
    return _readiness_response(run)


@router.get(
    "/career-readiness/runs/{run_id}",
    response_model=CareerReadinessPredictionResponse,
)
def get_career_readiness_for_run(
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    run = (
        db.query(PipelineRun)
        .filter(
            PipelineRun.id == run_id,
            PipelineRun.user_id == user.id,
        )
        .first()
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    if run.status != "completed":
        raise HTTPException(
            status_code=409,
            detail="Readiness is available only for completed pipeline runs",
        )
    return _readiness_response(run)


@router.get(
    "/career-readiness/explanations",
    response_model=FeatureExplanationResponse,
)
def get_latest_feature_explanations(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    run = (
        db.query(PipelineRun)
        .filter(
            PipelineRun.user_id == user.id,
            PipelineRun.status == "completed",
            PipelineRun.canonical_output.contains({"explanations": {}}),
        )
        .order_by(
            PipelineRun.completed_at.desc().nullslast(),
            PipelineRun.created_at.desc(),
            PipelineRun.id.desc(),
        )
        .first()
    )
    if run is None:
        raise HTTPException(
            status_code=404,
            detail="No completed pipeline run with explanations is available",
        )
    return _feature_explanation_response(run)


@router.get(
    "/career-readiness/runs/{run_id}/explanations",
    response_model=FeatureExplanationResponse,
)
def get_feature_explanations_for_run(
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    run = (
        db.query(PipelineRun)
        .filter(
            PipelineRun.id == run_id,
            PipelineRun.user_id == user.id,
        )
        .first()
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    if run.status != "completed":
        raise HTTPException(
            status_code=409,
            detail="Feature explanations are available only for completed pipeline runs",
        )
    return _feature_explanation_response(run)


def _feature_explanation_response(
    run: PipelineRun,
) -> FeatureExplanationResponse:
    canonical = run.canonical_output
    explanation = (
        canonical.get("explanations") if isinstance(canonical, dict) else None
    )
    if not isinstance(explanation, dict):
        raise HTTPException(
            status_code=404,
            detail="No feature explanations are available for this pipeline run",
        )

    try:
        return FeatureExplanationResponse(
            pipeline_run_id=run.id,
            resume_id=run.resume_id,
            **explanation,
        )
    except (TypeError, ValueError) as exc:
        logger.error(
            "Pipeline run %s contains invalid feature explanations",
            run.id,
        )
        raise HTTPException(
            status_code=503,
            detail="Saved feature explanations are invalid",
        ) from exc


def _readiness_response(
    run: PipelineRun,
) -> CareerReadinessPredictionResponse:
    canonical = run.canonical_output
    readiness = canonical.get("readiness") if isinstance(canonical, dict) else None
    if not isinstance(readiness, dict):
        raise HTTPException(
            status_code=404,
            detail="No readiness prediction is available for this pipeline run",
        )

    predicted_class = readiness.get("predicted_class")
    class_probabilities = readiness.get("class_probabilities")
    if (
        not isinstance(predicted_class, str)
        or not predicted_class.strip()
        or not isinstance(class_probabilities, dict)
        or not class_probabilities
        or any(
            not isinstance(name, str)
            or isinstance(probability, bool)
            or not isinstance(probability, (int, float))
            or not math.isfinite(probability)
            or probability < 0
            or probability > 1
            for name, probability in class_probabilities.items()
        )
    ):
        logger.error("Pipeline run %s contains invalid readiness data", run.id)
        raise HTTPException(
            status_code=503,
            detail="Saved readiness prediction is invalid",
        )

    return CareerReadinessPredictionResponse(
        pipeline_run_id=run.id,
        resume_id=run.resume_id,
        completed_at=run.completed_at,
        predicted_class=predicted_class,
        class_probabilities={
            name: float(probability)
            for name, probability in class_probabilities.items()
        },
        model_version=_optional_string(
            readiness.get("model_version"), run.id, "model_version"
        ),
        model_type=_optional_string(
            readiness.get("model_type"), run.id, "model_type"
        ),
        is_experimental=_optional_bool(
            readiness.get("is_experimental"), run.id, "is_experimental"
        ),
        is_ood=_optional_bool(readiness.get("is_ood"), run.id, "is_ood"),
        ood_warnings=_string_list(
            readiness.get("ood_warnings"), run.id, "ood_warnings"
        ),
        pipeline_warnings=_string_list(
            canonical.get("warnings"), run.id, "warnings"
        ),
        training_sample_count=_optional_int(
            readiness.get("training_sample_count"),
            run.id,
            "training_sample_count",
        ),
        training_class_distribution=_int_dict(
            readiness.get("training_class_distribution"),
            run.id,
            "training_class_distribution",
        ),
        feature_values=_float_dict(
            readiness.get("feature_values"), run.id, "feature_values"
        ),
        feature_diagnostics=_any_dict(
            readiness.get("feature_diagnostics"), run.id, "feature_diagnostics"
        ),
        limitations=_string_list(
            readiness.get("limitations"), run.id, "limitations"
        ),
    )


def _invalid_readiness_field(run_id: int, field: str) -> NoReturn:
    logger.error("Pipeline run %s has invalid readiness field %s", run_id, field)
    raise HTTPException(status_code=503, detail="Saved readiness prediction is invalid")


def _optional_string(value: object, run_id: int, field: str) -> str | None:
    if value is None or isinstance(value, str):
        return value
    _invalid_readiness_field(run_id, field)


def _optional_bool(value: object, run_id: int, field: str) -> bool | None:
    if value is None or isinstance(value, bool):
        return value
    _invalid_readiness_field(run_id, field)


def _optional_int(value: object, run_id: int, field: str) -> int | None:
    if value is None or (
        isinstance(value, int) and not isinstance(value, bool)
    ):
        return value
    _invalid_readiness_field(run_id, field)


def _string_list(value: object, run_id: int, field: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    _invalid_readiness_field(run_id, field)


def _int_dict(value: object, run_id: int, field: str) -> dict[str, int]:
    if value is None:
        return {}
    if isinstance(value, dict) and all(
        isinstance(key, str)
        and isinstance(item, int)
        and not isinstance(item, bool)
        for key, item in value.items()
    ):
        return value
    _invalid_readiness_field(run_id, field)


def _float_dict(value: object, run_id: int, field: str) -> dict[str, float]:
    if value is None:
        return {}
    if isinstance(value, dict) and all(
        isinstance(key, str)
        and isinstance(item, (int, float))
        and not isinstance(item, bool)
        and math.isfinite(item)
        for key, item in value.items()
    ):
        return {key: float(item) for key, item in value.items()}
    _invalid_readiness_field(run_id, field)


def _any_dict(value: object, run_id: int, field: str) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    _invalid_readiness_field(run_id, field)


@router.get(
    "/recommendations",
    response_model=CareerRecommendationsResponse,
)
def get_latest_recommendations(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    run = _get_pipeline_run(db, user.id)
    return _recommendations_response(run)


@router.get(
    "/recommendations/runs/{run_id}",
    response_model=CareerRecommendationsResponse,
)
def get_recommendations_for_run(
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    run = _get_pipeline_run(db, user.id, run_id)
    return _recommendations_response(run)


@router.get(
    "/learning-roadmap",
    response_model=LearningRoadmapResponse,
)
def get_latest_learning_roadmap(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _learning_roadmap_response(db, _get_pipeline_run(db, user.id))


@router.get(
    "/learning-roadmap/runs/{run_id}",
    response_model=LearningRoadmapResponse,
)
def get_learning_roadmap_for_run(
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _learning_roadmap_response(
        db,
        _get_pipeline_run(db, user.id, run_id),
    )


@router.get(
    "/learning-roadmap/runs/{run_id}/phases/{phase_number}",
    response_model=RoadmapPhaseResponse,
)
def get_roadmap_phase(
    run_id: int,
    phase_number: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not 1 <= phase_number <= 4:
        raise HTTPException(status_code=422, detail="Phase number must be from 1 to 4")
    roadmap = _learning_roadmap_response(
        db,
        _get_pipeline_run(db, user.id, run_id),
    )
    phase = next(
        (phase for phase in roadmap.phases if phase.phase_number == phase_number),
        None,
    )
    if phase is None:
        raise HTTPException(status_code=404, detail="Roadmap phase not found")
    return phase


@router.get(
    "/learning-roadmap/runs/{run_id}/items/{logical_item_key}",
    response_model=RoadmapItemResponse,
)
def get_roadmap_item(
    run_id: int,
    logical_item_key: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    roadmap = _learning_roadmap_response(
        db,
        _get_pipeline_run(db, user.id, run_id),
    )
    for phase in roadmap.phases:
        for item in phase.items:
            if item.logical_item_key == logical_item_key:
                return item
    raise HTTPException(status_code=404, detail="Roadmap item not found")


@router.get(
    "/learning-roadmap/runs/{run_id}/resources",
    response_model=list[RoadmapResourcesResponse],
)
def get_roadmap_resources(
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    roadmap = _learning_roadmap_response(
        db,
        _get_pipeline_run(db, user.id, run_id),
    )
    return [
        _roadmap_resource_response(run_id, item)
        for phase in roadmap.phases
        for item in phase.items
    ]


@router.get(
    "/learning-roadmap/runs/{run_id}/items/{logical_item_key}/resources",
    response_model=RoadmapResourcesResponse,
)
def get_roadmap_item_resources(
    run_id: int,
    logical_item_key: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = get_roadmap_item(
        run_id=run_id,
        logical_item_key=logical_item_key,
        db=db,
        user=user,
    )
    return _roadmap_resource_response(run_id, item)


def _get_pipeline_run(
    db: Session,
    user_id: int,
    run_id: int | None = None,
) -> PipelineRun:
    query = db.query(PipelineRun).filter(
        PipelineRun.user_id == user_id,
        PipelineRun.status == "completed",
    )
    if run_id is not None:
        query = query.filter(PipelineRun.id == run_id)
        run = query.first()
        if run is None:
            exists = db.query(PipelineRun.id).filter(
                PipelineRun.id == run_id,
                PipelineRun.user_id == user_id,
            ).first()
            if exists is None:
                raise HTTPException(status_code=404, detail="Pipeline run not found")
            raise HTTPException(
                status_code=409,
                detail="Results are available only for completed pipeline runs",
            )
        return run

    run = query.order_by(
        PipelineRun.completed_at.desc().nullslast(),
        PipelineRun.created_at.desc(),
        PipelineRun.id.desc(),
    ).first()
    if run is None:
        raise HTTPException(
            status_code=404,
            detail="No completed pipeline run is available",
        )
    return run


def _recommendations_response(
    run: PipelineRun,
) -> CareerRecommendationsResponse:
    canonical = run.canonical_output
    if not isinstance(canonical, dict):
        raise HTTPException(status_code=503, detail="Saved pipeline output is invalid")
    recommendations = canonical.get("occupation_recommendations")
    skills_section = canonical.get("skills")
    candidate_skills = (
        skills_section.get("extracted_skills")
        if isinstance(skills_section, dict)
        else []
    )
    skill_gap = canonical.get("skill_gap")
    if not isinstance(recommendations, list):
        raise HTTPException(
            status_code=404,
            detail="Occupation recommendations are not available for this run",
        )
    if not isinstance(candidate_skills, list):
        candidate_skills = []
    return CareerRecommendationsResponse(
        pipeline_run_id=run.id,
        target_occupation=(
            canonical.get("target_occupation")
            if isinstance(canonical.get("target_occupation"), dict)
            else None
        ),
        recommendations=recommendations,
        candidate_skills=candidate_skills,
        skill_gap=skill_gap if isinstance(skill_gap, dict) else None,
    )


def _learning_roadmap_response(
    db: Session,
    run: PipelineRun,
) -> LearningRoadmapResponse:
    canonical = run.canonical_output
    roadmap = canonical.get("learning_roadmap") if isinstance(canonical, dict) else None
    if not isinstance(roadmap, dict):
        raise HTTPException(
            status_code=404,
            detail="Learning roadmap is not available for this pipeline run",
        )
    phases = roadmap.get("phases")
    if not isinstance(phases, list):
        raise HTTPException(status_code=503, detail="Saved learning roadmap is invalid")

    task_rows = _get_roadmap_tasks(db, run.id)
    tasks_by_key = {task.logical_item_key: task for task in task_rows}
    phase_responses = []
    for phase in phases:
        if not isinstance(phase, dict):
            raise HTTPException(
                status_code=503,
                detail="Saved learning roadmap is invalid",
            )
        phase_number = phase.get("phase_number")
        phase_name = phase.get("phase_name")
        items = phase.get("items")
        if (
            isinstance(phase_number, bool)
            or not isinstance(phase_number, int)
            or not 1 <= phase_number <= 4
            or not isinstance(phase_name, str)
            or not isinstance(items, list)
        ):
            raise HTTPException(
                status_code=503,
                detail="Saved learning roadmap is invalid",
            )
        item_responses = []
        for item in items:
            if not isinstance(item, dict):
                raise HTTPException(
                    status_code=503,
                    detail="Saved learning roadmap is invalid",
                )
            skill_name = item.get("skill_name") or item.get("skill_label")
            skill_uri = item.get("esco_uri") or item.get("skill_uri") or item.get(
                "canonical_uri"
            )
            if not isinstance(skill_name, str) or not skill_name.strip():
                raise HTTPException(
                    status_code=503,
                    detail="Saved learning roadmap item is invalid",
                )
            key = logical_item_key(phase_number, skill_name, skill_uri)
            task = tasks_by_key.get(key)
            if task is None:
                raise HTTPException(
                    status_code=503,
                    detail="Could not persist a roadmap learning item",
                )
            item_responses.append(
                RoadmapItemResponse(
                    logical_item_key=key,
                    roadmap_phase_number=phase_number,
                    roadmap_phase_name=phase_name,
                    skill_name=task.skill_name,
                    skill_uri=task.skill_uri,
                    priority=task.priority,
                    roadmap_item_data=item,
                    current_status=_optional_string(
                        item.get("current_status"), run.id, "current_status"
                    ),
                    importance_rationale=_optional_string(
                        item.get("importance_rationale"),
                        run.id,
                        "importance_rationale",
                    ),
                    learning_outcome=_optional_string(
                        item.get("learning_outcome"), run.id, "learning_outcome"
                    ),
                    suggested_activities=_string_list(
                        item.get("suggested_activities"),
                        run.id,
                        "suggested_activities",
                    ),
                    practical_project=_optional_string(
                        item.get("practical_project"), run.id, "practical_project"
                    ),
                    estimated_duration_weeks=_optional_string(
                        item.get("estimated_duration_weeks"),
                        run.id,
                        "estimated_duration_weeks",
                    ),
                    prerequisites=_string_list(
                        item.get("prerequisites"), run.id, "prerequisites"
                    ),
                    completion_criteria=_optional_string(
                        item.get("completion_criteria"),
                        run.id,
                        "completion_criteria",
                    ),
                    resource_categories=_resource_categories(
                        item.get("resource_categories"), run.id
                    ),
                    status=task.status,
                    progress=task.progress,
                    task_id=task.id,
                    updated_at=task.updated_at,
                )
            )
        phase_responses.append(
            RoadmapPhaseResponse(
                phase_number=phase_number,
                phase_name=phase_name,
                description=_optional_string(
                    phase.get("description"), run.id, "description"
                ) or "",
                estimated_weeks=_optional_string(
                    phase.get("estimated_weeks"), run.id, "estimated_weeks"
                ) or "",
                items=item_responses,
            )
        )
    return LearningRoadmapResponse(
        pipeline_run_id=run.id,
        target_occupation_title=_optional_string(
            roadmap.get("target_occupation_title"), run.id, "target_occupation_title"
        ),
        target_occupation_uri=_optional_string(
            roadmap.get("target_occupation_uri"), run.id, "target_occupation_uri"
        ),
        total_roadmap_skills=_optional_int(
            roadmap.get("total_roadmap_skills"), run.id, "total_roadmap_skills"
        ),
        total_estimated_weeks=_optional_string(
            roadmap.get("total_estimated_weeks"), run.id, "total_estimated_weeks"
        ),
        phases=phase_responses,
        disclaimers=_string_list(roadmap.get("disclaimers"), run.id, "disclaimers"),
    )


def _get_roadmap_tasks(
    db: Session,
    run_id: int,
) -> list[LearningTask]:
    return (
        db.query(LearningTask)
        .filter(LearningTask.pipeline_run_id == run_id)
        .all()
    )


def _roadmap_resource_response(
    run_id: int,
    item: RoadmapItemResponse,
) -> RoadmapResourcesResponse:
    return RoadmapResourcesResponse(
        pipeline_run_id=run_id,
        logical_item_key=item.logical_item_key,
        skill_name=item.skill_name,
        resource_categories=item.resource_categories,
        suggested_activities=item.suggested_activities,
        practical_project=item.practical_project,
        learning_outcome=item.learning_outcome,
        completion_criteria=item.completion_criteria,
    )


def _resource_categories(
    value: object,
    run_id: int,
) -> list[dict[str, str]]:
    if value is None:
        return []
    if isinstance(value, list) and all(
        isinstance(entry, dict)
        and all(isinstance(key, str) and isinstance(item, str) for key, item in entry.items())
        for entry in value
    ):
        return value
    _invalid_readiness_field(run_id, "resource_categories")
