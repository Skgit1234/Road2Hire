"""Tests for Keyword and Taxonomy Skill Matching Baselines (Issue #16).

All assertions use manually precomputed, independent expected values.
Tests do not invoke the matching algorithms to calculate expected values.
"""

from __future__ import annotations

import math
import pytest

from AI.Baseline.evaluation_metrics import (
    aggregate_metrics,
    ndcg_at_k,
    precision_recall_f1,
)
from AI.Baseline.keyword_baseline import (
    keyword_match,
    keyword_match_with_metrics,
)
from AI.Baseline.taxonomy_baseline import (
    get_skill_esco_status,
    taxonomy_match,
)


# =====================================================================
# Keyword Matcher Tests
# =====================================================================

def test_keyword_match_normal_partial():
    """EVAL001: Partial match (normal case)."""
    cand = ["Python", "Pandas", "NumPy"]
    req = ["Python", "Pandas", "Scikit-learn", "Machine Learning"]

    res = keyword_match_with_metrics(cand, req)

    assert res["present_skills"] == ["Python", "Pandas"]
    assert res["missing_skills"] == ["Scikit-learn", "Machine Learning"]
    assert res["match_score"] == 0.50
    assert res["tp"] == 2
    assert res["fp"] == 0
    assert res["fn"] == 2
    assert res["precision"] == 1.0
    assert res["recall"] == 0.50
    assert res["f1"] == pytest.approx(2.0 / 3.0, rel=1e-3)
    assert res["candidate_skills_not_required"] == ["NumPy"]
    assert res["ndcg"] is None


def test_keyword_match_full():
    """EVAL002: Full match."""
    cand = ["Python", "Machine Learning", "Scikit-learn"]
    req = ["Python", "Machine Learning", "Scikit-learn"]

    res = keyword_match_with_metrics(cand, req)

    assert res["present_skills"] == ["Python", "Machine Learning", "Scikit-learn"]
    assert res["missing_skills"] == []
    assert res["match_score"] == 1.0
    assert res["tp"] == 3
    assert res["fp"] == 0
    assert res["fn"] == 0
    assert res["precision"] == 1.0
    assert res["recall"] == 1.0
    assert res["f1"] == 1.0
    assert res["candidate_skills_not_required"] == []


def test_keyword_match_cross_domain():
    """EVAL003: Cross-domain skills matched via exact string."""
    cand = ["JavaScript", "React"]
    req = ["Python", "JavaScript", "React"]

    res = keyword_match_with_metrics(cand, req)

    assert res["present_skills"] == ["JavaScript", "React"]
    assert res["missing_skills"] == ["Python"]
    assert res["match_score"] == 0.67
    assert res["tp"] == 2
    assert res["fp"] == 0
    assert res["fn"] == 1
    assert res["precision"] == 1.0
    assert res["recall"] == pytest.approx(2.0 / 3.0, rel=1e-3)
    assert res["f1"] == pytest.approx(0.80, rel=1e-3)
    assert res["candidate_skills_not_required"] == []


def test_keyword_match_aliases_not_expanded():
    """EVAL004: Keyword matcher fails to match abbreviations/synonyms."""
    cand = ["ML", "sklearn", "Python"]
    req = ["Machine Learning", "Scikit-learn", "Python"]

    res = keyword_match_with_metrics(cand, req)

    assert res["present_skills"] == ["Python"]
    assert res["missing_skills"] == ["Machine Learning", "Scikit-learn"]
    assert res["match_score"] == 0.33
    assert res["tp"] == 1
    assert res["fp"] == 0
    assert res["fn"] == 2
    assert res["precision"] == 1.0
    assert res["recall"] == pytest.approx(1.0 / 3.0, rel=1e-3)
    assert res["f1"] == pytest.approx(0.50, rel=1e-3)
    assert res["candidate_skills_not_required"] == ["ML", "sklearn"]


def test_keyword_match_unmapped_esco_skills():
    """EVAL005: Matches NumPy as string regardless of ESCO mapping."""
    cand = ["NumPy", "Python"]
    req = ["NumPy", "Pandas"]

    res = keyword_match_with_metrics(cand, req)

    assert res["present_skills"] == ["NumPy"]
    assert res["missing_skills"] == ["Pandas"]
    assert res["match_score"] == 0.50
    assert res["tp"] == 1
    assert res["fp"] == 0
    assert res["fn"] == 1
    assert res["precision"] == 1.0
    assert res["recall"] == 0.50
    assert res["f1"] == pytest.approx(2.0 / 3.0, rel=1e-3)
    assert res["candidate_skills_not_required"] == ["Python"]


