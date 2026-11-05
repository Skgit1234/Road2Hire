import csv
import logging
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from Api.career_insights import _latest_skill_gap
from Api.profile import get_current_user
from Core.database import get_db
from Models.user import User


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs", tags=["Job Matches"])
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ESCO_MAPPING_PATH = (
    PROJECT_ROOT
    / "Datasets"
    / "ESCO_ONET"
    / "Mappings"
    / "ESCO_Skill_Mapping.csv"
)
ROAD2HIRE_ESCO_MAPPING_PATH = (
    PROJECT_ROOT
    / "Datasets"
    / "Skill_Taxonomy"
    / "Processed"
    / "Road2Hire_ESCO_Mapping.csv"
)


@lru_cache(maxsize=1)
def _load_occupation_data():
    if not ESCO_MAPPING_PATH.is_file() or not ROAD2HIRE_ESCO_MAPPING_PATH.is_file():
        logger.error("ESCO occupation mapping data is unavailable")
        raise HTTPException(
            status_code=503,
            detail="Occupation-matching data is unavailable",
        )

    skill_ids_by_name: dict[str, set[str]] = {}
    skill_names_by_id: dict[str, str] = {}
    occupation_skill_ids: dict[str, set[str]] = {}

    try:
        with ROAD2HIRE_ESCO_MAPPING_PATH.open(
            encoding="utf-8-sig",
            newline="",
        ) as mapping_file:
            for row in csv.DictReader(mapping_file):
                skill_name = (row.get("Road2Hire_Skill") or "").strip()
                skill_id = (row.get("ESCO_Skill_Id") or "").strip()
                if skill_name and skill_id:
                    skill_ids_by_name.setdefault(skill_name.casefold(), set()).add(
                        skill_id
                    )

        with ESCO_MAPPING_PATH.open(encoding="utf-8-sig", newline="") as esco_file:
            for row in csv.DictReader(esco_file):
                skill_id = (row.get("ESCO_Skill_Id") or "").strip()
                skill_name = (row.get("Skill_Name") or "").strip()
                occupation = (row.get("Occupation") or "").strip()
                if not skill_id or not skill_name or not occupation:
                    continue

                skill_ids_by_name.setdefault(skill_name.casefold(), set()).add(
                    skill_id
                )
                skill_names_by_id.setdefault(skill_id, skill_name)
                occupation_skill_ids.setdefault(occupation, set()).add(skill_id)
    except (OSError, UnicodeError, csv.Error) as exc:
        logger.exception("Could not read ESCO occupation-matching data")
        raise HTTPException(
            status_code=503,
            detail="Occupation-matching data could not be read",
        ) from exc

    return skill_ids_by_name, skill_names_by_id, occupation_skill_ids


@router.get("/matches")
def get_job_matches(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    analysis = _latest_skill_gap(db, user.id)
    response_base = {
        "match_type": "occupation",
        "data_source": "ESCO skill-to-occupation mapping",
        "job_listings_available": False,
        "candidate_skills_source": (
            "matched_skills from the latest saved skill-gap analysis"
        ),
    }

    if analysis is None:
        return {
            **response_base,
            "matches": [],
            "message": "Run a skill-gap analysis before requesting occupation matches.",
        }

    if not isinstance(analysis.matched_skills, list) or any(
        not isinstance(skill, str) for skill in analysis.matched_skills
    ):
        logger.error("Skill-gap analysis %s has invalid matched-skills data", analysis.id)
        raise HTTPException(
            status_code=500,
            detail="Saved skill-gap data is invalid",
        )

    candidate_skills = sorted(
        {skill.strip() for skill in analysis.matched_skills if skill.strip()},
        key=str.casefold,
    )
    if not candidate_skills:
        return {
            **response_base,
            "analysis_id": analysis.id,
            "candidate_skills": [],
            "matches": [],
            "message": "The latest skill-gap analysis contains no matched skills.",
        }

    skill_ids_by_name, skill_names_by_id, occupation_skill_ids = (
        _load_occupation_data()
    )
    candidate_names_by_id: dict[str, set[str]] = {}
    unmapped_candidate_skills = []
    for candidate_skill in candidate_skills:
        skill_ids = skill_ids_by_name.get(candidate_skill.casefold(), set())
        if not skill_ids:
            unmapped_candidate_skills.append(candidate_skill)
        for skill_id in skill_ids:
            candidate_names_by_id.setdefault(skill_id, set()).add(candidate_skill)

    matches = []
    candidate_skill_ids = set(candidate_names_by_id)
    for occupation, required_skill_ids in occupation_skill_ids.items():
        matched_skill_ids = required_skill_ids & candidate_skill_ids
        if not matched_skill_ids:
            continue

        matches.append(
            {
                "occupation": occupation,
                "match_score": round(
                    len(matched_skill_ids) / len(required_skill_ids) * 100,
                    2,
                ),
                "matched_skill_count": len(matched_skill_ids),
                "required_skill_count": len(required_skill_ids),
                "matched_skills": [
                    {
                        "candidate_skill": candidate_name,
                        "esco_skill": skill_names_by_id.get(skill_id),
                    }
                    for skill_id in sorted(matched_skill_ids)
                    for candidate_name in sorted(candidate_names_by_id[skill_id])
                ],
            }
        )

    matches.sort(
        key=lambda match: (
            -match["match_score"],
            -match["matched_skill_count"],
            match["occupation"].casefold(),
        )
    )

    message = (
        "No live job listings are present in the repository; these are "
        "occupation-level matches from ESCO data."
    )
    if not matches:
        message = (
            "The verified candidate skills did not produce any occupation "
            "matches from the available ESCO mapping."
        )

    return {
        **response_base,
        "analysis_id": analysis.id,
        "candidate_skills": candidate_skills,
        "unmapped_candidate_skills": unmapped_candidate_skills,
        "formula": (
            "matched distinct ESCO skill identifiers / total distinct ESCO "
            "skill identifiers listed for the occupation * 100"
        ),
        "matches": matches[:limit],
        "message": message,
    }
