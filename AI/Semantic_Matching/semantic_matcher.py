"""Semantic Skill Matching Engine for Road2Hire (Issue #17).

Provides Sentence Transformer embedding-based skill matching to identify
conceptually similar candidate and job-required skills, even when their names
differ. Preserves unrecognized skills without requiring prior inclusion in
curated vocabularies or ESCO/O*NET mappings.

Safeguards and Design Rules:
----------------------------
1. Cosine similarity in embedding space is a geometric distance metric, NOT a
   probability of equivalence. Scores must not be treated as posterior confidence
   probabilities P(equivalent | similarity).
2. Thresholds are candidate parameters to be evaluated empirically against
   annotated ground-truth benchmarks. The defaults provided here are provisional
   benchmarking candidates.
3. Unrecognized skills (e.g., Rust, Go, FastAPI, custom tools) are preserved in
   full fidelity with their original string representation and diagnostic status.
   They are never marked invalid or automatically added to ESCO/O*NET without
   human-in-the-loop validation.
4. Distinguishes four distinct matching categories:
   - CONFIRMED_MATCH: Exact, canonical synonym, or high-confidence semantic match.
   - RELATED_SKILL: Topically or ecosystem-related skills (e.g., Docker & Kubernetes,
     PyTorch & Deep Learning) that share conceptual context but represent distinct
     capabilities. These are NEVER treated as equivalent or counted as present skills.
   - UNCERTAIN_MATCH: Ambiguous similarity in [uncertain_threshold, match_threshold).
     Preserved in unresolved_skills with matching evidence for human review.
   - NON_MATCH: Distinct skills or similarity below uncertain_threshold (e.g.,
     Rust vs Go, Java vs JavaScript, C vs C++).
5. One-to-one assignment is solved via maximum-weight bipartite matching
   (Hungarian algorithm) to find the globally optimal alignment across candidate
   and required skill sets without greedy ordering bias.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from AI.Baseline.evaluation_metrics import ndcg_at_k, precision_recall_f1
from AI.Skill_Extraction.skill_embeddings import (
    DEFAULT_MODEL_NAME,
    cosine_similarity,
    generate_skill_embeddings,
)
from AI.Skill_Extraction.skill_extractor import (
    load_skill_vocabulary,
    normalize_skill_name,
)

# Provisional candidate thresholds (to be evaluated and calibrated empirically).
# DO NOT treat these as established probabilities.
PROVISIONAL_MATCH_THRESHOLD = 0.82
PROVISIONAL_UNCERTAIN_THRESHOLD = 0.65

# Deceptive lexical or topical pairs that must NEVER be treated as equivalent
# matches regardless of raw embedding similarity.
KNOWN_DISTINCT_PAIRS: set[frozenset[str]] = {
    frozenset({"java", "javascript"}),
    frozenset({"c", "c++"}),
    frozenset({"c", "c#"}),
    frozenset({"rust", "go"}),
    frozenset({"rust", "golang"}),
    frozenset({"python", "pytorch"}),
}

# Known ecosystem / parent-child / co-occurring relations that represent related
# skills rather than interchangeable equivalents.
KNOWN_RELATED_PAIRS: dict[frozenset[str], str] = {
    frozenset({"docker", "kubernetes"}): "Containerization ecosystem (Engine vs Orchestrator)",
    frozenset({"pytorch", "deep learning"}): "Framework to domain concept",
    frozenset({"tensorflow", "deep learning"}): "Framework to domain concept",
    frozenset({"fastapi", "rest apis"}): "Specific web framework to general API protocol",
    frozenset({"react", "frontend"}): "Library to domain concept",
    frozenset({"django", "backend"}): "Framework to domain concept",
}

# Short polysemous words where contextual disambiguation helps embedding models
# separate the technical skill from common English words.
SKILL_CONTEXT_EXPANSIONS: dict[str, str] = {
    "go": "Go programming language",
    "golang": "Golang programming language",
    "rust": "Rust programming language",
    "c": "C programming language",
    "r": "R programming language for statistics",
}


@dataclass
class SkillAssignment:
    """Detailed evidence of a candidate-to-required skill pairing."""

    candidate_skill: str
    required_skill: str
    similarity_score: float
    status: str  # confirmed_match, related_skill, uncertain_match, non_match
    evidence: str
    is_candidate_recognized: bool
    is_required_recognized: bool
    candidate_canonical: str | None = None
    required_canonical: str | None = None


class SemanticSkillMatcher:
    """Sentence Transformer semantic skill matcher with bipartite assignment."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        match_threshold: float = PROVISIONAL_MATCH_THRESHOLD,
        uncertain_threshold: float = PROVISIONAL_UNCERTAIN_THRESHOLD,
        use_taxonomy: bool = True,
    ) -> None:
        """Initialize the semantic matcher.

        Parameters
        ----------
        model_name : str
            SentenceTransformer model identifier.
        match_threshold : float
            Candidate threshold for confirmed semantic equivalence.
        uncertain_threshold : float
            Candidate threshold below which pairs are considered non-matches.
        use_taxonomy : bool
            Whether to use curated taxonomy synonyms to resolve known aliases.
        """
        if match_threshold <= uncertain_threshold:
            raise ValueError(
                f"match_threshold ({match_threshold}) must be strictly greater "
                f"than uncertain_threshold ({uncertain_threshold})."
            )

        self.model_name = model_name
        self.match_threshold = match_threshold
        self.uncertain_threshold = uncertain_threshold
        self.use_taxonomy = use_taxonomy
        self._vocabulary: list[str] | None = None

    def _get_vocabulary(self) -> list[str]:
        """Lazy load curated skill vocabulary."""
        if self._vocabulary is None:
            try:
                self._vocabulary = load_skill_vocabulary()
            except Exception:
                self._vocabulary = []
        return self._vocabulary

    def _normalize_item(
        self,
        item: str | dict[str, Any],
    ) -> tuple[str, str, str | None, bool]:
        """Parse raw skill item into (name, text_for_embedding, canonical_name, is_recognized)."""
        if isinstance(item, dict):
            name = str(item.get("name", "")).strip()
            desc = str(item.get("description", "")).strip()
            context = str(item.get("context", "")).strip()
        elif isinstance(item, str):
            name = item.strip()
            desc = ""
            context = ""
        else:
            raise TypeError(f"Skill item must be str or dict, got {type(item).__name__}")

        if not name:
            return "", "", None, False

        key = name.casefold()

        # Taxonomy normalization
        canonical: str | None = None
        is_recognized = False
        if self.use_taxonomy:
            vocab = self._get_vocabulary()
            canonical = normalize_skill_name(name, vocab)
            if canonical is not None:
                is_recognized = True

        # Build representation for embedding
        parts = []
        if key in SKILL_CONTEXT_EXPANSIONS and not desc and not context:
            parts.append(SKILL_CONTEXT_EXPANSIONS[key])
        else:
            parts.append(name)

        if desc:
            parts.append(desc)
        if context:
            parts.append(f"Context: {context}")

        text_for_embedding = " - ".join(parts)
        return name, text_for_embedding, canonical, is_recognized

    def match(
        self,
        candidate_skills: list[str | dict[str, Any]],
        required_skills: list[str | dict[str, Any]],
        match_threshold: float | None = None,
        uncertain_threshold: float | None = None,
    ) -> dict[str, Any]:
        """Perform semantic skill matching between candidate and required skills.

        Parameters
        ----------
        candidate_skills : list[str | dict]
            Candidate skills as strings or dictionaries with optional descriptions.
        required_skills : list[str | dict]
            Job required skills as strings or dictionaries.
        match_threshold : float | None
            Override match threshold for this call.
        uncertain_threshold : float | None
            Override uncertain threshold for this call.

        Returns
        -------
        dict[str, Any]
            Dictionary containing present_skills, missing_skills, related_skills,
            unresolved_skills, unrecognized_skills, match_score, P/R/F1 metrics,
            and detailed assignments.
        """
        tau_match = match_threshold if match_threshold is not None else self.match_threshold
        tau_uncertain = (
            uncertain_threshold if uncertain_threshold is not None else self.uncertain_threshold
        )
        if tau_match <= tau_uncertain:
            tau_uncertain = max(0.0, tau_match - 0.15)

        if not isinstance(candidate_skills, list) or not isinstance(required_skills, list):
            raise TypeError("candidate_skills and required_skills must be lists.")

        # Clean, normalize, and deduplicate skills while preserving insertion order
        cand_parsed = []
        seen_cand = set()
        for item in candidate_skills:
            name, embed_text, canonical, recognized = self._normalize_item(item)
            if name and name.casefold() not in seen_cand:
                seen_cand.add(name.casefold())
                cand_parsed.append(
                    {
                        "original_name": name,
                        "embed_text": embed_text,
                        "canonical": canonical,
                        "is_recognized": recognized,
                    }
                )

        req_parsed = []
        seen_req = set()
        for item in required_skills:
            name, embed_text, canonical, recognized = self._normalize_item(item)
            if name and name.casefold() not in seen_req:
                seen_req.add(name.casefold())
                req_parsed.append(
                    {
                        "original_name": name,
                        "embed_text": embed_text,
                        "canonical": canonical,
                        "is_recognized": recognized,
                    }
                )

        # Track unrecognized skills (preserved, not discarded)
        unrecognized_candidate = [c["original_name"] for c in cand_parsed if not c["is_recognized"]]
        unrecognized_required = [r["original_name"] for r in req_parsed if not r["is_recognized"]]

        # Edge cases: empty sets
        if not req_parsed:
            return {
                "present_skills": [],
                "missing_skills": [],
                "related_skills": [],
                "unresolved_skills": [],
                "unrecognized_skills": {
                    "candidate": unrecognized_candidate,
                    "required": unrecognized_required,
                },
                "candidate_skills_not_required": [c["original_name"] for c in cand_parsed],
                "match_score": 0.0,
                "tp": 0,
                "fp": 0,
                "fn": 0,
                "precision": None,
                "recall": None,
                "f1": None,
                "ndcg": None,
                "assignments": [],
            }

        if not cand_parsed:
            missing = [r["original_name"] for r in req_parsed]
            metrics = precision_recall_f1(tp=0, fp=0, fn=len(missing))
            return {
                "present_skills": [],
                "missing_skills": missing,
                "related_skills": [],
                "unresolved_skills": [],
                "unrecognized_skills": {
                    "candidate": unrecognized_candidate,
                    "required": unrecognized_required,
                },
                "candidate_skills_not_required": [],
                "match_score": 0.0,
                "tp": 0,
                "fp": 0,
                "fn": len(missing),
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "f1": metrics["f1"],
                "ndcg": None,
                "assignments": [],
            }

        # Generate embeddings for candidate and required skills
        all_embed_texts = list(
            dict.fromkeys([c["embed_text"] for c in cand_parsed] + [r["embed_text"] for r in req_parsed])
        )
        embed_res = generate_skill_embeddings(all_embed_texts, model_name=self.model_name)
        embedding_map = {item["skill"]: item["embedding"] for item in embed_res.get("skills", [])}

        num_c = len(cand_parsed)
        num_r = len(req_parsed)

        # Similarity matrix: rows = candidates, cols = required
        sim_matrix = np.zeros((num_c, num_r), dtype=float)
        relation_matrix: list[list[str | None]] = [[None for _ in range(num_r)] for _ in range(num_c)]

        for i, cand in enumerate(cand_parsed):
            c_name_kf = cand["original_name"].casefold()
            c_canon_kf = cand["canonical"].casefold() if cand["canonical"] else None

            for j, req in enumerate(req_parsed):
                r_name_kf = req["original_name"].casefold()
                r_canon_kf = req["canonical"].casefold() if req["canonical"] else None
                pair_key = frozenset({c_name_kf, r_name_kf})

                # Check 1: Exact string or canonical match
                if c_name_kf == r_name_kf or (c_canon_kf and r_canon_kf and c_canon_kf == r_canon_kf):
                    sim_matrix[i, j] = 1.0
                    relation_matrix[i][j] = "canonical_exact"
                    continue

                # Check 2: Known distinct/deceptive pairs guard
                if pair_key in KNOWN_DISTINCT_PAIRS:
                    sim_matrix[i, j] = 0.0
                    relation_matrix[i][j] = "known_distinct"
                    continue

                # Check 3: Known related pairs guard (topical/ecosystem relation)
                if pair_key in KNOWN_RELATED_PAIRS:
                    c_vec = embedding_map.get(cand["embed_text"])
                    r_vec = embedding_map.get(req["embed_text"])
                    sim = cosine_similarity(c_vec, r_vec) if (c_vec and r_vec) else 0.0
                    sim_matrix[i, j] = sim
                    relation_matrix[i][j] = "known_related"
                    continue

                # Compute semantic cosine similarity
                c_vec = embedding_map.get(cand["embed_text"])
                r_vec = embedding_map.get(req["embed_text"])
                if c_vec and r_vec:
                    sim = cosine_similarity(c_vec, r_vec)
                else:
                    sim = 0.0
                sim_matrix[i, j] = sim

        # Maximum-weight bipartite matching
        # Transform similarities into costs for minimization: cost = -similarity
        # Disallow or heavily penalize known distinct pairs and known related pairs
        # from being assigned as equivalent matches.
        cost_matrix = np.full((num_c, num_r), 100.0, dtype=float)
        for i in range(num_c):
            for j in range(num_r):
                rel = relation_matrix[i][j]
                if rel == "known_distinct" or rel == "known_related":
                    cost_matrix[i, j] = 100.0  # blocked from match assignment
                elif sim_matrix[i, j] >= tau_uncertain:
                    cost_matrix[i, j] = -sim_matrix[i, j]

        assigned_pairs = self._solve_bipartite_assignment(cost_matrix)

        # Track results
        matched_required_indices = set()
        matched_candidate_indices = set()
        assignments: list[SkillAssignment] = []
        present_skills: list[str] = []
        related_skills: list[dict[str, Any]] = []
        unresolved_skills: list[dict[str, Any]] = []

        # Process assigned edges from maximum-weight bipartite matching
        for i, j in assigned_pairs:
            sim = float(sim_matrix[i, j])
            rel = relation_matrix[i][j]
            cand = cand_parsed[i]
            req = req_parsed[j]

            if rel == "canonical_exact" or sim >= tau_match:
                # Confirmed match
                matched_candidate_indices.add(i)
                matched_required_indices.add(j)
                present_skills.append(req["original_name"])
                status = "confirmed_match"
                evidence = (
                    f"Canonical/exact equality"
                    if rel == "canonical_exact"
                    else f"Semantic cosine similarity: {sim:.4f} >= match threshold {tau_match:.2f}"
                )
                assignments.append(
                    SkillAssignment(
                        candidate_skill=cand["original_name"],
                        required_skill=req["original_name"],
                        similarity_score=sim,
                        status=status,
                        evidence=evidence,
                        is_candidate_recognized=cand["is_recognized"],
                        is_required_recognized=req["is_recognized"],
                        candidate_canonical=cand["canonical"],
                        required_canonical=req["canonical"],
                    )
                )
            elif tau_uncertain <= sim < tau_match:
                # Uncertain match - captured in unresolved_skills with matching evidence
                matched_candidate_indices.add(i)
                unresolved_skills.append(
                    {
                        "candidate_skill": cand["original_name"],
                        "target_required_skill": req["original_name"],
                        "similarity_score": round(sim, 4),
                        "evidence": (
                            f"Provisional similarity {sim:.4f} in uncertain band "
                            f"[{tau_uncertain:.2f}, {tau_match:.2f}); requires review"
                        ),
                        "status": "unresolved_uncertain_match",
                    }
                )
                assignments.append(
                    SkillAssignment(
                        candidate_skill=cand["original_name"],
                        required_skill=req["original_name"],
                        similarity_score=sim,
                        status="uncertain_match",
                        evidence=f"Similarity {sim:.4f} in uncertain band [{tau_uncertain:.2f}, {tau_match:.2f})",
                        is_candidate_recognized=cand["is_recognized"],
                        is_required_recognized=req["is_recognized"],
                        candidate_canonical=cand["canonical"],
                        required_canonical=req["canonical"],
                    )
                )

        # Identify related skills across all pairs (not restricted to 1-to-1 assignments)
        for i, cand in enumerate(cand_parsed):
            for j, req in enumerate(req_parsed):
                rel = relation_matrix[i][j]
                if rel == "known_related":
                    pair_key = frozenset({cand["original_name"].casefold(), req["original_name"].casefold()})
                    relation_desc = KNOWN_RELATED_PAIRS.get(pair_key, "Domain related skill")
                    related_skills.append(
                        {
                            "candidate_skill": cand["original_name"],
                            "required_skill": req["original_name"],
                            "similarity_score": round(float(sim_matrix[i, j]), 4),
                            "relation": relation_desc,
                            "is_equivalent": False,
                        }
                    )

        # Missing skills: required skills that received no confirmed match
        missing_skills = [
            req["original_name"]
            for j, req in enumerate(req_parsed)
            if j not in matched_required_indices
        ]

        # Candidate skills not required: candidates not matched to any required skill
        candidate_skills_not_required = [
            cand["original_name"]
            for i, cand in enumerate(cand_parsed)
            if i not in matched_candidate_indices
        ]

        # Calculate metrics using canonical precision_recall_f1
        tp = len(present_skills)
        fp = 0
        fn = len(missing_skills)
        metrics = precision_recall_f1(tp=tp, fp=fp, fn=fn)

        match_score = round(tp / num_r, 4) if num_r > 0 else 0.0

        return {
            "present_skills": present_skills,
            "missing_skills": missing_skills,
            "related_skills": related_skills,
            "unresolved_skills": unresolved_skills,
            "unrecognized_skills": {
                "candidate": unrecognized_candidate,
                "required": unrecognized_required,
            },
            "candidate_skills_not_required": candidate_skills_not_required,
            "match_score": match_score,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": metrics["precision"],
            "recall": metrics["recall"],
            "f1": metrics["f1"],
            "ndcg": None,  # NDCG is None for unranked binary sets (Issue #16 convention)
            "assignments": [
                {
                    "candidate_skill": a.candidate_skill,
                    "required_skill": a.required_skill,
                    "similarity_score": round(a.similarity_score, 4),
                    "status": a.status,
                    "evidence": a.evidence,
                    "candidate_canonical": a.candidate_canonical,
                    "required_canonical": a.required_canonical,
                }
                for a in assignments
            ],
            "provisional_thresholds": {
                "match_threshold": tau_match,
                "uncertain_threshold": tau_uncertain,
                "note": "Provisional candidate thresholds for empirical evaluation; not probabilities.",
            },
        }

    def _solve_bipartite_assignment(
        self,
        cost_matrix: np.ndarray,
    ) -> list[tuple[int, int]]:
        """Solve maximum weight bipartite assignment using Hungarian algorithm."""
        num_c, num_r = cost_matrix.shape
        if num_c == 0 or num_r == 0:
            return []

        try:
            from scipy.optimize import linear_sum_assignment

            row_ind, col_ind = linear_sum_assignment(cost_matrix)
            pairs = []
            for r, c in zip(row_ind, col_ind):
                # Accept assignment only if cost indicates a valid pairing (not 100.0)
                if cost_matrix[r, c] < 0.0:
                    pairs.append((int(r), int(c)))
            return pairs
        except Exception:
            # Greedy fallback if scipy is unavailable
            pairs = []
            used_r = set()
            used_c = set()
            # Sort edges by descending similarity (ascending cost)
            edges = []
            for i in range(num_c):
                for j in range(num_r):
                    if cost_matrix[i, j] < 0.0:
                        edges.append((cost_matrix[i, j], i, j))
            edges.sort(key=lambda x: x[0])
            for _, i, j in edges:
                if i not in used_c and j not in used_r:
                    used_c.add(i)
                    used_r.add(j)
                    pairs.append((i, j))
            return pairs


