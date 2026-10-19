
from AI.Knowledge_Graph.skill_graph_matcher import match_skills



def test_direct_and_related_matches():
    result = match_skills(
        ["Python", "Scikit-learn"],
        ["Python", "Machine Learning"],
    )

    assert result["direct_matches"] == ["Python"]
    assert result["related_matches"] == ["Scikit-learn"]
    assert result["missing_target_skills"] == ["Machine Learning"]
    assert any(
        item["relationship"] == "related-to"
        for item in result["relationship_evidence"]
    )



def test_unknown_skills_are_preserved():
    result = match_skills(
        ["Python", "Kubernetes"],
        ["SQL", "Unknown Target Skill"],
    )

    assert result["unknown_candidate_skills"] == ["Kubernetes"]
    assert result["unknown_target_skills"] == ["Unknown Target Skill"]


def test_present_but_unrelated_skill_is_reported():
    result = match_skills(["Git"], ["SQL"])

    assert result["graph_unmatched_candidate_skills"] == ["Git"]
    assert result["relationship_evidence"] == []
