"""Hybrid Skill Gap Detection Engine for Road2Hire (M3).

Compares a candidate's profile skills against the requirements of a selected
ESCO target occupation using a three-tier matching pipeline:
1. Exact and normalized ESCO concept matching.
2. ESCO knowledge graph semantic relations (related, narrower, broader).
3. Sentence Transformer semantic embedding matching (384-d) with Hungarian
   bipartite assignment and hard-negative guardrails.

Enforces strict one-to-one matching and produces explainable, non-probabilistic
gap reports with clear audit trails.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from scipy.optimize import linear_sum_assignment

from AI.Candidate_Profile.profile_schema import CandidateProfile
from AI.Knowledge_Graph.esco_graph import ESCOKnowledgeGraph, get_esco_graph
from AI.Semantic_Matching.semantic_matcher import (
    KNOWN_DISTINCT_PAIRS,
    KNOWN_RELATED_PAIRS,
    PROVISIONAL_MATCH_THRESHOLD,
    PROVISIONAL_UNCERTAIN_THRESHOLD,
    SemanticSkillMatcher,
)
from AI.Skill_Extraction.esco_taxonomy import ESCOTaxonomy, get_esco_taxonomy
from AI.Skill_Extraction.skill_embeddings import (
    cosine_similarity,
    generate_skill_embeddings,
)
from AI.Skill_Gap.gap_schema import (
    MatchEvidence,
    SkillGapReport,
    SkillItem,
    TargetOccupationInfo,
)
from AI.Skill_Gap.gap_scoring import (
    DEFAULT_ESSENTIAL_WEIGHT,
    DEFAULT_OPTIONAL_WEIGHT,
    DISCLAIMER_TEXT,
    EXACT_MATCH_CREDIT,
    GRAPH_BROADER_CREDIT,
    GRAPH_NARROWER_CREDIT,
    GRAPH_RELATED_CREDIT,
    SEMANTIC_CONFIRMED_CREDIT,
    SEMANTIC_PARTIAL_SCALE,
    compute_gap_scores,
)

logger = logging.getLogger(__name__)


class SkillGapDetector:
    """Hybrid skill gap detector comparing candidate skills against ESCO occupations.

    Parameters
    ----------
    graph:
        Optional pre-loaded ESCOKnowledgeGraph instance (reuses cached singleton by default).
    taxonomy:
        Optional pre-loaded ESCOTaxonomy instance.
    matcher:
        Optional pre-loaded SemanticSkillMatcher instance.
    essential_weight:
        Weight for essential skills in overall score (default 0.75).
    optional_weight:
        Weight for optional skills in overall score (default 0.25).
    match_threshold:
        Threshold for confirmed semantic match (default 0.82).
    uncertain_threshold:
        Threshold for partial semantic match (default 0.65).
    """

    def __init__(
        self,
        graph: ESCOKnowledgeGraph | None = None,
        taxonomy: ESCOTaxonomy | None = None,
        matcher: SemanticSkillMatcher | None = None,
        essential_weight: float = DEFAULT_ESSENTIAL_WEIGHT,
        optional_weight: float = DEFAULT_OPTIONAL_WEIGHT,
        match_threshold: float = PROVISIONAL_MATCH_THRESHOLD,
        uncertain_threshold: float = PROVISIONAL_UNCERTAIN_THRESHOLD,
    ) -> None:
        if essential_weight < 0 or optional_weight < 0:
            raise ValueError("Scoring weights must be non-negative.")

        self.taxonomy = taxonomy if taxonomy is not None else get_esco_taxonomy()
        self.graph = graph if graph is not None else get_esco_graph(self.taxonomy)
        self.matcher = matcher if matcher is not None else SemanticSkillMatcher(
            match_threshold=match_threshold,
            uncertain_threshold=uncertain_threshold,
        )
        self.essential_weight = essential_weight
        self.optional_weight = optional_weight
        self.match_threshold = match_threshold
        self.uncertain_threshold = uncertain_threshold

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def detect_gap(
        self,
        candidate: CandidateProfile | dict[str, Any] | list[Any],
        target_occupation: str,
    ) -> SkillGapReport:
        """Detect skill gaps between a candidate and a target occupation.

        Parameters
        ----------
        candidate:
            CandidateProfile dict, or dictionary with a 'skills' key, or a raw
            list of skill strings/dictionaries.
        target_occupation:
            ESCO occupation concept URI, preferred label, or alternative label.

        Returns
        -------
        SkillGapReport
            Structured report conforming to the M3 schema.

        Raises
        ------
        ValueError
            If target_occupation cannot be resolved in ESCO.
        """
        # 1. Resolve Target Occupation
        occ_info, target_skills = self._resolve_target_occupation(target_occupation)

        # 2. Extract and Normalize Candidate Skills
        candidate_skills, unmapped_skills = self._extract_candidate_skills(candidate)

        # 3. Handle Empty Candidate Profile Edge Case
        if not candidate_skills:
            return self._handle_empty_candidate(
                occ_info=occ_info,
                target_skills=target_skills,
                unmapped_skills=unmapped_skills,
            )

        # 4. Partition Target Skills into Essential and Optional
        essential_targets = [s for s in target_skills if s["relation_type"] == "essential"]
        optional_targets = [s for s in target_skills if s["relation_type"] == "optional"]

        # 5. Execute 3-Tier Strict One-to-One Matching
        matched_evidence, partial_evidence, missing_targets, surplus_candidates = (
            self._execute_hybrid_matching(candidate_skills, target_skills)
        )

        # 6. Partition Missing Skills
        missing_essential: list[SkillItem] = [
            s for s in missing_targets if s["relation_type"] == "essential"
        ]
        missing_optional: list[SkillItem] = [
            s for s in missing_targets if s["relation_type"] == "optional"
        ]

        # 7. Collect Credits and Compute Scores
        essential_credits = [
            e["credit_assigned"]
            for e in matched_evidence + partial_evidence
            if e.get("target_skill_type") == "essential"
        ]
        optional_credits = [
            e["credit_assigned"]
            for e in matched_evidence + partial_evidence
            if e.get("target_skill_type") == "optional"
        ]

        scores = compute_gap_scores(
            essential_credits=essential_credits,
            total_essential_count=len(essential_targets),
            optional_credits=optional_credits,
            total_optional_count=len(optional_targets),
            essential_weight=self.essential_weight,
            optional_weight=self.optional_weight,
        )

        # 8. Assemble Structured Report
        matching_summary = {
            "total_candidate_skills": len(candidate_skills),
            "matched_skills_count": len(matched_evidence),
            "partially_matched_skills_count": len(partial_evidence),
            "missing_essential_skills_count": len(missing_essential),
            "missing_optional_skills_count": len(missing_optional),
            "unmapped_candidate_skills_count": len(unmapped_skills),
            "surplus_candidate_skills_count": len(surplus_candidates),
        }

        return {
            "target_occupation": occ_info,
            "overall_skill_coverage_score": scores["overall_skill_coverage_score"],
            "essential_skill_coverage_score": scores["essential_skill_coverage_score"],
            "optional_skill_coverage_score": scores["optional_skill_coverage_score"],
            "scoring_weights": scores["scoring_weights"],
            "matched_skills": matched_evidence,
            "partially_matched_skills": partial_evidence,
            "missing_essential_skills": missing_essential,
            "missing_optional_skills": missing_optional,
            "unmapped_candidate_skills": unmapped_skills,
            "surplus_candidate_skills": surplus_candidates,
            "matching_summary": matching_summary,
            "disclaimer": DISCLAIMER_TEXT,
        }

    # ------------------------------------------------------------------
    # Step Helpers
    # ------------------------------------------------------------------

    def _resolve_target_occupation(
        self,
        target_occupation: str,
    ) -> tuple[TargetOccupationInfo, list[SkillItem]]:
        """Resolve occupation URI and fetch its essential and optional skills."""
        if not isinstance(target_occupation, str) or not target_occupation.strip():
            raise ValueError("Target occupation must be a non-empty string.")

        occ_uri = self.graph.resolve_occupation_uri(target_occupation.strip())
        if not occ_uri or occ_uri not in self.graph.graph:
            raise ValueError(
                f"Target occupation '{target_occupation}' could not be resolved in the ESCO taxonomy."
            )

        occ_node = self.graph.get_occupation_node(occ_uri)
        pref_label = occ_node.get("label", "") if occ_node else target_occupation
        description = occ_node.get("description") if occ_node else None

        raw_skills = self.graph.get_occupation_skills(occ_uri)

        # Format skills as SkillItem
        target_skills: list[SkillItem] = []
        for s in raw_skills:
            target_skills.append({
                "skill_uri": s["skill_uri"],
                "skill_label": s["skill_label"],
                "relation_type": s["relation_type"],
                "skill_type": s.get("skill_type", "skill/competence"),
            })

        essential_count = sum(1 for s in target_skills if s["relation_type"] == "essential")
        optional_count = sum(1 for s in target_skills if s["relation_type"] == "optional")

        occ_info: TargetOccupationInfo = {
            "uri": occ_uri,
            "preferred_label": pref_label,
            "description": description,
            "essential_skills_count": essential_count,
            "optional_skills_count": optional_count,
            "total_skills_count": len(target_skills),
        }

        return occ_info, target_skills

    def _extract_candidate_skills(
        self,
        candidate: CandidateProfile | dict[str, Any] | list[Any],
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Extract standardized candidate skill dictionaries and list unmapped skills."""
        raw_items: list[Any] = []
        if isinstance(candidate, dict):
            raw_items = candidate.get("skills", [])
        elif isinstance(candidate, list):
            raw_items = candidate
        else:
            raise TypeError("Candidate must be a CandidateProfile dictionary or list of skills.")

        standardized: list[dict[str, Any]] = []
        unmapped: list[str] = []
        seen_names: set[str] = set()

        for item in raw_items:
            name: str = ""
            uri: str | None = None
            embedding: list[float] | None = None

            if isinstance(item, dict):
                name = (item.get("ESCO_Skill_Name") or item.get("skill") or "").strip()
                uri = item.get("ESCO_Skill_Id") or None
                if not uri and name:
                    uri = self.graph.resolve_skill_uri(name)
                embedding = item.get("embedding")
            elif isinstance(item, str):
                name = item.strip()
                if name:
                    uri = self.graph.resolve_skill_uri(name)

            if not name:
                continue

            name_norm = name.casefold()
            if name_norm in seen_names:
                continue
            seen_names.add(name_norm)

            if not uri:
                unmapped.append(name)

            standardized.append({
                "name": name,
                "uri": uri,
                "embedding": embedding,
            })

        # Ensure embeddings exist for all candidate skills
        missing_embed_indices = [
            idx for idx, s in enumerate(standardized) if not s.get("embedding")
        ]
        if missing_embed_indices:
            names_to_embed = [standardized[idx]["name"] for idx in missing_embed_indices]
            embed_res = generate_skill_embeddings(names_to_embed)
            embed_lookup = {
                e["skill"].casefold(): e["embedding"] for e in embed_res.get("skills", [])
            }
            for idx in missing_embed_indices:
                cand_name = standardized[idx]["name"]
                standardized[idx]["embedding"] = embed_lookup.get(cand_name.casefold())

        return standardized, unmapped

    def _handle_empty_candidate(
        self,
        occ_info: TargetOccupationInfo,
        target_skills: list[SkillItem],
        unmapped_skills: list[str],
    ) -> SkillGapReport:
        """Construct a 0% coverage report for an empty candidate profile."""
        missing_essential = [s for s in target_skills if s["relation_type"] == "essential"]
        missing_optional = [s for s in target_skills if s["relation_type"] == "optional"]

        scores = compute_gap_scores(
            essential_credits=[],
            total_essential_count=len(missing_essential),
            optional_credits=[],
            total_optional_count=len(missing_optional),
            essential_weight=self.essential_weight,
            optional_weight=self.optional_weight,
        )

        return {
            "target_occupation": occ_info,
            "overall_skill_coverage_score": 0.0,
            "essential_skill_coverage_score": 0.0,
            "optional_skill_coverage_score": 0.0 if missing_optional else None,
            "scoring_weights": scores["scoring_weights"],
            "matched_skills": [],
            "partially_matched_skills": [],
            "missing_essential_skills": missing_essential,
            "missing_optional_skills": missing_optional,
            "unmapped_candidate_skills": unmapped_skills,
            "surplus_candidate_skills": [],
            "matching_summary": {
                "total_candidate_skills": 0,
                "matched_skills_count": 0,
                "partially_matched_skills_count": 0,
                "missing_essential_skills_count": len(missing_essential),
                "missing_optional_skills_count": len(missing_optional),
                "unmapped_candidate_skills_count": len(unmapped_skills),
                "surplus_candidate_skills_count": 0,
            },
            "disclaimer": DISCLAIMER_TEXT,
        }

    # ------------------------------------------------------------------
    # Three-Tier Matching Implementation
    # ------------------------------------------------------------------

    def _execute_hybrid_matching(
        self,
        candidate_skills: list[dict[str, Any]],
        target_skills: list[SkillItem],
    ) -> tuple[list[MatchEvidence], list[MatchEvidence], list[SkillItem], list[str]]:
        """Run the 3-tier matching pipeline with strict 1-to-1 assignment."""
        available_cand_indices = set(range(len(candidate_skills)))
        unmatched_target_uris = {s["skill_uri"]: s for s in target_skills}

        matched_evidence: list[MatchEvidence] = []
        partial_evidence: list[MatchEvidence] = []

        # ==============================================================
        # Tier 1: Exact Match (URI or Normalized Label)
        # ==============================================================
        for c_idx in sorted(available_cand_indices):
            c_skill = candidate_skills[c_idx]
            c_uri = c_skill.get("uri")
            c_name = c_skill["name"].strip().casefold()

            target_match: SkillItem | None = None

            # Case A: URI exact match
            if c_uri and c_uri in unmatched_target_uris:
                target_match = unmatched_target_uris[c_uri]
            else:
                # Case B: Label exact match
                for t_uri, t_item in unmatched_target_uris.items():
                    if t_item["skill_label"].strip().casefold() == c_name:
                        target_match = t_item
                        break

            if target_match:
                t_uri = target_match["skill_uri"]
                matched_evidence.append({
                    "tier": "exact",
                    "candidate_skill": c_skill["name"],
                    "candidate_uri": c_uri,
                    "target_skill": target_match["skill_label"],
                    "target_uri": t_uri,
                    "target_skill_type": target_match["relation_type"],
                    "graph_relationship": "exact_concept_match",
                    "similarity_score": 1.0,
                    "credit_assigned": EXACT_MATCH_CREDIT,
                    "explanation": f"Exact match with required {target_match['relation_type']} skill '{target_match['skill_label']}'.",
                })
                available_cand_indices.remove(c_idx)
                unmatched_target_uris.pop(t_uri, None)

        # ==============================================================
        # Tier 2: ESCO Knowledge Graph Relationships
        # ==============================================================
        # Find all possible graph relations between available candidate skills
        # and unmatched target skills, then greedily assign disjoint pairs
        # by descending credit (narrower > related > broader) for strict 1-to-1 matching.
        graph_candidates: list[tuple[float, int, str, SkillItem, str]] = []

        for c_idx in sorted(available_cand_indices):
            c_skill = candidate_skills[c_idx]
            c_uri = c_skill.get("uri")
            if not c_uri or c_uri not in self.graph.graph:
                continue

            for t_uri, t_item in unmatched_target_uris.items():
                if t_uri not in self.graph.graph:
                    continue

                best_rel: str | None = None
                best_credit = 0.0

                # Check edge from candidate to target:
                # c_uri -> t_uri with broader_skill: t_uri is broader => candidate skill is narrower
                # c_uri -> t_uri with narrower_skill: t_uri is narrower => candidate skill is broader
                if self.graph.graph.has_edge(c_uri, t_uri):
                    edge_data = self.graph.graph.edges[c_uri, t_uri]
                    rel_names = set(edge_data.get("relation_names", []))
                    if "relation" in edge_data:
                        rel_names.add(edge_data["relation"])

                    if "broader_skill" in rel_names and GRAPH_NARROWER_CREDIT > best_credit:
                        best_rel = "is_narrower_than"
                        best_credit = GRAPH_NARROWER_CREDIT
                    if ("related" in rel_names or "related_skill" in rel_names) and GRAPH_RELATED_CREDIT > best_credit:
                        best_rel = "is_related_to"
                        best_credit = GRAPH_RELATED_CREDIT
                    if "narrower_skill" in rel_names and GRAPH_BROADER_CREDIT > best_credit:
                        best_rel = "is_broader_than"
                        best_credit = GRAPH_BROADER_CREDIT

                # Check reverse edge from target to candidate:
                # t_uri -> c_uri with narrower_skill: c_uri is narrower than t_uri
                # t_uri -> c_uri with broader_skill: c_uri is broader than t_uri
                if self.graph.graph.has_edge(t_uri, c_uri):
                    edge_data = self.graph.graph.edges[t_uri, c_uri]
                    rel_names = set(edge_data.get("relation_names", []))
                    if "relation" in edge_data:
                        rel_names.add(edge_data["relation"])

                    if "narrower_skill" in rel_names and GRAPH_NARROWER_CREDIT > best_credit:
                        best_rel = "is_narrower_than"
                        best_credit = GRAPH_NARROWER_CREDIT
                    if ("related" in rel_names or "related_skill" in rel_names) and GRAPH_RELATED_CREDIT > best_credit:
                        best_rel = "is_related_to"
                        best_credit = GRAPH_RELATED_CREDIT
                    if "broader_skill" in rel_names and GRAPH_BROADER_CREDIT > best_credit:
                        best_rel = "is_broader_than"
                        best_credit = GRAPH_BROADER_CREDIT

                if best_rel is not None and best_credit > 0.0:
                    graph_candidates.append((best_credit, c_idx, t_uri, t_item, best_rel))

        # Sort all potential graph pairs by credit descending
        graph_candidates.sort(key=lambda x: x[0], reverse=True)

        for credit, c_idx, t_uri, t_item, rel_name in graph_candidates:
            if c_idx in available_cand_indices and t_uri in unmatched_target_uris:
                c_skill = candidate_skills[c_idx]
                partial_evidence.append({
                    "tier": "graph",
                    "candidate_skill": c_skill["name"],
                    "candidate_uri": c_skill.get("uri"),
                    "target_skill": t_item["skill_label"],
                    "target_uri": t_uri,
                    "target_skill_type": t_item["relation_type"],
                    "graph_relationship": rel_name,
                    "similarity_score": credit,
                    "credit_assigned": credit,
                    "explanation": (
                        f"Candidate skill '{c_skill['name']}' has an ESCO taxonomy relationship "
                        f"({rel_name}) with {t_item['relation_type']} skill '{t_item['skill_label']}'."
                    ),
                })
                available_cand_indices.remove(c_idx)
                unmatched_target_uris.pop(t_uri, None)

        # ==============================================================
        # Tier 3: Semantic Similarity Matching (Hungarian 1-to-1)
        # ==============================================================
        remaining_cand_indices = sorted(available_cand_indices)
        remaining_targets = list(unmatched_target_uris.values())

        if remaining_cand_indices and remaining_targets:
            # Prepare target embeddings
            target_labels = [t["skill_label"] for t in remaining_targets]
            target_embed_res = generate_skill_embeddings(target_labels)
            target_embed_lookup = {
                item["skill"].casefold(): item["embedding"]
                for item in target_embed_res.get("skills", [])
            }

            # Build cost matrix for maximum weight bipartite matching
            num_cands = len(remaining_cand_indices)
            num_targets = len(remaining_targets)
            sim_matrix = [[0.0] * num_targets for _ in range(num_cands)]

            for i, c_idx in enumerate(remaining_cand_indices):
                c_vec = candidate_skills[c_idx].get("embedding")
                c_name = candidate_skills[c_idx]["name"]
                if not c_vec:
                    continue

                for j, t_item in enumerate(remaining_targets):
                    t_name = t_item["skill_label"]
                    t_vec = target_embed_lookup.get(t_name.casefold())
                    if not t_vec:
                        continue

                    # Hard negative check
                    pair_key = frozenset({c_name.casefold(), t_name.casefold()})
                    if pair_key in KNOWN_DISTINCT_PAIRS:
                        sim_matrix[i][j] = 0.0
                        continue

                    try:
                        sim = cosine_similarity(c_vec, t_vec)
                    except Exception:
                        sim = 0.0

                    sim_matrix[i][j] = max(0.0, sim)

            # Solve Hungarian algorithm
            cost_matrix = [[1.0 - sim_matrix[i][j] for j in range(num_targets)] for i in range(num_cands)]
            row_ind, col_ind = linear_sum_assignment(cost_matrix)

            assigned_c_indices: set[int] = set()
            assigned_t_uris: set[str] = set()

            for r, c in zip(row_ind, col_ind):
                sim = sim_matrix[r][c]
                c_idx = remaining_cand_indices[r]
                t_item = remaining_targets[c]
                t_uri = t_item["skill_uri"]
                c_skill = candidate_skills[c_idx]

                pair_key = frozenset({c_skill["name"].casefold(), t_item["skill_label"].casefold()})

                if pair_key in KNOWN_RELATED_PAIRS:
                    # Domain-related safeguard: never treat ecosystem/related pairs as confirmed matches
                    if sim >= self.uncertain_threshold:
                        credit = round(SEMANTIC_PARTIAL_SCALE * sim, 4)
                        rel_desc = KNOWN_RELATED_PAIRS[pair_key]
                        partial_evidence.append({
                            "tier": "semantic",
                            "candidate_skill": c_skill["name"],
                            "candidate_uri": c_skill.get("uri"),
                            "target_skill": t_item["skill_label"],
                            "target_uri": t_uri,
                            "target_skill_type": t_item["relation_type"],
                            "graph_relationship": "domain_related",
                            "similarity_score": round(sim, 4),
                            "credit_assigned": credit,
                            "explanation": (
                                f"Domain-related skill ({rel_desc}; {sim:.2f} similarity) with "
                                f"{t_item['relation_type']} skill '{t_item['skill_label']}'."
                            ),
                        })
                        assigned_c_indices.add(c_idx)
                        assigned_t_uris.add(t_uri)

                elif sim >= self.match_threshold:
                    # Confirmed semantic equivalence
                    matched_evidence.append({
                        "tier": "semantic",
                        "candidate_skill": c_skill["name"],
                        "candidate_uri": c_skill.get("uri"),
                        "target_skill": t_item["skill_label"],
                        "target_uri": t_uri,
                        "target_skill_type": t_item["relation_type"],
                        "graph_relationship": None,
                        "similarity_score": round(sim, 4),
                        "credit_assigned": SEMANTIC_CONFIRMED_CREDIT,
                        "explanation": (
                            f"Confirmed semantic match ({sim:.2f} cosine similarity) with "
                            f"{t_item['relation_type']} skill '{t_item['skill_label']}'."
                        ),
                    })
                    assigned_c_indices.add(c_idx)
                    assigned_t_uris.add(t_uri)

                elif sim >= self.uncertain_threshold:
                    # Partial semantic match
                    credit = round(SEMANTIC_PARTIAL_SCALE * sim, 4)
                    partial_evidence.append({
                        "tier": "semantic",
                        "candidate_skill": c_skill["name"],
                        "candidate_uri": c_skill.get("uri"),
                        "target_skill": t_item["skill_label"],
                        "target_uri": t_uri,
                        "target_skill_type": t_item["relation_type"],
                        "graph_relationship": "semantic_related",
                        "similarity_score": round(sim, 4),
                        "credit_assigned": credit,
                        "explanation": (
                            f"Partial semantic alignment ({sim:.2f} cosine similarity) with "
                            f"{t_item['relation_type']} skill '{t_item['skill_label']}'."
                        ),
                    })
                    assigned_c_indices.add(c_idx)
                    assigned_t_uris.add(t_uri)

            for c_idx in assigned_c_indices:
                available_cand_indices.discard(c_idx)
            for t_uri in assigned_t_uris:
                unmatched_target_uris.pop(t_uri, None)

        # ==============================================================
        # Unmatched Collections
        # ==============================================================
        missing_targets = list(unmatched_target_uris.values())
        surplus_candidates = [
            candidate_skills[idx]["name"] for idx in sorted(available_cand_indices)
        ]

        return matched_evidence, partial_evidence, missing_targets, surplus_candidates


# ---------------------------------------------------------------------------
# Module Singleton Helper
# ---------------------------------------------------------------------------

_detector_singleton: SkillGapDetector | None = None


def get_skill_gap_detector() -> SkillGapDetector:
    """Return a cached instance of SkillGapDetector."""
    global _detector_singleton  # noqa: PLW0603
    if _detector_singleton is None:
        _detector_singleton = SkillGapDetector()
    return _detector_singleton

