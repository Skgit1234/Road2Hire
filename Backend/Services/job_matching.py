"""Explicit job requirement matching built on the shared semantic matcher."""

import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from AI.Semantic_Matching.semantic_matcher import SemanticSkillMatcher
from AI.Skill_Gap.gap_scoring import compute_gap_scores


def _skill_name(item: Any) -> str:
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        name = item.get("skill") or item.get("name") or item.get("ESCO_Skill_Name")
        return name.strip() if isinstance(name, str) else ""
    return ""


def _uri_matches(
    candidate_names: list[str],
    candidate_mappings: list[Any],
    requirements: list[dict[str, Any]],
) -> tuple[dict[int, dict[str, Any]], str]:
    """Return strict URI matches only when both URIs resolve in the ESCO data."""
    if not candidate_mappings or not any(item["canonical_uri"] for item in requirements):
        return {}, "not_used"

    try:
        from AI.Skill_Extraction.esco_taxonomy import get_esco_taxonomy

        taxonomy = get_esco_taxonomy()
    except Exception:
        return {}, "unavailable"

    candidate_names_by_uri: dict[str, list[str]] = {}
    extracted_by_key = {name.casefold(): name for name in candidate_names}
    for mapping in candidate_mappings:
        if not isinstance(mapping, dict):
            continue
        name = mapping.get("skill")
        uri = mapping.get("ESCO_Skill_Id") or mapping.get("canonical_uri")
        if not isinstance(name, str) or not isinstance(uri, str) or not uri.strip():
            continue
        extracted_name = extracted_by_key.get(name.strip().casefold())
        if extracted_name is None:
            continue
        resolved = taxonomy.get_skill_by_uri(uri)
        if resolved is not None and resolved.concept_uri == uri.strip():
            candidate_names_by_uri.setdefault(resolved.concept_uri, []).append(extracted_name)

    matches: dict[int, dict[str, Any]] = {}
    consumed_candidates: set[str] = set()
    for index, requirement in enumerate(requirements):
        uri = requirement["canonical_uri"]
        if not uri:
            continue
        resolved = taxonomy.get_skill_by_uri(uri)
        if resolved is None or resolved.concept_uri != uri.strip():
            continue
        available = candidate_names_by_uri.get(resolved.concept_uri, [])
        candidate = next(
            (name for name in available if name.casefold() not in consumed_candidates),
            None,
        )
        if candidate is not None:
            consumed_candidates.add(candidate.casefold())
            matches[index] = {
                "candidate_skill": candidate,
                "required_skill": requirement["name"],
                "similarity_score": 1.0,
                "status": "confirmed_match",
                "evidence": "Exact canonical URI equality; both URIs resolve in the ESCO taxonomy.",
            }
    return matches, "used" if matches else "unresolved_or_unmatched"


