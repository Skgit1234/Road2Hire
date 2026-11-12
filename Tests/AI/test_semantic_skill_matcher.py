"""Tests for Semantic Skill Matcher (Issue #17).

Validates Sentence Transformer semantic matching, unknown skill preservation,
bipartite assignment, deceptive pair rejection, related skill separation, and
edge cases without regressing Issue #16 baselines.
"""

from __future__ import annotations

import pytest

from AI.Semantic_Matching.semantic_matcher import (
    PROVISIONAL_MATCH_THRESHOLD,
    PROVISIONAL_UNCERTAIN_THRESHOLD,
    SemanticSkillMatcher,
    compute_ranking_ndcg,
    semantic_match,
)


# =====================================================================
# 1. Edge Cases: Empty Inputs and Duplicates
# =====================================================================

def test_empty_candidate_skills():
    """Empty candidate skill list returns all required skills as missing."""
    candidate = []
    required = ["Python", "Machine Learning"]

    res = semantic_match(candidate, required)

    assert res["present_skills"] == []
    assert res["missing_skills"] == ["Python", "Machine Learning"]
    assert res["match_score"] == 0.0
    assert res["tp"] == 0
    assert res["fn"] == 2
    assert res["fp"] == 0
    assert res["precision"] is None
    assert res["recall"] == 0.0
    assert res["f1"] is None
    assert res["ndcg"] is None


def test_empty_required_skills():
    """Empty required skill list returns match_score 0.0 and None for metrics."""
    candidate = ["Python", "SQL"]
    required = []

    res = semantic_match(candidate, required)

    assert res["present_skills"] == []
    assert res["missing_skills"] == []
    assert res["candidate_skills_not_required"] == ["Python", "SQL"]
    assert res["match_score"] == 0.0
    assert res["tp"] == 0
    assert res["fn"] == 0
    assert res["precision"] is None
    assert res["recall"] is None
    assert res["f1"] is None


def test_both_candidate_and_required_empty():
    """Both candidate and required skill lists empty."""
    res = semantic_match([], [])

    assert res["present_skills"] == []
    assert res["missing_skills"] == []
    assert res["match_score"] == 0.0
    assert res["tp"] == 0
    assert res["fn"] == 0


def test_duplicate_skills_deduplication():
    """Duplicate candidate or required skills are deduplicated safely."""
    candidate = ["Python", "python", " PYTHON ", "Pandas"]
    required = ["Python", "python", "NumPy"]

    res = semantic_match(candidate, required)

    # Should only match Python once
    assert res["present_skills"] == ["Python"]
    assert res["missing_skills"] == ["NumPy"]
    assert res["candidate_skills_not_required"] == ["Pandas"]
    assert res["tp"] == 1
    assert res["fn"] == 1


# =====================================================================
# 2. Unknown and Unrecognized Skill Preservation
# =====================================================================

def test_unrecognized_skills_preserved_not_discarded():
    """Skills not in curated vocabulary or ESCO are preserved in unrecognized_skills."""
    candidate = ["Rust", "FastAPI", "Terraform"]
    required = ["Rust", "Go"]

    res = semantic_match(candidate, required)

    # Neither Rust nor Go nor FastAPI nor Terraform are in skill_graph_v1.json
    assert "Rust" in res["unrecognized_skills"]["candidate"]
    assert "FastAPI" in res["unrecognized_skills"]["candidate"]
    assert "Terraform" in res["unrecognized_skills"]["candidate"]
    assert "Rust" in res["unrecognized_skills"]["required"]
    assert "Go" in res["unrecognized_skills"]["required"]

    # Rust matches Rust via string equivalence even though unrecognized
    assert "Rust" in res["present_skills"]
    assert "Go" in res["missing_skills"]


def test_rust_and_go_are_distinct():
    """Rust and Go must NOT match each other; they are distinct languages."""
    candidate = ["Rust"]
    required = ["Go"]

    res = semantic_match(candidate, required)

    assert res["present_skills"] == []
    assert res["missing_skills"] == ["Go"]
    assert res["candidate_skills_not_required"] == ["Rust"]
    assert res["tp"] == 0
    assert res["fn"] == 1


def test_golang_and_go_match():
    """Golang and Go match as aliases of the same programming language."""
    candidate = ["Golang"]
    required = ["Go"]

    res = semantic_match(candidate, required)

    assert res["present_skills"] == ["Go"]
    assert res["missing_skills"] == []
    assert res["tp"] == 1
    assert res["fn"] == 0
    assert res["match_score"] == 1.0


def test_postgres_and_postgresql_match():
    """Postgres matches PostgreSQL with high semantic similarity."""
    candidate = ["Postgres"]
    required = ["PostgreSQL"]

    res = semantic_match(candidate, required)

    assert res["present_skills"] == ["PostgreSQL"]
    assert res["missing_skills"] == []
    assert res["tp"] == 1