def test_keyword_match_no_overlap_precision_none():
    """EVAL006: No overlap yields Precision=None (0/0) and Recall=0.0."""
    cand = ["SQL", "Git"]
    req = ["Python", "Machine Learning", "Scikit-learn"]

    res = keyword_match_with_metrics(cand, req)

    assert res["present_skills"] == []
    assert res["missing_skills"] == ["Python", "Machine Learning", "Scikit-learn"]
    assert res["match_score"] == 0.0
    assert res["tp"] == 0
    assert res["fp"] == 0
    assert res["fn"] == 3
    assert res["precision"] is None
    assert res["recall"] == 0.0
    assert res["f1"] is None
    assert res["candidate_skills_not_required"] == ["SQL", "Git"]


def test_keyword_match_empty_candidate():
    """EVAL007: Empty candidate list produces Precision=None and Recall=0.0."""
    cand = []
    req = ["Python", "Pandas"]

    res = keyword_match_with_metrics(cand, req)

    assert res["present_skills"] == []
    assert res["missing_skills"] == ["Python", "Pandas"]
    assert res["match_score"] == 0.0
    assert res["tp"] == 0
    assert res["fp"] == 0
    assert res["fn"] == 2
    assert res["precision"] is None
    assert res["recall"] == 0.0
    assert res["f1"] is None
    assert res["candidate_skills_not_required"] == []


def test_keyword_match_unrecognized_candidate_reported_separately():
    """EVAL008: Keyword matcher reports extra candidate skill in not-required."""
    cand = ["UnknownFramework", "Python"]
    req = ["Python", "Machine Learning"]

    res = keyword_match_with_metrics(cand, req)

    assert res["present_skills"] == ["Python"]
    assert res["missing_skills"] == ["Machine Learning"]
    assert res["match_score"] == 0.50
    assert res["tp"] == 1
    assert res["fp"] == 0
    assert res["fn"] == 1
    assert res["precision"] == 1.0
    assert res["recall"] == 0.50
    assert res["f1"] == pytest.approx(2.0 / 3.0, rel=1e-3)
    assert res["candidate_skills_not_required"] == ["UnknownFramework"]


def test_keyword_match_backward_compat():
    """Preserve existing keyword_match() signature and 3-field return format."""
    cand = ["Python", "Pandas"]
    req = ["Python", "Pandas", "NumPy"]

    res = keyword_match(cand, req)

    assert set(res.keys()) == {"present_skills", "missing_skills", "match_score"}
    assert res["present_skills"] == ["Python", "Pandas"]
    assert res["missing_skills"] == ["NumPy"]
    assert res["match_score"] == 0.67


# =====================================================================
# Taxonomy Matcher Tests
# =====================================================================

def test_taxonomy_match_normal_partial():
    """EVAL001: Taxonomy partial match."""
    cand = ["Python", "Pandas", "NumPy"]
    req = ["Python", "Pandas", "Scikit-learn", "Machine Learning"]

    res = taxonomy_match(cand, req)

    assert res["present_skills"] == ["Python", "Pandas"]
    assert res["missing_skills"] == ["Scikit-learn", "Machine Learning"]
    assert res["match_score"] == 0.50
    assert res["tp"] == 2
    assert res["fp"] == 0
    assert res["fn"] == 2
    assert res["precision"] == 1.0
    assert res["recall"] == 0.50
    assert res["f1"] == pytest.approx(2.0 / 3.0, rel=1e-3)
    assert res["unrecognized_candidate"] == []
    assert res["unrecognized_required"] == []
    assert res["candidate_skills_not_required"] == ["NumPy"]
    assert res["ndcg"] is None


def test_taxonomy_match_full():
    """EVAL002: Taxonomy full match."""
    cand = ["Python", "Machine Learning", "Scikit-learn"]
    req = ["Python", "Machine Learning", "Scikit-learn"]

    res = taxonomy_match(cand, req)

    assert res["present_skills"] == ["Python", "Machine Learning", "Scikit-learn"]
    assert res["missing_skills"] == []
    assert res["match_score"] == 1.0
    assert res["tp"] == 3
    assert res["fp"] == 0
    assert res["fn"] == 0
    assert res["precision"] == 1.0
    assert res["recall"] == 1.0
    assert res["f1"] == 1.0
    assert res["unrecognized_candidate"] == []
    assert res["unrecognized_required"] == []
    assert res["candidate_skills_not_required"] == []