def semantic_match(
    candidate_skills: list[str | dict[str, Any]],
    required_skills: list[str | dict[str, Any]],
    match_threshold: float = PROVISIONAL_MATCH_THRESHOLD,
    uncertain_threshold: float = PROVISIONAL_UNCERTAIN_THRESHOLD,
    model_name: str = DEFAULT_MODEL_NAME,
    use_taxonomy: bool = True,
) -> dict[str, Any]:
    """Public functional interface for semantic skill matching.

    Parameters
    ----------
    candidate_skills : list[str | dict]
        Skills possessed by the candidate.
    required_skills : list[str | dict]
        Skills required by the job.
    match_threshold : float
        Candidate threshold for confirmed semantic match.
    uncertain_threshold : float
        Candidate threshold for ambiguous/uncertain band.
    model_name : str
        Sentence Transformer model name.
    use_taxonomy : bool
        Whether to resolve canonical synonyms from taxonomy vocabulary.

    Returns
    -------
    dict[str, Any]
        Standard Road2Hire skill matching result dictionary.
    """
    matcher = SemanticSkillMatcher(
        model_name=model_name,
        match_threshold=match_threshold,
        uncertain_threshold=uncertain_threshold,
        use_taxonomy=use_taxonomy,
    )
    return matcher.match(candidate_skills, required_skills)


