
import hashlib
import json
import logging
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from AI.Baseline.keyword_baseline import keyword_match
from AI.Resume_Processing.resume_pipeline import process_resume
from AI.Skill_Extraction.skill_extractor import extract_skills
from Api.profile import get_current_user
from Core.database import get_db
from Models.resume import Resume
from Models.skill_gap import SkillGap

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/skill-gaps", tags=["Skill Gaps"])


@router.get("/history")
def get_skill_gap_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(SkillGap).filter(
        SkillGap.user_id == current_user.id
    )

    total = query.count()

    items = (
        query.order_by(SkillGap.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "items": [
            {
                "id": item.id,
                "resume_id": item.resume_id,
                "target_role": item.target_role,
                "required_skills": item.required_skills,
                "matched_skills": item.matched_skills,
                "missing_skills": item.missing_skills,
                "match_score": item.match_score,
                "created_at": item.created_at,
            }
            for item in items
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/history/{analysis_id}")
def get_skill_gap_history_item(
    analysis_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = (
        db.query(SkillGap)
        .filter(
            SkillGap.id == analysis_id,
            SkillGap.user_id == current_user.id,
        )
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Skill gap analysis not found",
        )

    return {
        "id": item.id,
        "resume_id": item.resume_id,
        "target_role": item.target_role,
        "required_skills": item.required_skills,
        "matched_skills": item.matched_skills,
        "missing_skills": item.missing_skills,
        "match_score": item.match_score,
        "created_at": item.created_at,
    }

@router.get("/")
def get_skill_gaps(
    resume_id: int,
    target_role: str,
    required_skills: list[str] = Query(..., min_length=1),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target_role = target_role.strip()
    required_skills = sorted({
        skill.strip()
        for skill in required_skills
        if skill.strip()
    }, key=str.casefold)

    if not target_role or not required_skills:
        raise HTTPException(
            status_code=422,
            detail="Target role and required skills cannot be empty.",
        )

    resume = (
        db.query(Resume)
        .filter(
            Resume.id == resume_id,
            Resume.user_id == current_user.id,
        )
        .first()
    )

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    file_path = Path(resume.file_path)

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Resume file not found")

    try:
        # Hash the resume contents and analysis inputs.
        # Changed resume contents or requirements produce a new analysis.
        resume_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        cache_data = json.dumps(
            {
                "resume_hash": resume_hash,
                "target_role": target_role.casefold(),
                "required_skills": [
                    skill.casefold() for skill in required_skills
                ],
            },
            sort_keys=True,
        )
        analysis_hash = hashlib.sha256(
            cache_data.encode("utf-8")
        ).hexdigest()

        # Reuse an existing analysis if its inputs have not changed.
        saved = (
            db.query(SkillGap)
            .filter(
                SkillGap.resume_id == resume.id,
                SkillGap.user_id == current_user.id,
                SkillGap.requirements_hash == analysis_hash,
            )
            .first()
        )

        if saved:
            return {
                "id": saved.id,
                "resume_id": saved.resume_id,
                "target_role": saved.target_role,
                "required_skills": saved.required_skills,
                "matched_skills": saved.matched_skills,
                "missing_skills": saved.missing_skills,
                "match_score": saved.match_score,
                "created_at": saved.created_at,
                "cached": True,
            }

        # Calculate only when no matching saved result exists.
        resume_data = process_resume(str(file_path))

        if resume_data.get("extraction_status") == "needs_ocr":
            raise HTTPException(
                status_code=422,
                detail="This resume requires OCR before analysis.",
            )

        extracted = extract_skills(resume_data)
        candidate_skills = [
            item["skill"] for item in extracted["skills"]
        ]

        result = keyword_match(candidate_skills, required_skills)

        matched = result["present_skills"]
        missing = result["missing_skills"]

        # The existing endpoint converts the matcher score to a percentage.
        score = round(result["match_score"] * 100, 2)

        saved = SkillGap(
            user_id=current_user.id,
            resume_id=resume.id,
            target_role=target_role,
            requirements_hash=analysis_hash,
            required_skills=required_skills,
            matched_skills=matched,
            missing_skills=missing,
            match_score=score,
        )

        db.add(saved)
        db.commit()
        db.refresh(saved)

        return {
            "id": saved.id,
            "resume_id": saved.resume_id,
            "target_role": saved.target_role,
            "required_skills": saved.required_skills,
            "matched_skills": saved.matched_skills,
            "missing_skills": saved.missing_skills,
            "match_score": saved.match_score,
            "created_at": saved.created_at,
            "cached": False,
        }

    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Skill gap analysis failed")
        raise HTTPException(
            status_code=500,
            detail="Skill gap analysis failed.",
        ) from exc