def test_taxonomy_match_unrecognized_vocab_gap():
    """EVAL003: JavaScript and React unrecognized by current taxonomy vocabulary."""
    cand = ["JavaScript", "React"]
    req = ["Python", "JavaScript", "React"]

    res = taxonomy_match(cand, req)

    assert res["present_skills"] == []
    assert res["missing_skills"] == ["Python"]
    assert res["unrecognized_candidate"] == ["JavaScript", "React"]
    assert res["unrecognized_required"] == ["JavaScript", "React"]
    assert res["match_score"] == 0.0
    assert res["tp"] == 0
    assert res["fp"] == 0
    assert res["fn"] == 1
    assert res["precision"] is None
    assert res["recall"] == 0.0
    assert res["f1"] is None
    assert res["candidate_skills_not_required"] == []


def test_taxonomy_match_aliases_expanded():
    """EVAL004: ML -> Machine Learning and sklearn -> Scikit-learn expanded."""
    cand = ["ML", "sklearn", "Python"]
    req = ["Machine Learning", "Scikit-learn", "Python"]

    res = taxonomy_match(cand, req)

    assert res["present_skills"] == ["Machine Learning", "Scikit-learn", "Python"]
    assert res["missing_skills"] == []
    assert res["match_score"] == 1.0
    assert res["tp"] == 3
    assert res["fp"] == 0
    assert res["fn"] == 0
    assert res["precision"] == 1.0
    assert res["recall"] == 1.0
    assert res["f1"] == 1.0
    assert res["unrecognized_candidate"] == []
    assert res["unrecognized_required"] == []
    assert res["candidate_skills_not_required"] == []


def test_taxonomy_match_unmapped_esco_still_matches():
    """EVAL005: ESCO-unmapped skills still match at canonical level and are annotated."""
    cand = ["NumPy", "Python"]
    req = ["NumPy", "Pandas"]

    res = taxonomy_match(cand, req)

    assert res["present_skills"] == ["NumPy"]
    assert res["missing_skills"] == ["Pandas"]
    assert res["match_score"] == 0.50
    assert res["tp"] == 1
    assert res["fp"] == 0
    assert res["fn"] == 1
    assert res["precision"] == 1.0
    assert res["recall"] == 0.50
    assert res["f1"] == pytest.approx(2.0 / 3.0, rel=1e-3)
    assert res["unrecognized_candidate"] == []
    assert res["unrecognized_required"] == []
    assert res["candidate_skills_not_required"] == ["Python"]
    assert res["esco_status"]["NumPy"] == "unmapped"
    assert res["esco_status"]["Pandas"] == "unmapped"


def test_taxonomy_match_no_overlap_precision_none():
    """EVAL006: No canonical overlap gives Precision=None."""
    cand = ["SQL", "Git"]
    req = ["Python", "Machine Learning", "Scikit-learn"]

    res = taxonomy_match(cand, req)

    assert res["present_skills"] == []
    assert res["missing_skills"] == ["Python", "Machine Learning", "Scikit-learn"]
    assert res["match_score"] == 0.0
    assert res["tp"] == 0
    assert res["fp"] == 0
    assert res["fn"] == 3
    assert res["precision"] is None
    assert res["recall"] == 0.0
    assert res["f1"] is None
    assert res["unrecognized_candidate"] == []
    assert res["unrecognized_required"] == []
    assert res["candidate_skills_not_required"] == ["SQL", "Git"]


def test_taxonomy_match_empty_candidate():
    """EVAL007: Empty candidate yields Precision=None and Recall=0.0."""
    cand = []
    req = ["Python", "Pandas"]

    res = taxonomy_match(cand, req)

    assert res["present_skills"] == []
    assert res["missing_skills"] == ["Python", "Pandas"]
    assert res["match_score"] == 0.0
    assert res["tp"] == 0
    assert res["fp"] == 0
    assert res["fn"] == 2
    assert res["precision"] is None
    assert res["recall"] == 0.0
    assert res["f1"] is None
    assert res["unrecognized_candidate"] == []
    assert res["unrecognized_required"] == []
    assert res["candidate_skills_not_required"] == []


