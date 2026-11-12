"""Semantic Skill Matching Module for Road2Hire (Issue #17).

Provides Sentence Transformer embedding-based skill matching, unknown skill
preservation, maximum-weight bipartite assignment, and evidence-based matching.
"""

from AI.Semantic_Matching.semantic_matcher import (
    PROVISIONAL_MATCH_THRESHOLD,
    PROVISIONAL_UNCERTAIN_THRESHOLD,
    SemanticSkillMatcher,
    compute_ranking_ndcg,
    semantic_match,
)

__all__ = [
    "PROVISIONAL_MATCH_THRESHOLD",
    "PROVISIONAL_UNCERTAIN_THRESHOLD",
    "SemanticSkillMatcher",
    "compute_ranking_ndcg",
    "semantic_match",
]
