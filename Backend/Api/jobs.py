import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from Api.profile import get_current_user
from Core.database import get_db
from Models.job import Job
from Models.pipeline_run import PipelineRun
from Models.resume import Resume
from Models.user import User
from Schemas.job import (
    JobCreate,
    JobMatchRequest,
    JobMatchingResponse,
    JobResponse,
    OccupationMatchesResponse,
    PipelineRunResponse,
)
from Services.pipeline_service import (
    ResumeFileValidationError,
    ResumeOwnershipError,
    run_pipeline_for_resume,
)
from Services.job_matching import match_job_requirements


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs", tags=["Job Matches"])


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_job(
    details: JobCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job = Job(
        user_id=user.id,
        title=details.title,
        description=details.description,
        target_occupation=details.target_occupation,
        required_skills=[
            skill.model_dump() for skill in details.required_skills
        ],
    )
    try:
        db.add(job)
        db.commit()
        db.refresh(job)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Could not save job for user %s", user.id)
        raise HTTPException(
            status_code=500,
            detail="Could not save job",
        ) from exc
    return job


@router.get("", response_model=list[JobResponse])
@router.get("/", response_model=list[JobResponse], include_in_schema=False)
def list_jobs(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return (
        db.query(Job)
        .filter(Job.user_id == user.id)
        .order_by(Job.created_at.desc(), Job.id.desc())
        .all()
    )


@router.get("/matches", response_model=OccupationMatchesResponse)
def get_job_matches(
    resume_id: int | None = Query(default=None, gt=0),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(PipelineRun).filter(
        PipelineRun.user_id == user.id,
        PipelineRun.status == "completed",
    )
    if resume_id is not None:
        resume = db.query(Resume).filter(
            Resume.id == resume_id,
            Resume.user_id == user.id,
        ).first()
        if resume is None:
            raise HTTPException(status_code=404, detail="Resume not found")
        query = query.filter(PipelineRun.resume_id == resume_id)

    run = query.order_by(
        PipelineRun.created_at.desc(),
        PipelineRun.id.desc(),
    ).first()
    if run is None:
        return OccupationMatchesResponse(
            analysis_id=None,
            candidate_skills=[],
            matches=[],
            message="Run skill matching before requesting occupation matches.",
        )

    canonical = run.canonical_output if isinstance(run.canonical_output, dict) else {}
    skills_section = canonical.get("skills")
    candidate_skills = (
        skills_section.get("extracted_skills", [])
        if isinstance(skills_section, dict)
        else []
    )
    recommendations = canonical.get("occupation_recommendations", [])
    if not isinstance(candidate_skills, list):
        candidate_skills = []
    if not isinstance(recommendations, list):
        recommendations = []

    return OccupationMatchesResponse(
        analysis_id=run.id,
        candidate_skills=candidate_skills,
        matches=recommendations[:limit],
        message=(
            "Matches are ESCO occupation recommendations from the saved pipeline run; "
            "live job listings are not available."
        ),
    )


@router.post(
    "/{job_id}/matches",
    response_model=JobMatchingResponse,
)
def match_resume_to_job(
    job_id: int,
    details: JobMatchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == user.id,
    ).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    resume = db.query(Resume).filter(
        Resume.id == details.resume_id,
        Resume.user_id == user.id,
    ).first()
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")

    user_ref = User(id=user.id)
    resume_ref = Resume(id=resume.id, user_id=resume.user_id)
    user_id = user.id
    resume_pk = resume.id
    job_pk = job.id
    job_response = JobResponse.model_validate(job)
    target_occupation = job.target_occupation
    db.rollback()

    try:
        run = run_pipeline_for_resume(
            user=user_ref,
            resume=resume_ref,
            target_occupation=target_occupation,
        )
    except ResumeOwnershipError as exc:
        raise HTTPException(status_code=404, detail="Resume not found") from exc
    except ResumeFileValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception(
            "Could not match resume %s to job %s for user %s",
            resume_pk,
            job_pk,
            user_id,
        )
        raise HTTPException(
            status_code=500,
            detail="Could not run job matching",
        ) from exc

    canonical = run.canonical_output if isinstance(run.canonical_output, dict) else {}
    skills = canonical.get("skills")
    extracted_skills = (
        skills.get("extracted_skills", []) if isinstance(skills, dict) else []
    )
    if not isinstance(extracted_skills, list):
        extracted_skills = []
    candidate_mappings = (
        skills.get("esco_mappings", []) if isinstance(skills, dict) else []
    )
    if not isinstance(candidate_mappings, list):
        candidate_mappings = []
    job_requirements = job_response.required_skills
    job_specific_matching = None
    if run.status == "completed":
        try:
            job_specific_matching = match_job_requirements(
                extracted_skills,
                [item.model_dump() for item in job_requirements],
                job_id=job_pk,
                pipeline_run_id=run.id,
                candidate_mappings=candidate_mappings,
            )
        except ValueError as exc:
            raise HTTPException(status_code=500, detail="Saved job requirements are invalid") from exc
        except Exception as exc:
            logger.exception("Job requirement matching failed for job %s run %s", job_pk, run.id)
            raise HTTPException(status_code=503, detail="Job-specific skill matching is unavailable") from exc

    has_requirements = bool(job_requirements)
    return JobMatchingResponse(
        job=job_response,
        run=PipelineRunResponse.model_validate(run),
        matching_basis=(
            "Occupation-based analysis comes from the unified pipeline target ESCO occupation. "
            "Job-specific analysis separately compares pipeline-extracted candidate skills "
            "with this job's stored requirements."
        ),
        job_specific_required_skills_applied=(
            has_requirements and job_specific_matching is not None
            and job_specific_matching.get("status") == "completed"
        ),
        job_specific_matching=job_specific_matching,
    )


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == user.id,
    ).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
