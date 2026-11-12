"""Feature Engineering for Career Readiness Prediction (M4.4).

Extracts a small, interpretable, deterministic numeric feature matrix X
directly from raw candidate profile evidence.

Strict Methodological Safeguards:
- Zero dependency on human annotation sub-ratings (Cols 9-12).
- Zero dependency on M3 skill coverage scores or gold compatibility labels.
- Zero dependency on candidate identifiers or PII.
- No high-dimensional or non-deterministic embeddings.
- Scikit-learn Pipeline compatible transformer.
"""

from __future__ import annotations

import re
from typing import Any

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin

FEATURE_NAMES = [
    "skills_count",
    "exp_positions_count",
    "has_senior_role",
    "project_count",
    "project_words",
    "project_tech_count",
    "has_production_system",
    "edu_level_ordinal",
    "is_stem_degree",
]


def get_feature_names() -> list[str]:
    """Return the canonical list of engineered feature names."""
    return list(FEATURE_NAMES)


class ReadinessFeatureExtractor(BaseEstimator, TransformerMixin):
    """Deterministic feature extractor from candidate evidence dictionaries."""

    def __init__(self) -> None:
        self.feature_names_ = get_feature_names()

    def fit(self, X: list[dict[str, str]], y: Any = None) -> ReadinessFeatureExtractor:
        """Fit transformer (stateless, conforms to scikit-learn API)."""
        return self

    def transform(self, X: list[dict[str, str]]) -> np.ndarray:
        """Transform raw evidence records into 2D float64 feature matrix."""
        rows: list[list[float]] = []

        for record in X:
            skills_str = record.get("skills_text", "")
            exp_str = record.get("experience_text", "")
            proj_str = record.get("projects_text", "")
            edu_str = record.get("education_text", "")

            # 1. Technical Skills Count
            if skills_str:
                items = [
                    s.strip()
                    for s in skills_str.split(",")
                    if s.strip() and s.strip().lower() != "not provided"
                ]
                skills_count = float(len(items))
            else:
                skills_count = 0.0

            # 2 & 3. Work Experience Positions & Seniority
            if exp_str:
                exp_lines = [
                    l.strip()
                    for l in exp_str.split("\n")
                    if l.strip() and "not provided" not in l.strip().lower()[:20]
                ]
                exp_count = float(len(exp_lines))
                exp_lower = exp_str.lower()
                has_senior = 1.0 if any(
                    k in exp_lower
                    for k in ["senior", "lead", "architect", "manager", "principal", "sr."]
                ) else 0.0
            else:
                exp_count = 0.0
                has_senior = 0.0

            # 4, 5, 6, 7. Technical Projects Depth & Production Evidence
            if proj_str:
                proj_lines = [
                    l.strip()
                    for l in proj_str.split("\n")
                    if l.strip()
                    and l.strip().lower() not in ["• project", "project"]
                    and "not provided: not provided" not in l.strip().lower()
                ]
                proj_count = float(len(proj_lines))
                proj_words = float(sum(len(re.findall(r"\w+", l)) for l in proj_lines))
                tech_matches = re.findall(r"\(Tech:\s*([^)]+)\)", proj_str, re.IGNORECASE)
                tech_count = float(sum(
                    len([t.strip() for t in m.split(",") if t.strip()])
                    for m in tech_matches
                ))
                proj_lower = proj_str.lower()
                has_production = 1.0 if any(
                    k in proj_lower
                    for k in [
                        "enterprise",
                        "banking",
                        "billing",
                        "deployed",
                        "production",
                        "epks",
                        "monitoring",
                        "inventory",
                        "multi-tier",
                    ]
                ) else 0.0
            else:
                proj_count = 0.0
                proj_words = 0.0
                tech_count = 0.0
                has_production = 0.0

            # 8 & 9. Education Level & STEM Degree
            if edu_str:
                edu_lower = edu_str.lower()
                if any(
                    k in edu_lower
                    for k in ["me ", "m.e", "m.tech", "master", "mca", "pgp", "post graduate"]
                ):
                    edu_level = 2.0
                elif any(
                    k in edu_lower
                    for k in ["be ", "b.e", "b.tech", "bachelor", "bca", "b.sc", "bsc"]
                ):
                    edu_level = 1.0
                else:
                    edu_level = 0.0

                is_stem = 1.0 if any(
                    k in edu_lower
                    for k in [
                        "computer",
                        "information technology",
                        "software",
                        "electronics",
                        "telecommunication",
                        "data science",
                        "technology",
                        "engineering",
                    ]
                ) else 0.0
            else:
                edu_level = 0.0
                is_stem = 0.0

            feature_vector = [
                skills_count,
                exp_count,
                has_senior,
                proj_count,
                proj_words,
                tech_count,
                has_production,
                edu_level,
                is_stem,
            ]
            rows.append(feature_vector)

        return np.array(rows, dtype=np.float64)

    def get_feature_names_out(self, input_features: Any = None) -> list[str]:
        """Return feature names for scikit-learn compliance."""
        return list(self.feature_names_)
