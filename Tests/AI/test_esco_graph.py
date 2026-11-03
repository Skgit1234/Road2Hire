"""Automated tests for NetworkX ESCO Knowledge Graph."""

import pytest
import networkx as nx

from AI.Knowledge_Graph.esco_graph import ESCOKnowledgeGraph, get_esco_graph


@pytest.fixture(scope="module")
def graph() -> ESCOKnowledgeGraph:
    """Load the ESCO knowledge graph once for the test module."""
    return get_esco_graph()


def test_esco_graph_nodes_and_edges(graph: ESCOKnowledgeGraph):
    g = graph.get_graph()
    assert isinstance(g, nx.DiGraph)

    # 13,939 unique skills + 640 unique skill groups = 14,579 nodes
    assert g.number_of_nodes() == 14579
    # Relationships: skill-skill + broader/narrower + group memberships
    assert g.number_of_edges() > 30000


def test_skill_node_attributes(graph: ESCOKnowledgeGraph):
    node = graph.get_skill_node("Python (computer programming)")
    assert node is not None
    assert node["kind"] == "skill"
    assert node["skill_type"] == "knowledge"
    assert node["has_description"] is True
    assert node["uri"] == graph.resolve_skill_uri("Python (computer programming)")


def test_related_skills_lookup(graph: ESCOKnowledgeGraph):
    related = graph.get_related_skills("Python (computer programming)")
    assert len(related) > 0

    labels = {r["target_label"] for r in related}
    assert "computer programming" in labels


def test_path_finding_between_skills(graph: ESCOKnowledgeGraph):
    # Python (computer programming) -> broader: computer programming
    path = graph.find_path(
        "Python (computer programming)",
        "computer programming",
    )
    assert path is not None
    assert len(path) == 2
    assert path[0] == graph.resolve_skill_uri("Python (computer programming)")
    assert path[1] == graph.resolve_skill_uri("computer programming")


def test_subgraph_extraction(graph: ESCOKnowledgeGraph):
    sub = graph.get_subgraph(
        ["Python (computer programming)", "machine learning"],
        include_neighbors=False,
    )
    assert isinstance(sub, nx.DiGraph)
    assert sub.number_of_nodes() == 2


def test_graph_matching(graph: ESCOKnowledgeGraph):
    result = graph.match_skills(
        candidate_skills=["Python (computer programming)", "Random Nonexistent Skill"],
        target_skills=["Python (computer programming)", "computer programming"],
    )

    assert "Python (computer programming)" in result["direct_matches"]
    assert "Random Nonexistent Skill" in result["unknown_candidate_skills"]
    assert len(result["missing_target_skills"]) >= 0
