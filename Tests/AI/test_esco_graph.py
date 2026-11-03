"""Automated tests for NetworkX ESCO Knowledge Graph with Occupation Integration."""

import pytest
import networkx as nx

from AI.Knowledge_Graph.esco_graph import ESCOKnowledgeGraph, get_esco_graph


@pytest.fixture(scope="module")
def graph() -> ESCOKnowledgeGraph:
    """Load the ESCO knowledge graph once for the test module."""
    return get_esco_graph(force_reload=True)


def test_esco_graph_nodes_and_edges(graph: ESCOKnowledgeGraph):
    g = graph.get_graph()
    assert isinstance(g, nx.DiGraph)

    # 13,939 skills + 640 skill groups + 3,039 occupations = 17,618 nodes
    assert g.number_of_nodes() == 17618
    # 158,509 unique directed edges holding 158,512 relation entries (3 dual-relation edges)
    assert g.number_of_edges() == 158509

    total_rel_entries = sum(len(data.get("relations", [])) for u, v, data in g.edges(data=True))
    assert total_rel_entries == 158512


def test_skill_node_attributes(graph: ESCOKnowledgeGraph):
    node = graph.get_skill_node("Python (computer programming)")
    assert node is not None
    assert node["kind"] == "skill"
    assert node["skill_type"] == "knowledge"
    assert node["has_description"] is True
    assert node["uri"] == graph.resolve_skill_uri("Python (computer programming)")


def test_occupation_node_attributes(graph: ESCOKnowledgeGraph):
    node = graph.get_occupation_node("data scientist")
    assert node is not None
    assert node["kind"] == "occupation"
    assert node["label"] == "data scientist"
    assert node["code"] == "2511.4"
    assert node["isco_group"] == "2511"
    assert node["has_description"] is True
    assert node["uri"] == "http://data.europa.eu/esco/occupation/258e46f9-0075-4a2e-adae-1ff0477e0f30"


def test_occupation_lookup_by_uri_and_label(graph: ESCOKnowledgeGraph):
    uri = "http://data.europa.eu/esco/occupation/258e46f9-0075-4a2e-adae-1ff0477e0f30"

    # Exact URI lookup
    assert graph.resolve_occupation_uri(uri) == uri

    # Preferred label lookup (case/whitespace insensitive)
    assert graph.resolve_occupation_uri("  DATA SCIENTIST  ") == uri
    assert graph.resolve_occupation_uri("data scientist") == uri

    # Unknown occupation returns None
    assert graph.resolve_occupation_uri("Nonexistent Occupation XYZ") is None


def test_occupation_skills_retrieval(graph: ESCOKnowledgeGraph):
    skills = graph.get_occupation_skills("data scientist")
    assert len(skills) == 97

    skill_labels = {s["skill_label"] for s in skills}
    assert "data mining" in skill_labels
    assert "mathematical modelling" in skill_labels


def test_essential_vs_optional_skills(graph: ESCOKnowledgeGraph):
    essential = graph.get_essential_skills_for_occupation("data scientist")
    optional = graph.get_optional_skills_for_occupation("data scientist")
    all_skills = graph.get_occupation_skills("data scientist")

    assert len(essential) == 63
    assert len(optional) == 34
    assert len(essential) + len(optional) == len(all_skills)

    for item in essential:
        assert item["relation_type"] == "essential"
    for item in optional:
        assert item["relation_type"] == "optional"


def test_skill_to_occupations_lookup(graph: ESCOKnowledgeGraph):
    occs = graph.get_occupations_for_skill("Python (computer programming)")
    assert len(occs) > 0

    essential_occs = graph.get_occupations_for_skill(
        "Python (computer programming)",
        relation_type="essential",
    )
    optional_occs = graph.get_occupations_for_skill(
        "Python (computer programming)",
        relation_type="optional",
    )

    assert len(essential_occs) + len(optional_occs) == len(occs)
    assert len(essential_occs) > 0


def test_occupation_subgraph_extraction(graph: ESCOKnowledgeGraph):
    sub = graph.get_occupation_subgraph("data scientist", include_skill_groups=False)
    assert isinstance(sub, nx.DiGraph)

    # 1 occupation node + 97 skill nodes = 98 nodes
    assert sub.number_of_nodes() == 98
    occ_uri = graph.resolve_occupation_uri("data scientist")
    assert occ_uri in sub
    assert sub.nodes[occ_uri]["kind"] == "occupation"

    # Filtered by essential only
    sub_essential = graph.get_occupation_subgraph(
        "data scientist",
        relation_type="essential",
    )
    # 1 occupation node + 63 essential skills = 64 nodes
    assert sub_essential.number_of_nodes() == 64


def test_overlapping_skill_relationships_preserved(graph: ESCOKnowledgeGraph):
    """Verify that the 3 dual-relation skill pairs retain both 'related' and 'broader_skill'."""
    overlapping_pairs = [
        ("electroplating metal materials", "electroplating processes", "optional"),
        ("identify statistical patterns", "manage quantitative data", "essential"),
        ("resource description framework query language", "query languages", "optional"),
    ]

    for src, tgt, expected_rel_type in overlapping_pairs:
        # 1. Both relation types exist on the directed edge
        assert graph.has_relation(src, tgt, "related")
        assert graph.has_relation(src, tgt, "broader_skill")

        # 2. Both entries retain their respective metadata
        relations = graph.get_edge_relations(src, tgt)
        assert len(relations) == 2

        rel_by_name = {r["relation"]: r for r in relations}
        assert rel_by_name["related"]["relation_type"] == expected_rel_type
        assert rel_by_name["broader_skill"]["relation_type"] == "hierarchy"

        # 3. Queries can distinguish between related and hierarchy
        all_related = graph.get_related_skills(src, include_hierarchy=True)
        only_related = graph.get_related_skills(src, include_hierarchy=False)

        # When hierarchy is included, both relations appear
        tgt_uri = graph.resolve_skill_uri(tgt)
        assert any(r["target_uri"] == tgt_uri and r["relation"] == "related" for r in all_related)
        assert any(r["target_uri"] == tgt_uri and r["relation"] == "broader_skill" for r in all_related)

        # When hierarchy is excluded, only 'related' appears
        assert any(r["target_uri"] == tgt_uri and r["relation"] == "related" for r in only_related)
        assert not any(r["target_uri"] == tgt_uri and r["relation"] == "broader_skill" for r in only_related)


def test_related_skills_lookup(graph: ESCOKnowledgeGraph):
    related = graph.get_related_skills("Python (computer programming)")
    assert len(related) > 0

    labels = {r["target_label"] for r in related}
    assert "computer programming" in labels


def test_path_finding_between_skills(graph: ESCOKnowledgeGraph):
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


def test_referential_integrity_and_duplicate_prevention(graph: ESCOKnowledgeGraph):
    g = graph.get_graph()

    # Every edge endpoints must exist as valid nodes
    for source, target in g.edges():
        assert source in g
        assert target in g

    # Check kind attribute exists on every node
    for node, data in g.nodes(data=True):
        assert data.get("kind") in ("skill", "skill_group", "occupation")
