"""Occupation Adapters for Road2Hire M4.2.

Adapts target occupations from:
1. Canonical ESCO Knowledge Graph (essential and optional skills, preferred labels, URIs).
2. Scraped job postings (Datasets/scraped_jobs.json).

Reuses existing ESCOKnowledgeGraph and ESCOTaxonomy logic without duplicating functionality.
"""

from __future__ import annotations

from typing import Any

from AI.Dataset_Preparation.unified_schema import OccupationRequirementSummary
from AI.Knowledge_Graph.esco_graph import ESCOKnowledgeGraph, get_esco_graph


def adapt_esco_occupation(
    occupation_name_or_uri: str,
    graph: ESCOKnowledgeGraph | None = None,
) -> OccupationRequirementSummary:
    """Adapt an ESCO occupation into a standardized requirement summary.

    Parameters
    ----------
    occupation_name_or_uri:
        ESCO preferred label, alternative label, or concept URI.
    graph:
        Optional pre-loaded ESCOKnowledgeGraph instance.

    Returns
    -------
    OccupationRequirementSummary dictionary.

    Raises
    ------
    ValueError
        If the occupation cannot be resolved in ESCO.
    """
    g = graph if graph is not None else get_esco_graph()

    uri = g.resolve_occupation_uri(occupation_name_or_uri.strip())
    if not uri or uri not in g.graph:
        raise ValueError(f"Occupation '{occupation_name_or_uri}' could not be resolved in ESCO.")

    node_data = g.get_occupation_node(uri)
    pref_label = node_data.get("label", occupation_name_or_uri) if node_data else occupation_name_or_uri
    desc = node_data.get("description") if node_data else None

    # Retrieve required skills
    raw_skills = g.get_occupation_skills(uri)
    essential = [s["skill_label"] for s in raw_skills if s.get("relation_type") == "essential"]
    optional = [s["skill_label"] for s in raw_skills if s.get("relation_type") == "optional"]

    return {
        "occupation_id": uri,
        "occupation_title": pref_label,
        "source_type": "esco",
        "total_required_skills": len(raw_skills),
        "essential_skills": essential,
        "optional_skills": optional,
        "description": desc,
    }


def adapt_scraped_job(
    job_record: dict[str, Any],
) -> OccupationRequirementSummary:
    """Adapt a scraped job posting from Datasets/scraped_jobs.json into an occupation summary.

    Parameters
    ----------
    job_record:
        Dictionary parsed from scraped_jobs.json.

    Returns
    -------
    OccupationRequirementSummary dictionary.
    """
    job_id = str(job_record.get("id", "unknown_job"))
    title = str(job_record.get("title", "Untitled Role"))
    desc = job_record.get("description")

    # Scraped jobs do not have pre-extracted ESCO skills; placeholder lists until NER/skill extractor runs
    return {
        "occupation_id": job_id,
        "occupation_title": title,
        "source_type": "scraped_jobs",
        "total_required_skills": 0,
        "essential_skills": [],
        "optional_skills": [],
        "description": desc,
    }