def test_taxonomy_match_unrecognized_excluded_not_forced():
    """EVAL008: UnknownFramework excluded from matching, not forced into mapping."""
    cand = ["UnknownFramework", "Python"]
    req = ["Python", "Machine Learning"]

    res = taxonomy_match(cand, req)

    assert res["present_skills"] == ["Python"]
    assert res["missing_skills"] == ["Machine Learning"]
    assert res["match_score"] == 0.50
    assert res["tp"] == 1
    assert res["fp"] == 0
    assert res["fn"] == 1
    assert res["precision"] == 1.0
    assert res["recall"] == 0.50
    assert res["f1"] == pytest.approx(2.0 / 3.0, rel=1e-3)
    assert res["unrecognized_candidate"] == ["UnknownFramework"]
    assert res["unrecognized_required"] == []
    assert res["candidate_skills_not_required"] == []


# =====================================================================
# Evaluation Metrics Unit Tests
# =====================================================================

def test_metrics_precision_recall_f1_normal():
    """Test normal P/R/F1 computation."""
    res = precision_recall_f1(tp=2, fp=0, fn=2)
    assert res["precision"] == 1.0
    assert res["recall"] == 0.50
    assert res["f1"] == pytest.approx(2.0 / 3.0, rel=1e-3)


def test_metrics_precision_none_when_tp_zero():
    """Undefined precision when TP=0 and FP=0 (0/0)."""
    res = precision_recall_f1(tp=0, fp=0, fn=3)
    assert res["precision"] is None
    assert res["recall"] == 0.0
    assert res["f1"] is None


def test_metrics_recall_zero_when_all_missing():
    """Recall is 0.0 when TP=0 and FN > 0."""
    res = precision_recall_f1(tp=0, fp=0, fn=5)
    assert res["recall"] == 0.0


def test_metrics_both_none_when_no_required():
    """All metrics None when no required skills exist (0/0)."""
    res = precision_recall_f1(tp=0, fp=0, fn=0)
    assert res["precision"] is None
    assert res["recall"] is None
    assert res["f1"] is None


def test_metrics_aggregate_excludes_none_precision():
    """Samples with undefined precision are excluded from macro_precision."""
    samples = [
        {"precision": 1.0, "recall": 0.50, "f1": 2.0 / 3.0},
        {"precision": None, "recall": 0.0, "f1": None},
    ]
    agg = aggregate_metrics(samples)
    assert agg["macro_precision"] == 1.0
    assert agg["macro_recall"] == 0.25
    assert agg["macro_f1"] == pytest.approx(2.0 / 3.0, rel=1e-3)


def test_metrics_aggregate_none_count_reported():
    """Undefined sample counts are explicitly reported in aggregate results."""
    samples = [
        {"precision": 1.0, "recall": 0.50, "f1": 2.0 / 3.0},
        {"precision": None, "recall": 0.0, "f1": None},
    ]
    agg = aggregate_metrics(samples)
    assert agg["precision_undefined_count"] == 1
    assert agg["f1_undefined_count"] == 1
    assert agg["sample_count"] == 2


def test_metrics_aggregate_all_none_precision():
    """When all samples have undefined precision, macro_precision is None."""
    samples = [
        {"precision": None, "recall": 0.0, "f1": None},
        {"precision": None, "recall": 0.0, "f1": None},
    ]
    agg = aggregate_metrics(samples)
    assert agg["macro_precision"] is None
    assert agg["macro_recall"] == 0.0
    assert agg["macro_f1"] is None
    assert agg["precision_undefined_count"] == 2
    assert agg["f1_undefined_count"] == 2


# =====================================================================
# NDCG Tests
# =====================================================================

def test_ndcg_at_k_perfect_ranking():
    """NDCG@k is 1.0 when relevant items are ranked at the top."""
    ranked = ["Python", "SQL", "Pandas"]
    relevant = {"Python", "SQL"}
    score = ndcg_at_k(ranked, relevant, k=2)
    assert score == pytest.approx(1.0)


def test_ndcg_at_k_imperfect_ranking():
    """NDCG@k is between 0 and 1 for sub-optimal item rankings."""
    ranked = ["Git", "Python"]
    relevant = {"Python"}
    score = ndcg_at_k(ranked, relevant, k=2)
    # ideal DCG: Python at rank 1 -> 1 / log2(2) = 1.0
    # actual DCG: Git at rank 1 (0), Python at rank 2 -> 1 / log2(3) ≈ 0.6309
    assert score is not None
    assert 0.0 < score < 1.0
    assert score == pytest.approx(1.0 / math.log2(3), rel=1e-3)


def test_ndcg_returns_none_for_empty_ranked_list():
    """NDCG@k returns None when ranked list is empty or k=0."""
    assert ndcg_at_k([], {"Python"}, k=3) is None
    assert ndcg_at_k(["Python"], {"Python"}, k=0) is None