# =====================================================================
# 3. Deceptive Lexical & Topical Pairs Rejection
# =====================================================================

def test_java_and_javascript_rejected():
    """Java and JavaScript must NEVER be treated as equivalent."""
    candidate = ["Java"]
    required = ["JavaScript"]

    res = semantic_match(candidate, required)

    assert "JavaScript" in res["missing_skills"]
    assert "JavaScript" not in res["present_skills"]
    assert "Java" in res["candidate_skills_not_required"]
    assert res["tp"] == 0


def test_c_and_cpp_rejected():
    """C and C++ must NEVER be treated as equivalent."""
    candidate = ["C"]
    required = ["C++"]

    res = semantic_match(candidate, required)

    assert "C++" in res["missing_skills"]
    assert "C++" not in res["present_skills"]
    assert res["tp"] == 0


# =====================================================================
# 4. Related Skills vs Confirmed Equivalences
# =====================================================================

def test_docker_and_kubernetes_related_not_equivalent():
    """Docker and Kubernetes are related tools, NOT interchangeable equivalents."""
    candidate = ["Docker"]
    required = ["Kubernetes"]

    res = semantic_match(candidate, required)

    # Kubernetes remains missing
    assert "Kubernetes" in res["missing_skills"]
    assert res["present_skills"] == []
    assert res["tp"] == 0

    # Identified in related_skills
    assert len(res["related_skills"]) == 1
    rel = res["related_skills"][0]
    assert rel["candidate_skill"] == "Docker"
    assert rel["required_skill"] == "Kubernetes"
    assert rel["is_equivalent"] is False


def test_fastapi_and_rest_apis_related_not_equivalent():
    """FastAPI and REST APIs are related (framework to concept), not equivalent."""
    candidate = ["FastAPI"]
    required = ["REST APIs"]

    res = semantic_match(candidate, required)

    assert "REST APIs" in res["missing_skills"]
    assert res["present_skills"] == []
    assert len(res["related_skills"]) == 1
    assert res["related_skills"][0]["candidate_skill"] == "FastAPI"


# =====================================================================
# 5. Global Maximum-Weight Bipartite Assignment
# =====================================================================

def test_bipartite_assignment_global_optimality():
    """Maximum-weight bipartite matching assigns optimal 1-to-1 pairings."""
    # Candidate has Go and Rust; Required has Rust and Go
    candidate = ["Rust", "Go"]
    required = ["Go", "Rust"]

    res = semantic_match(candidate, required)

    assert set(res["present_skills"]) == {"Go", "Rust"}
    assert res["missing_skills"] == []
    assert res["tp"] == 2
    assert res["fn"] == 0
    assert res["match_score"] == 1.0


# =====================================================================
# 6. Uncertain Matches Handling
# =====================================================================

def test_uncertain_match_routed_to_unresolved():
    """Skills falling into the uncertain band are routed to unresolved_skills."""
    # Test with custom thresholds to test the uncertain band explicitly
    matcher = SemanticSkillMatcher(match_threshold=0.90, uncertain_threshold=0.40)
    # Golang vs Go has similarity ~0.71 contextual, falling between 0.40 and 0.90
    candidate = ["Golang"]
    required = ["Go"]

    res = matcher.match(candidate, required)

    # Under strict 0.90 threshold, it is unresolved rather than confirmed
    assert "Go" in res["missing_skills"]
    assert len(res["unresolved_skills"]) == 1
    unresolved = res["unresolved_skills"][0]
    assert unresolved["candidate_skill"] == "Golang"
    assert unresolved["target_required_skill"] == "Go"


# =====================================================================
# 7. NDCG and Ranking Verification
# =====================================================================

def test_ndcg_is_none_for_unranked_binary_matching():
    """NDCG must be None for unranked binary skill gap detection (Issue #16 convention)."""
    res = semantic_match(["Python"], ["Python", "SQL"])
    assert res["ndcg"] is None


def test_compute_ranking_ndcg_graded_relevance():
    """NDCG@k evaluates correctly when ranked candidate lists and graded judgments exist."""
    # Required query: "Go"
    # Candidate retrieval ordered by model: ["Golang", "Rust", "Python"]
    # Ground truth graded relevance: Golang=2 (alias), Rust=0 (irrelevant), Python=0 (irrelevant)
    ranked_candidates = ["Golang", "Rust", "Python"]
    relevance = {"golang": 2, "rust": 0, "python": 0}

    # Best possible order: ["Golang", ...] gives perfect NDCG 1.0
    score = compute_ranking_ndcg(ranked_candidates, relevance, k=3)
    assert score == pytest.approx(1.0, rel=1e-3)

    # Suboptimal ranking: ["Rust", "Golang", "Python"]
    suboptimal = ["Rust", "Golang", "Python"]
    suboptimal_score = compute_ranking_ndcg(suboptimal, relevance, k=3)
    assert suboptimal_score is not None
    assert 0.0 < suboptimal_score < 1.0


