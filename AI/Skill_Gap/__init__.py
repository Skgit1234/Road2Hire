"""Road2Hire M3 Hybrid Skill Gap Detection package."""

from AI.Skill_Gap.gap_schema import (
    MatchEvidence,
    SkillGapReport,
    SkillItem,
    TargetOccupationInfo,
)
from AI.Skill_Gap.gap_scoring import (
    DEFAULT_ESSENTIAL_WEIGHT,
    DEFAULT_OPTIONAL_WEIGHT,
    compute_gap_scores,
)
from AI.Skill_Gap.skill_gap_detector import (
    SkillGapDetector,
    get_skill_gap_detector,
)

__all__ = [
    "SkillGapDetector",
    "get_skill_gap_detector",
    "SkillGapReport",
    "MatchEvidence",
    "SkillItem",
    "TargetOccupationInfo",
    "compute_gap_scores",
    "DEFAULT_ESSENTIAL_WEIGHT",
    "DEFAULT_OPTIONAL_WEIGHT",
]