def compute_ranking_ndcg(
    ranked_skills: list[str],
    relevance_judgments: dict[str, float | int],
    k: int | None = None,
) -> float | None:
    """Compute NDCG@k for a ranked list of candidate skills against graded relevance.

    NDCG is mathematically applicable only when an ordered candidate retrieval
    list exists and ground-truth relevance labels are defined.

    Parameters
    ----------
    ranked_skills : list[str]
        Ordered candidate skill names from highest to lowest similarity.
    relevance_judgments : dict[str, float | int]
        Ground-truth relevance ratings (e.g., 2=exact/alias, 1=related, 0=non-match).
    k : int | None
        Truncation rank. If None, evaluates across the full ranked list.

    Returns
    -------
    float | None
        Normalized Discounted Cumulative Gain in [0.0, 1.0], or None if judgments
        contain zero relevant items.
    """
    if not ranked_skills or not relevance_judgments:
        return None

    cutoff = len(ranked_skills) if k is None else min(k, len(ranked_skills))
    if cutoff <= 0:
        return None

    # Compute DCG
    dcg = 0.0
    for rank_idx, skill in enumerate(ranked_skills[:cutoff], start=1):
        rel = float(relevance_judgments.get(skill.casefold(), 0.0))
        dcg += (2.0**rel - 1.0) / math.log2(rank_idx + 1.0)

    # Compute IDCG (ideal ranking)
    ideal_scores = sorted(
        [float(v) for v in relevance_judgments.values()],
        reverse=True,
    )[:cutoff]

    idcg = 0.0
    for rank_idx, rel in enumerate(ideal_scores, start=1):
        idcg += (2.0**rel - 1.0) / math.log2(rank_idx + 1.0)

    if idcg == 0.0:
        return None

    return dcg / idcg