def test_compute_ranking_ndcg_edge_cases():
    """NDCG returns None on empty inputs or zero relevant items."""
    assert compute_ranking_ndcg([], {"a": 2}) is None
    assert compute_ranking_ndcg(["a"], {}) is None
    assert compute_ranking_ndcg(["a"], {"a": 0}) is None


# =====================================================================
# 8. Threshold Analysis and Evaluation Pipeline Tests
# =====================================================================

def test_semantic_benchmark_file_validity():
    """Verify semantic_evaluation_data.json contains 13 valid benchmark samples."""
    import json
    from pathlib import Path

    benchmark_path = Path(__file__).resolve().parents[2] / "AI" / "Semantic_Matching" / "semantic_evaluation_data.json"
    assert benchmark_path.exists(), "semantic_evaluation_data.json must exist."

    with open(benchmark_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("is_synthetic") is True
    samples = data.get("samples", [])
    assert len(samples) == 13

    # Check each sample has required keys
    for s in samples:
        assert "id" in s
        assert "category" in s
        assert "candidate_skills" in s
        assert "required_skills" in s
        assert "expected" in s


def test_threshold_sweep_structure():
    """Test threshold sweep runs and returns complete calibration data including 0.82."""
    from AI.Semantic_Matching.threshold_analysis import sweep_thresholds

    sweep = sweep_thresholds(min_tau=0.70, max_tau=0.85, step=0.05)

    assert "sweep_range" in sweep
    assert "thresholds_evaluated" in sweep
    # Grid is 0.70, 0.75, 0.80, 0.85, plus 0.82 exactly once
    assert sweep["thresholds_evaluated"] == [0.70, 0.75, 0.80, 0.82, 0.85]
    assert sweep["thresholds_evaluated"].count(0.82) == 1
    assert len(sweep["pairwise_calibration"]) == 5

    # Verify zero false positives across optimal range
    for row in sweep["pairwise_calibration"]:
        assert row["fp"] == 0
        assert row["precision"] == 1.0


def test_threshold_selection_logic():
    """Verify threshold selection selects conservative candidate from plateau."""
    from AI.Semantic_Matching.threshold_analysis import analyze_threshold_selection

    mock_pair_results = [
        {"threshold": 0.60, "fp": 0, "f1": 0.80},
        {"threshold": 0.70, "fp": 0, "f1": 0.80},
        {"threshold": 0.82, "fp": 0, "f1": 0.80},
        {"threshold": 0.90, "fp": 0, "f1": 0.50},
    ]
    mock_macro = []

    res = analyze_threshold_selection(mock_pair_results, mock_macro)
    assert res["selected_match_threshold"] == 0.82
    assert "optimal_plateau" in res
    assert 0.82 in res["optimal_plateau"]


def test_evaluation_pipeline_end_to_end(tmp_path):
    """Verify comparative evaluation pipeline executes and produces valid results."""
    from AI.Semantic_Matching.evaluate_semantic import run_evaluation

    tmp_results = tmp_path / "test_results.json"
    out = run_evaluation(results_path=tmp_results)

    assert tmp_results.exists()
    assert out["benchmark_metadata"]["benchmark_size"] == 13
    assert out["benchmark_metadata"]["is_synthetic"] is True

    comp = out["baseline_comparison"]
    assert "keyword_baseline" in comp
    assert "taxonomy_baseline" in comp
    assert "semantic_matching" in comp

    # Semantic matching achieves higher macro recall than keyword on benchmark
    assert comp["semantic_matching"]["macro_recall"] > comp["keyword_baseline"]["macro_recall"]
    # All matchers achieve 1.0 precision by rejecting non-matches
    assert comp["semantic_matching"]["macro_precision"] == 1.0

    # Verify sample_macro_sweep and thresholds_evaluated are serialized
    assert "sample_macro_sweep" in out["threshold_sweep_summary"]
    assert len(out["threshold_sweep_summary"]["sample_macro_sweep"]) > 0
    assert "thresholds_evaluated" in out["threshold_sweep_summary"]
    assert 0.82 in out["threshold_sweep_summary"]["thresholds_evaluated"]
    assert out["threshold_sweep_summary"]["thresholds_evaluated"].count(0.82) == 1

    # Verify provisional thresholds align with selection
    assert out["provisional_thresholds"]["match_threshold"] == 0.82
    assert "0.82" in out["provisional_thresholds"]["selection_rationale"]
