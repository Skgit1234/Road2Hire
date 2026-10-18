
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from Core.database import get_db
from Models.resume import Resume
from Models.user import User
from Schemas.resume import ResumeUploadResponse
from Services.file_service import (
    get_resume_file_path,
    remove_resume_file,
    save_resume_file,
)
from Api.profile import get_current_user

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from AI.Resume_Processing.resume_pipeline import process_resume
from AI.Skill_Extraction.skill_extractor import extract_skills


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/resume", tags=["Resume"])
resumes_router = APIRouter(prefix="/resumes", tags=["Resumes"])

MAX_FILE_SIZE = 5 * 1024 * 1024
PDF_SIGNATURE = b"%PDF-"


def _resume_metadata(resume: Resume) -> dict:
    return {
        "id": resume.id,
        "user_id": resume.user_id,
        "original_name": resume.original_name,
        "stored_name": resume.stored_name,
        "uploaded_at": resume.uploaded_at,
        "download_url": f"/resume/{resume.id}/download"
    }


def _list_resumes(db: Session, user: User) -> list[dict]:
    resumes = db.query(Resume).filter(
        Resume.user_id == user.id
    ).order_by(Resume.uploaded_at.desc()).all()
    return [_resume_metadata(resume) for resume in resumes]


@resumes_router.get("")
@resumes_router.get("/", include_in_schema=False)
def list_user_resumes(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    return _list_resumes(db, user)


@resumes_router.delete("/{resume_id}")
def delete_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == user.id
    ).first()

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    try:
        file_path = get_resume_file_path(resume.file_path)
    except ValueError as exc:
        logger.error("Refusing to delete resume %s outside the upload directory", resume_id)
        raise HTTPException(
            status_code=500,
            detail="Resume file path is invalid"
        ) from exc

    try:
        db.delete(resume)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Could not delete resume metadata for resume %s", resume_id)
        raise HTTPException(
            status_code=500,
            detail="Could not delete resume"
        ) from exc

    try:
        remove_resume_file(str(file_path))
    except OSError as exc:
        logger.exception("Could not remove file for deleted resume %s", resume_id)
        raise HTTPException(
            status_code=500,
            detail="Resume was deleted, but its file could not be removed"
        ) from exc

    return {"message": "Resume deleted successfully", "resume_id": resume_id}


@router.get("/{resume_id}/download")
def download_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == user.id
    ).first()

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Resume not found"
        )

    file_path = Path(resume.file_path)

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Resume file not found on server"
        )

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=resume.original_name
    )


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    user_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    original_name = file.filename or ""

    if not original_name or Path(original_name).suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="File must have the application/pdf content type",
        )

    if len(original_name) > 255:
        raise HTTPException(
            status_code=400,
            detail="Filename must be 255 characters or fewer"
        )

    contents = await file.read(MAX_FILE_SIZE + 1)

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="PDF file must be 5 MB or smaller"
        )

    if not contents.startswith(PDF_SIGNATURE):
        raise HTTPException(
            status_code=400,
            detail="File does not have a valid PDF signature"
        )

    file_path = None

    try:
        if db.query(User.id).filter(User.id == user_id).first() is None:
            raise HTTPException(status_code=404, detail="User not found")

        stored_name, file_path = save_resume_file(contents)

        resume = Resume(
            user_id=user_id,
            original_name=original_name,
            stored_name=stored_name,
            file_path=file_path,
        )

        db.add(resume)
        db.flush()
        db.refresh(resume)
        db.commit()

    except HTTPException:
        raise

    except OSError as exc:
        db.rollback()

        if file_path is not None:
            try:
                remove_resume_file(file_path)
            except OSError:
                logger.exception("Could not remove uploaded resume after storage failure")

        logger.exception("Could not store uploaded resume", exc_info=exc)
        raise HTTPException(
            status_code=500,
            detail="Could not store uploaded resume"
        ) from exc

    except SQLAlchemyError as exc:
        db.rollback()

        if file_path is not None:
            try:
                remove_resume_file(file_path)
            except OSError:
                logger.exception("Could not remove uploaded resume after database failure")

        logger.exception("Could not save resume metadata", exc_info=exc)
        raise HTTPException(
            status_code=500,
            detail="Could not save resume metadata"
        ) from exc

    return {"message": "Resume uploaded successfully", "resume": resume}



@router.get("/{resume_id}/analysis")
def analyze_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == user.id
    ).first()

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Resume not found"
        )

    file_path = Path(resume.file_path)

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Resume file not found on server"
        )

    try:
        result = process_resume(file_path)

        if result["extraction_status"] == "needs_ocr":
            raise HTTPException(
                status_code=422,
                detail="This PDF contains no extractable text. OCR is required."
            )

        skill_result = extract_skills(result)

        return {
            "resume_id": resume.id,
            "original_name": resume.original_name,
            "status": "completed",
            "pipeline_version": result["pipeline_version"],
            "extraction_status": result["extraction_status"],
            "page_count": result["page_count"],
            "sections": result["sections"],
            "detected_section_names": result["detected_section_names"],
            "extracted_skills": skill_result["skills"],
            "skill_count": skill_result["skill_count"],
            "skill_extraction_method": skill_result["extraction_method"]
        }

    except HTTPException:
        raise
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Could not analyze this resume: {exc}"
        ) from exc
    except Exception as exc:
        logger.exception("Resume analysis failed for resume %s", resume_id)
        raise HTTPException(
            status_code=500,
            detail="Resume analysis failed"
        ) from exc