def _index_matcher_evidence(
    entries: list[Any],
    requirement_indices: list[int],
    requirements: list[dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    """Attach matcher rows to original requirement indices, consuming each candidate once.

    The shared matcher returns labels rather than requirement IDs. For duplicate
    labels, preserve original input order and use each emitted candidate at most
    once so one assignment cannot credit multiple requirement rows.
    """
    indices_by_name: dict[str, list[int]] = {}
    for index in requirement_indices:
        indices_by_name.setdefault(requirements[index]["name"].casefold(), []).append(index)

    indexed: dict[int, dict[str, Any]] = {}
    consumed_candidates: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        required_name = entry.get("required_skill")
        candidate_name = entry.get("candidate_skill")
        if not isinstance(required_name, str) or not isinstance(candidate_name, str):
            continue
        candidate_key = candidate_name.casefold()
        if candidate_key in consumed_candidates:
            continue
        available_indices = indices_by_name.get(required_name.casefold(), [])
        index = next((item for item in available_indices if item not in indexed), None)
        if index is None:
            continue
        indexed[index] = entry
        consumed_candidates.add(candidate_key)
    return indexed


def match_job_requirements(
    candidate_skills: list[Any],
    requirements: list[dict[str, Any]],
    *,
    job_id: int,
    pipeline_run_id: int,
    matcher: SemanticSkillMatcher | None = None,
    candidate_mappings: list[Any] | None = None,
) -> dict[str, Any]:
    """Match extracted candidate skills to requirements and retain match evidence.

    Candidate skills are sourced exclusively from pipeline ``extracted_skills``.
    URI evidence is considered only for those names and only after both URIs
    resolve through the repository's ESCO taxonomy.
    """
    if not isinstance(candidate_skills, list) or not isinstance(requirements, list):
        raise ValueError("Candidate skills and job requirements must be lists.")
    if candidate_mappings is not None and not isinstance(candidate_mappings, list):
        raise ValueError("Candidate skill mappings must be a list.")

    normalized_requirements: list[dict[str, Any]] = []
    for item in requirements:
        if not isinstance(item, dict):
            raise ValueError("A saved job requirement is invalid.")
        name = item.get("skill_name")
        importance = item.get("importance", "essential")
        uri = item.get("canonical_uri")
        if (
            not isinstance(name, str)
            or not name.strip()
            or importance not in ("essential", "optional")
            or uri is not None and not isinstance(uri, str)
        ):
            raise ValueError("A saved job requirement is invalid.")
        normalized_requirements.append({
            "name": name.strip(),
            "importance": importance,
            "canonical_uri": uri,
        })

    if not normalized_requirements:
        return {
            "job_id": job_id,
            "pipeline_run_id": pipeline_run_id,
            "status": "no_requirements",
            "candidate_skill_source": "pipeline.skills.extracted_skills",
            "matching_method": "semantic_skill_matcher",
            "canonical_uri_matching": "not_used",
            "requirements": [],
            "scores": {"essential": None, "optional": None, "overall": None},
        }

    candidate_names: list[str] = []
    seen_names: set[str] = set()
    for item in candidate_skills:
        name = _skill_name(item)
        if name and name.casefold() not in seen_names:
            seen_names.add(name.casefold())
            candidate_names.append(name)

    uri_matches, uri_status = _uri_matches(
        candidate_names, candidate_mappings or [], normalized_requirements,
    )
    consumed_candidates = {
        item["candidate_skill"].casefold() for item in uri_matches.values()
    }
    remaining_names = [name for name in candidate_names if name.casefold() not in consumed_candidates]
    remaining_indices = [i for i in range(len(normalized_requirements)) if i not in uri_matches]

    matched: dict[str, Any] = {"assignments": [], "related_skills": []}
    if remaining_indices and remaining_names:
        matcher = matcher or SemanticSkillMatcher()
        matched = matcher.match(
            remaining_names,
            [normalized_requirements[i]["name"] for i in remaining_indices],
        )

    matcher_requirement_indices = [i for i in remaining_indices]
    assignments_by_index = _index_matcher_evidence(
        matched.get("assignments", []), matcher_requirement_indices, normalized_requirements,
    )
    related_by_index = _index_matcher_evidence(
        matched.get("related_skills", []), matcher_requirement_indices, normalized_requirements,
    )

    results = []
    for index, requirement in enumerate(normalized_requirements):
        name = requirement["name"]
        assignment = uri_matches.get(index)
        if assignment is None:
            assignment = assignments_by_index.get(index)
        related = [related_by_index[index]] if index in related_by_index else []
        if assignment is not None:
            match_status = assignment.get("status", "non_match")
            candidate_skill = assignment.get("candidate_skill")
            similarity_score = assignment.get("similarity_score")
            evidence = assignment.get("evidence")
        elif related:
            match_status = "related_skill"
            candidate_skill = related[0].get("candidate_skill")
            similarity_score = related[0].get("similarity_score")
            evidence = related[0].get("relation")
        else:
            match_status = "non_match" if candidate_names else "missing"
            candidate_skill = None
            similarity_score = None
            evidence = None

        confirmed = match_status == "confirmed_match"
        results.append({
            **requirement,
            "matched": confirmed,
            "candidate_skill": candidate_skill,
            "match_status": match_status,
            "similarity_score": similarity_score,
            "evidence": evidence,
            "related_evidence": [
                {
                    "candidate_skill": item.get("candidate_skill"),
                    "similarity_score": item.get("similarity_score"),
                    "relation": item.get("relation"),
                    "is_equivalent": item.get("is_equivalent", False),
                }
                for item in related
            ],
        })

    essential = [r for r in results if r["importance"] == "essential"]
    optional = [r for r in results if r["importance"] == "optional"]
    scores = compute_gap_scores(
        essential_credits=[1.0 if r["matched"] else 0.0 for r in essential],
        total_essential_count=len(essential),
        optional_credits=[1.0 if r["matched"] else 0.0 for r in optional],
        total_optional_count=len(optional),
    )
    return {
        "job_id": job_id,
        "pipeline_run_id": pipeline_run_id,
        "status": "completed",
        "candidate_skill_source": "pipeline.skills.extracted_skills",
        "candidate_skills_are_verified": False,
        "matching_method": "semantic_skill_matcher",
        "canonical_uri_matching": uri_status,
        "thresholds_are_provisional": True,
        "requirements": results,
        "scores": {
            "essential": scores["essential_skill_coverage_score"],
            "optional": scores["optional_skill_coverage_score"],
            "overall": scores["overall_skill_coverage_score"],
        },
    }
