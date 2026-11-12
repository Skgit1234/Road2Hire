import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from Api.profile import get_current_user
from Core.database import get_db
from Models.pipeline_run import PipelineRun
from Models.resume import Resume
from Models.user import User
from Schemas.skill_gap import (
    KnowledgeGraphResponse,
    PipelineRunResultResponse,
    SkillGapAnalysisRequest,
    SkillGapAnalysisResponse,
    SkillGapHistoryItem,
    SkillGapHistoryResponse,
    SkillPriorityResponse,
)
from Services.file_service import get_resume_file_path
from Services.pipeline_service import (
    ResumeFileValidationError,
    ResumeOwnershipError,
    run_pipeline_for_resume,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/skill-gaps", tags=["Skill Gaps"])


@router.post("/analyze", response_model=SkillGapAnalysisResponse)
def analyze_skill_gap(
    details: SkillGapAnalysisRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _analyze_for_resume(
        db=db,
        user=user,
        resume_id=details.resume_id,
        target_occupation=details.target_occupation,
        auto_select_top_occupation=details.auto_select_top_occupation,
    )


@router.get("/", response_model=SkillGapAnalysisResponse)
def get_skill_gaps(
    resume_id: int = Query(..., gt=0),
    target_role: str = Query(..., min_length=1, max_length=512),
    required_skills: list[str] | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    target_role = target_role.strip()
    if not target_role:
        raise HTTPException(status_code=422, detail="Target role cannot be blank")

    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == user.id,
    ).first()
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")

    try:
        file_path = get_resume_file_path(resume.file_path)
    except (ValueError, OSError, RuntimeError) as exc:
        logger.warning("Refusing to access resume %s outside the upload directory", resume_id)
        raise HTTPException(
            status_code=404,
            detail="Resume file not found",
        ) from exc

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Resume file not found")

    run = (
        db.query(PipelineRun)
        .filter(
            PipelineRun.user_id == user.id,
            PipelineRun.resume_id == resume_id,
            func.lower(PipelineRun.target_occupation_title) == target_role.casefold(),
        )
        .order_by(PipelineRun.created_at.desc(), PipelineRun.id.desc())
        .first()
    )
    if run is None:
        raise HTTPException(
            status_code=404,
            detail="No existing analysis found for this resume and target role. Submit a new analysis.",
        )

    warnings = []
    if required_skills:
        warnings.append(
            "Custom required_skills are stored with jobs but are not independently "
            "evaluated by the unified pipeline; results use ESCO occupation requirements."
        )
    return _analysis_response(run, warnings=warnings)


@router.get("/history", response_model=SkillGapHistoryResponse)
def get_skill_gap_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(PipelineRun).filter(PipelineRun.user_id == user.id)
    total = query.count()
    runs = (
        query.order_by(PipelineRun.created_at.desc(), PipelineRun.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return SkillGapHistoryResponse(
        items=[_history_item(run) for run in runs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/history/{analysis_id}", response_model=SkillGapAnalysisResponse)
def get_skill_gap_history_item(
    analysis_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    run = _owned_run(db, analysis_id, user.id)
    return _analysis_response(run)


@router.get("/runs/{run_id}", response_model=PipelineRunResultResponse)
def get_pipeline_run_result(
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    run = _owned_run(db, run_id, user.id)
    error = None
    if run.status == "failed":
        error = {
            "code": run.error_code,
            "stage": run.error_stage,
            "message": run.error_message,
        }
    return PipelineRunResultResponse(
        pipeline_run_id=run.id,
        status=run.status,
        resume_id=run.resume_id,
        canonical_output=_canonical(run),
        error=error,
    )


@router.get("/runs/{run_id}/priorities", response_model=SkillPriorityResponse)
def get_run_skill_priorities(
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    run = _owned_run(db, run_id, user.id)
    canonical = _canonical(run)
    roadmap = canonical.get("learning_roadmap")
    target = canonical.get("target_occupation")
    items: list[dict[str, Any]] = []
    if isinstance(roadmap, dict):
        phases = roadmap.get("phases")
        if isinstance(phases, list):
            for phase in phases:
                if not isinstance(phase, dict):
                    continue
                phase_items = phase.get("items")
                if not isinstance(phase_items, list):
                    continue
                for item in phase_items:
                    if isinstance(item, dict):
                        items.append(
                            {
                                **item,
                                "phase_number": phase.get("phase_number"),
                                "phase_name": phase.get("phase_name"),
                            }
                        )
    return SkillPriorityResponse(
        pipeline_run_id=run.id,
        target_occupation=target if isinstance(target, dict) else None,
        items=items,
    )


@router.get("/runs/{run_id}/knowledge-graph", response_model=KnowledgeGraphResponse)
def get_run_knowledge_graph(
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    run = _owned_run(db, run_id, user.id)
    canonical = _canonical(run)
    graph_summary = canonical.get("knowledge_graph")
    if not isinstance(graph_summary, dict):
        graph_summary = {}
    gap = canonical.get("skill_gap")
    if not isinstance(gap, dict):
        gap = {}
    nodes, relationships = _skill_graph_view(gap)
    return KnowledgeGraphResponse(
        pipeline_run_id=run.id,
        summary=graph_summary,
        nodes=nodes,
        relationships=relationships,
        scope=(
            "Skill-match relationships are derived from canonical matched and "
            "partially matched evidence; the canonical pipeline output stores "
            "graph summary metrics rather than the complete graph topology."
        ),
    )


def _analyze_for_resume(
    *,
    db: Session,
    user: User,
    resume_id: int,
    target_occupation: str | None,
    auto_select_top_occupation: bool,
    warnings: list[str] | None = None,
) -> SkillGapAnalysisResponse:
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == user.id,
    ).first()
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")

    user_ref = User(id=user.id)
    resume_ref = Resume(id=resume.id, user_id=resume.user_id)
    db.rollback()

    try:
        run = run_pipeline_for_resume(
            user=user_ref,
            resume=resume_ref,
            target_occupation=target_occupation,
            auto_select_top_occupation=auto_select_top_occupation,
        )
    except ResumeOwnershipError as exc:
        raise HTTPException(status_code=404, detail="Resume not found") from exc
    except ResumeFileValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Could not run skill-gap analysis for resume %s", resume_id)
        raise HTTPException(
            status_code=500,
            detail="Could not run skill-gap analysis",
        ) from exc

    return _analysis_response(run, warnings=warnings)


def _owned_run(db: Session, run_id: int, user_id: int) -> PipelineRun:
    run = db.query(PipelineRun).filter(
        PipelineRun.id == run_id,
        PipelineRun.user_id == user_id,
    ).first()
    if run is None:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return run


def _analysis_response(
    run: PipelineRun,
    *,
    warnings: list[str] | None = None,
) -> SkillGapAnalysisResponse:
    canonical = _canonical(run)
    target = canonical.get("target_occupation")
    gap = canonical.get("skill_gap")
    roadmap = canonical.get("learning_roadmap")
    graph = canonical.get("knowledge_graph")
    error = None
    if run.status == "failed":
        error = {
            "code": run.error_code,
            "stage": run.error_stage,
            "message": run.error_message,
        }
    return SkillGapAnalysisResponse(
        pipeline_run_id=run.id,
        status=run.status,
        matching_basis="Unified AI pipeline skill matching against ESCO occupation requirements.",
        warnings=warnings or [],
        target_occupation=target if isinstance(target, dict) else None,
        skill_gap=gap if isinstance(gap, dict) else None,
        learning_roadmap=roadmap if isinstance(roadmap, dict) else None,
        knowledge_graph=graph if isinstance(graph, dict) else None,
        error=error,
    )


def _history_item(run: PipelineRun) -> SkillGapHistoryItem:
    return SkillGapHistoryItem(
        id=run.id,
        resume_id=run.resume_id,
        status=run.status,
        target_occupation_uri=run.target_occupation_uri,
        target_occupation_title=run.target_occupation_title,
        overall_skill_coverage_score=run.overall_skill_coverage_score,
        essential_skill_coverage_score=run.essential_skill_coverage_score,
        optional_skill_coverage_score=run.optional_skill_coverage_score,
        readiness_class=run.readiness_class,
        created_at=run.created_at,
        completed_at=run.completed_at,
    )


def _canonical(run: PipelineRun) -> dict[str, Any]:
    return run.canonical_output if isinstance(run.canonical_output, dict) else {}


def _skill_graph_view(
    gap: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    nodes: dict[str, dict[str, Any]] = {}
    relationships: list[dict[str, Any]] = []

    for field, relationship_type in (
        ("matched_skills", "matches_skill"),
        ("partially_matched_skills", "partially_matches_skill"),
    ):
        evidence = gap.get(field)
        if not isinstance(evidence, list):
            continue
        for item in evidence:
            if not isinstance(item, dict):
                continue
            candidate = item.get("candidate_skill")
            target = item.get("target_skill")
            candidate_uri = item.get("candidate_uri")
            target_uri = item.get("target_uri")
            if not isinstance(candidate, str) or not isinstance(target, str):
                continue
            source_id = candidate_uri or f"candidate-skill:{candidate.casefold()}"
            target_id = target_uri or f"esco-skill:{target.casefold()}"
            nodes[source_id] = {
                "id": source_id,
                "label": candidate,
                "kind": "candidate_skill",
            }
            nodes[target_id] = {
                "id": target_id,
                "label": target,
                "kind": "esco_skill",
            }
            relationships.append(
                {
                    "source": source_id,
                    "target": target_id,
                    "type": relationship_type,
                    "tier": item.get("tier"),
                    "graph_relationship": item.get("graph_relationship"),
                    "credit_assigned": item.get("credit_assigned"),
                    "similarity_score": item.get("similarity_score"),
                    "explanation": item.get("explanation"),
                }
            )

    for field, requirement_type in (
        ("missing_essential_skills", "essential"),
        ("missing_optional_skills", "optional"),
    ):
        missing = gap.get(field)
        if not isinstance(missing, list):
            continue
        for item in missing:
            if not isinstance(item, dict):
                continue
            label = item.get("skill_label")
            uri = item.get("skill_uri")
            if not isinstance(label, str):
                continue
            node_id = uri or f"esco-skill:{label.casefold()}"
            nodes[node_id] = {
                "id": node_id,
                "label": label,
                "kind": "esco_skill",
                "gap_status": "missing",
                "requirement_type": requirement_type,
            }

    return list(nodes.values()), relationships
