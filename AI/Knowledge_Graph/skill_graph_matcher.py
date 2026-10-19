
import json
import re
from pathlib import Path
from typing import Any


GRAPH_PATH = Path(__file__).with_name("skill_graph_v1.json")


def normalize_skill_name(name: str) -> str:
    """Normalize a skill name for case-insensitive matching."""
    return re.sub(r"\s+", " ", name.strip()).casefold()


def load_skill_graph(
    graph_path: str | Path = GRAPH_PATH,
) -> dict[str, Any]:
    """Load and validate the skill graph JSON."""
    with Path(graph_path).open("r", encoding="utf-8") as file:
        graph = json.load(file)

    if not isinstance(graph.get("skills"), list):
        raise ValueError("Graph must contain a skills list.")
    if not isinstance(graph.get("relationships"), list):
        raise ValueError("Graph must contain a relationships list.")

    node_ids = set()
    for skill in graph["skills"]:
        if not isinstance(skill, dict) or not skill.get("id") or not skill.get("name"):
            raise ValueError("Each skill must have an id and name.")
        if skill["id"] in node_ids:
            raise ValueError(f"Duplicate skill ID: {skill['id']}")
        node_ids.add(skill["id"])

    for relationship in graph["relationships"]:
        if (
            relationship.get("source") not in node_ids
            or relationship.get("target") not in node_ids
            or not relationship.get("relationship")
        ):
            raise ValueError("Relationship references an invalid node or type.")

    return graph


def match_skills(
    candidate_skills: list[str],
    target_skills: list[str],
    graph_path: str | Path = GRAPH_PATH,
) -> dict[str, Any]:
    """Match skills using graph nodes and actual directed relationships."""
    graph = load_skill_graph(graph_path)
    skills_by_name = {
        normalize_skill_name(skill["name"]): skill
        for skill in graph["skills"]
    }
    skills_by_id = {skill["id"]: skill for skill in graph["skills"]}

    def resolve(names: list[str]) -> tuple[list[dict], list[str]]:
        found = []
        unknown = []
        seen = set()

        for name in names:
            if not isinstance(name, str) or not name.strip():
                continue
            key = normalize_skill_name(name)
            skill = skills_by_name.get(key)
            if skill is None:
                unknown.append(name.strip())
            elif skill["id"] not in seen:
                found.append(skill)
                seen.add(skill["id"])

        return found, unknown

    candidate_nodes, unknown_candidate = resolve(candidate_skills)
    target_nodes, unknown_target = resolve(target_skills)

    candidate_ids = {skill["id"] for skill in candidate_nodes}
    target_ids = {skill["id"] for skill in target_nodes}
    relationships = graph["relationships"]

    evidence = []
    related_candidate_ids = set()

    for relationship in relationships:
        source = relationship["source"]
        target = relationship["target"]

        if source in candidate_ids and target in target_ids:
            evidence.append({
                "candidate_skill": skills_by_id[source]["name"],
                "relationship": relationship["relationship"],
                "target_skill": skills_by_id[target]["name"],
                "direction": "candidate_to_target",
            })
            related_candidate_ids.add(source)

        if source in target_ids and target in candidate_ids:
            evidence.append({
                "candidate_skill": skills_by_id[target]["name"],
                "relationship": relationship["relationship"],
                "target_skill": skills_by_id[source]["name"],
                "direction": "target_to_candidate",
            })
            related_candidate_ids.add(target)

    direct_matches = [
        skill["name"] for skill in candidate_nodes
        if skill["id"] in target_ids
    ]
    related_matches = [
        skill["name"] for skill in candidate_nodes
        if skill["id"] in related_candidate_ids
        and skill["id"] not in target_ids
    ]

    return {
        "direct_matches": direct_matches,
        "related_matches": related_matches,
        "missing_target_skills": [
            skill["name"] for skill in target_nodes
            if skill["id"] not in candidate_ids
        ],
        "unknown_candidate_skills": unknown_candidate,
        "unknown_target_skills": unknown_target,
        "relationship_evidence": evidence,
        "graph_unmatched_candidate_skills": [
            skill["name"] for skill in candidate_nodes
            if skill["id"] not in target_ids
            and skill["id"] not in related_candidate_ids
        ],
        "relationship_types_available": sorted({
            item["relationship"] for item in relationships
        }),
    }
