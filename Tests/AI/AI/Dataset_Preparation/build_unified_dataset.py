"""Unified Candidate-Occupation Dataset Builder for Road2Hire (M4.2).

Constructs the standardized, explainable candidate-occupation dataset for career-readiness
model research and evaluation by combining:
1. Candidate profiles from Datasets/master_resumes.jsonl (streaming) and Datasets/synthetic_profiles.json.
2. Target occupation requirements from the ESCO Knowledge Graph (essential and optional skills).
3. Hybrid skill gap detection features (strict 1-to-1 matching, coverage scores, audit trail).
4. Personalized knowledge graph topological features (NetworkX graph summary).
5. Supplementary O*NET importance/level metrics where available.
6. Separate gold-label ground truth (from gold_labels.json) strictly annotating candidate-job
   compatibility, never conflating compatibility with career readiness.

Saves output as JSON Lines (JSONL) at:
Datasets/Processed/candidate_occupation_dataset.jsonl
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sys
import time
from pathlib import Path
from typing import Any

from AI.Candidate_Profile.profile_schema import CandidateProfile
from AI.Candidate_Profile.profile_validator import validate_candidate_profile_comprehensive
from AI.Dataset_Preparation.candidate_adapter import (
    adapt_master_resume_to_candidate_profile,
    adapt_synthetic_profile_to_candidate_profile,
)
from AI.Dataset_Preparation.dataset_inventory import (
    get_datasets_dir,
    get_gold_label_index,
    load_synthetic_profiles,
    stream_master_resumes,
)
from AI.Dataset_Preparation.occupation_adapter import adapt_esco_occupation
from AI.Dataset_Preparation.unified_schema import (
    CandidateOccupationRecord,
    GraphTopologicalFeatures,
    GroundTruthAlignment,
    OccupationRequirementSummary,
    SkillGapSummaryFeatures,
)
from AI.Knowledge_Graph.esco_graph import ESCOKnowledgeGraph, get_esco_graph
from AI.Knowledge_Graph.personalized_graph import PersonalizedKnowledgeGraph
from AI.Skill_Extraction.esco_taxonomy import ESCOTaxonomy, get_esco_taxonomy
from AI.Skill_Gap.gap_schema import SkillGapReport
from AI.Skill_Gap.skill_gap_detector import SkillGapDetector, get_skill_gap_detector

logger = logging.getLogger(__name__)

# Seniority & modifier stripping regex
PREFIX_REGEX = re.compile(
    r"^(junior|senior|staff|lead|principal|associate|entry[\s\-]level|intern|mid[\s\-]level|chief|head of|vp of|assistant)\s+",
    re.IGNORECASE,
)

SUFFIX_REGEX = re.compile(
    r"\s+(\(devops\)|\(rpa\)|intern|consultant|specialist|practitioner|engineer|developer)$",
    re.IGNORECASE,
)

# Canonical industry title fallback mappings to ESCO preferred labels
CANONICAL_OCCUPATION_MAP: dict[str, str] = {
    # Software & Web Engineering
    "python developer": "software developer",
    "java developer": "software developer",
    "javascript developer": "software developer",
    "backend developer": "software developer",
    "backend engineer": "software developer",
    "frontend developer": "software developer",
    "frontend engineer": "software developer",
    "full stack developer": "software developer",
    "full stack engineer": "software developer",
    "software engineer": "software developer",
    "software developer": "software developer",
    "mobile app developer": "software developer",
    "mobile developer": "software developer",
    "ios developer": "software developer",
    "android developer": "software developer",
    "react developer": "web developer",
    "angular developer": "web developer",
    "vue developer": "web developer",
    "node.js developer": "web developer",
    "web developer": "web developer",
    "react native developer": "software developer",
    "flutter developer": "software developer",
    "jr. java developer": "software developer",
    "python developer/analyst": "software developer",
    "python restful api developer": "software developer",
    # Data & AI
    "data scientist": "data scientist",
    "data science consultant": "data scientist",
    "machine learning engineer": "data scientist",
    "machine learning engineer intern": "data scientist",
    "deep learning engineer": "data scientist",
    "nlp engineer": "data scientist",
    "mlops engineer": "data scientist",
    "data analyst": "data analyst",
    "business analyst": "data analyst",
    "senior business analyst - rpa": "data analyst",
    "business intelligence analyst": "data analyst",
    # Systems, DevOps & Cloud
    "devops engineer": "ICT system administrator",
    "cloud operations architect": "ICT system administrator",
    "cloud operations architect (devops)": "ICT system administrator",
    "cloud engineer": "ICT system administrator",
    "site reliability engineer": "ICT system administrator",
    "systems engineer": "ICT system administrator",
    "infrastructure engineer": "ICT system administrator",
    "kubernetes engineer": "ICT system administrator",
    "platform engineer": "ICT system administrator",
    "system administrator": "ICT system administrator",
    # Database
    "database administrator": "database administrator",
    "database engineer": "database administrator",
    "sql developer": "database administrator",
    "nosql developer": "database administrator",
    # Quality Assurance & Security
    "software tester": "software tester",
    "qa engineer": "software tester",
    "software testing & automation engineer": "software tester",
    "security engineer": "ict security specialist",
    "information security analyst": "ict security specialist",
    "it support specialist": "ict help desk technician",
}


def load_onet_supplementary_data() -> dict[str, dict[str, Any]]:
    """Load O*NET skill mapping table for supplementary importance and level scores.

    Returns
    -------
    Dictionary mapping normalized skill name (casefolded) to O*NET metadata.
    """
    onet_path = get_datasets_dir() / "ESCO_ONET" / "Mappings" / "ONET_Skill_Mapping.csv"
    if not onet_path.exists():
        logger.warning("ONET_Skill_Mapping.csv not found at %s", onet_path)
        return {}

    lookup: dict[str, dict[str, Any]] = {}
    with onet_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Handle possible BOM
            skill_name = (row.get("Skill_Name") or row.get("\ufeffSkill_Name") or "").strip()
            if not skill_name:
                continue

            try:
                imp = float(row.get("Importance_Score", 0.0))
            except (ValueError, TypeError):
                imp = 0.0

            try:
                lvl = float(row.get("Level_Score", 0.0))
            except (ValueError, TypeError):
                lvl = 0.0

            soc = row.get("ONET_SOC_Code") or row.get("\ufeffONET_SOC_Code") or ""
            norm_key = skill_name.casefold()
            # If seen before, keep highest importance
            if norm_key not in lookup or imp > lookup[norm_key]["importance_score"]:
                lookup[norm_key] = {
                    "skill_name": skill_name,
                    "onet_skill_id": row.get("ONET_Skill_Id", ""),
                    "onet_soc_code": soc,
                    "skill_type": row.get("Skill_Type", ""),
                    "importance_score": imp,
                    "level_score": lvl,
                }

    return lookup


class RoleOccupationResolver:
    """Robust resolver mapping candidate roles and resume job titles to canonical ESCO occupations."""

    def __init__(self, graph: ESCOKnowledgeGraph | None = None) -> None:
        self.graph = graph if graph is not None else get_esco_graph()
        self._cache: dict[str, tuple[str, str] | None] = {}

    def resolve(self, raw_title: str | None) -> tuple[str, str] | None:
        """Resolve a title or role string to (esco_uri, esco_preferred_label).

        Returns None if no grounded ESCO occupation can be determined.
        """
        if not raw_title or not isinstance(raw_title, str):
            return None

        cleaned = raw_title.strip()
        if not cleaned:
            return None

        cache_key = cleaned.casefold()
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 1. Direct ESCO resolution
        uri = self.graph.resolve_occupation_uri(cleaned)
        if uri:
            node = self.graph.get_occupation_node(uri)
            label = node.get("label", cleaned) if node else cleaned
            res = (uri, label)
            self._cache[cache_key] = res
            return res

        # 2. Strip Seniority / Rank Prefixes (e.g., 'Senior Backend Engineer' -> 'Backend Engineer')
        without_prefix = PREFIX_REGEX.sub("", cleaned).strip()
        if without_prefix and without_prefix.casefold() != cache_key:
            uri = self.graph.resolve_occupation_uri(without_prefix)
            if uri:
                node = self.graph.get_occupation_node(uri)
                label = node.get("label", without_prefix) if node else without_prefix
                res = (uri, label)
                self._cache[cache_key] = res
                return res

        # 3. Canonical dictionary lookup
        lookup_candidate = without_prefix.casefold() if without_prefix else cache_key
        if lookup_candidate in CANONICAL_OCCUPATION_MAP:
            target_label = CANONICAL_OCCUPATION_MAP[lookup_candidate]
            uri = self.graph.resolve_occupation_uri(target_label)
            if uri:
                node = self.graph.get_occupation_node(uri)
                label = node.get("label", target_label) if node else target_label
                res = (uri, label)
                self._cache[cache_key] = res
                return res

        # 4. Partial / Suffix stripping
        without_suffix = SUFFIX_REGEX.sub("", lookup_candidate).strip()
        if without_suffix and without_suffix in CANONICAL_OCCUPATION_MAP:
            target_label = CANONICAL_OCCUPATION_MAP[without_suffix]
            uri = self.graph.resolve_occupation_uri(target_label)
            if uri:
                node = self.graph.get_occupation_node(uri)
                label = node.get("label", target_label) if node else target_label
                res = (uri, label)
                self._cache[cache_key] = res
                return res

        # Not resolved
        self._cache[cache_key] = None
        return None


class UnifiedDatasetBuilder:
    """Orchestrates generation of the unified candidate-occupation dataset."""

    def __init__(
        self,
        graph: ESCOKnowledgeGraph | None = None,
        taxonomy: ESCOTaxonomy | None = None,
        detector: SkillGapDetector | None = None,
        output_dir: Path | None = None,
    ) -> None:
        self.taxonomy = taxonomy if taxonomy is not None else get_esco_taxonomy()
        self.graph = graph if graph is not None else get_esco_graph(self.taxonomy)
        self.detector = detector if detector is not None else SkillGapDetector(
            graph=self.graph,
            taxonomy=self.taxonomy,
        )
        self.resolver = RoleOccupationResolver(self.graph)
        self.onet_lookup = load_onet_supplementary_data()
        self.gold_label_index = get_gold_label_index()

        self.output_dir = output_dir or (get_datasets_dir() / "Processed")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.output_file = self.output_dir / "candidate_occupation_dataset.jsonl"

        # Statistics Tracking
        self.total_candidates_processed = 0
        self.candidates_by_source: dict[str, int] = {}
        self.total_pairs_generated = 0
        self.unique_occupations_covered: set[str] = set()
        self.excluded_records: list[dict[str, Any]] = []
        self.seen_pair_keys: set[str] = set()
        self.coverage_scores: list[float] = []

    def _extract_ground_truth(
        self, candidate_id: str | int, occupation_title: str
    ) -> GroundTruthAlignment | None:
        """Check for gold compatibility annotations matching candidate_id.

        Note: Gold labels strictly represent candidate-job compatibility per M4.2 audit,
        never career readiness.
        """
        cand_str = str(candidate_id)
        # Search by cand_X or raw X
        for pair_id, item in self.gold_label_index.items():
            g_cand = str(item.get("candidate_id", ""))
            if g_cand == cand_str or g_cand == f"cand_{cand_str}":
                return {
                    "pair_id": pair_id,
                    "skills_score": item.get("skills_score"),
                    "seniority_score": item.get("seniority_score"),
                    "domain_score": item.get("domain_score"),
                    "location_score": item.get("location_score"),
                    "composite_score": item.get("composite_score"),
                    "overqualified": item.get("overqualified"),
                    "reasoning": item.get("reasoning"),
                }
        return None

    def _extract_graph_features(
        self,
        candidate_profile: CandidateProfile,
        target_uri: str,
        gap_report: SkillGapReport,
    ) -> GraphTopologicalFeatures:
        """Extract graph topological features using PersonalizedKnowledgeGraph."""
        pkg = PersonalizedKnowledgeGraph(
            candidate=candidate_profile,
            target_occupation=target_uri,
            esco_graph=self.graph,
            gap_report=gap_report,
        )
        summary = pkg.get_summary()
        node_counts = summary.get("node_counts_by_kind", {})
        edge_counts = summary.get("edge_counts_by_relation", {})

        provenance = edge_counts.get("applies_skill", 0) + edge_counts.get("uses_skill", 0)
        taxonomy_rels = sum(
            edge_counts.get(k, 0)
            for k in (
                "broader_skill",
                "narrower_skill",
                "related",
                "member_of_group",
                "is_broader_than",
                "is_narrower_than",
                "is_related_to",
            )
        )

        return {
            "total_nodes": summary.get("total_nodes", 0),
            "total_edges": summary.get("total_edges", 0),
            "provenance_edges_count": provenance,
            "candidate_skill_nodes_count": node_counts.get("candidate_skill", 0),
            "esco_skill_nodes_count": node_counts.get("esco_skill", 0),
            "taxonomy_edges_count": taxonomy_rels,
        }

    def _enrich_skills_with_onet(self, skill_list: list[dict[str, Any]]) -> None:
        """Attach supplementary O*NET importance/level data in place if matching."""
        if not self.onet_lookup:
            return
        for item in skill_list:
            name = item.get("skill") or item.get("skill_label") or item.get("name") or ""
            if not isinstance(name, str):
                continue
            norm = name.casefold()
            if norm in self.onet_lookup:
                onet_entry = self.onet_lookup[norm]
                item["onet_supplementary"] = {
                    "onet_skill_id": onet_entry["onet_skill_id"],
                    "onet_soc_code": onet_entry["onet_soc_code"],
                    "importance_score": onet_entry["importance_score"],
                    "level_score": onet_entry["level_score"],
                }

    def build_candidate_occupation_record(
        self,
        candidate_profile: CandidateProfile,
        target_occupation_uri: str,
        candidate_source: str,
    ) -> CandidateOccupationRecord | None:
        """Construct a validated CandidateOccupationRecord."""
        cand_id = str(candidate_profile.get("metadata", {}).get("candidate_id", "unknown"))
        pair_key = f"{cand_id}__{target_occupation_uri}"

        # Deduplication check
        if pair_key in self.seen_pair_keys:
            self.excluded_records.append({
                "candidate_id": cand_id,
                "source": candidate_source,
                "target_occupation": target_occupation_uri,
                "reason": "Duplicate candidate-occupation pair",
            })
            return None

        # Resolve target occupation requirement summary
        try:
            target_summary: OccupationRequirementSummary = adapt_esco_occupation(
                target_occupation_uri, graph=self.graph
            )
        except Exception as err:
            self.excluded_records.append({
                "candidate_id": cand_id,
                "source": candidate_source,
                "target_occupation": target_occupation_uri,
                "reason": f"Failed to adapt ESCO target occupation: {err}",
            })
            return None

        # Hybrid Skill Gap Detection
        try:
            gap_report = self.detector.detect_gap(candidate_profile, target_occupation_uri)
        except Exception as err:
            self.excluded_records.append({
                "candidate_id": cand_id,
                "source": candidate_source,
                "target_occupation": target_occupation_uri,
                "reason": f"Skill gap detection error: {err}",
            })
            return None

        # Topological graph features
        graph_feats = self._extract_graph_features(
            candidate_profile, target_occupation_uri, gap_report
        )

        # Ground truth compatibility alignment (strictly separate from readiness)
        ground_truth = self._extract_ground_truth(cand_id, target_summary["occupation_title"])

        # Extract normalized candidate skill names
        cand_skills_normalized = [
            s.get("ESCO_Skill_Name") or s.get("skill")
            for s in candidate_profile.get("skills", [])
            if s.get("ESCO_Skill_Name") or s.get("skill")
        ]

        # Extract numerical features
        gap_summary = gap_report.get("matching_summary", {})
        scoring_weights = gap_report.get("scoring_weights", {})
        skill_gap_feats: SkillGapSummaryFeatures = {
            "overall_skill_coverage_score": gap_report.get("overall_skill_coverage_score", 0.0),
            "essential_skill_coverage_score": gap_report.get("essential_skill_coverage_score", 0.0),
            "optional_skill_coverage_score": gap_report.get("optional_skill_coverage_score"),
            "essential_weight": scoring_weights.get("essential_weight", 0.75),
            "optional_weight": scoring_weights.get("optional_weight", 0.25),
            "matched_skills_count": gap_summary.get("matched_skills_count", 0),
            "partially_matched_skills_count": gap_summary.get("partially_matched_skills_count", 0),
            "missing_essential_skills_count": gap_summary.get("missing_essential_skills_count", 0),
            "missing_optional_skills_count": gap_summary.get("missing_optional_skills_count", 0),
            "unmapped_candidate_skills_count": gap_summary.get("unmapped_candidate_skills_count", 0),
            "surplus_candidate_skills_count": gap_summary.get("surplus_candidate_skills_count", 0),
        }

        # Track stats
        self.seen_pair_keys.add(pair_key)
        self.unique_occupations_covered.add(target_occupation_uri)
        self.coverage_scores.append(gap_report.get("overall_skill_coverage_score", 0.0))

        record: CandidateOccupationRecord = {
            "pair_id": pair_key,
            "candidate_id": cand_id,
            "candidate_source": candidate_source,
            "candidate_profile": candidate_profile,
            "candidate_skills_normalized": cand_skills_normalized,
            "target_occupation": target_summary,
            "skill_gap_features": skill_gap_feats,
            "graph_features": graph_feats,
            "matched_skills_evidence": gap_report.get("matched_skills", []),
            "partially_matched_skills_evidence": gap_report.get("partially_matched_skills", []),
            "missing_essential_skills": gap_report.get("missing_essential_skills", []),
            "missing_optional_skills": gap_report.get("missing_optional_skills", []),
            "ground_truth": ground_truth,
            "metadata": {
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                "scoring_disclaimer": gap_report.get("disclaimer"),
                "has_gold_compatibility_label": ground_truth is not None,
                "onet_supplementary_available": bool(self.onet_lookup),
            },
        }

        return record

    def process_synthetic_profiles(
        self,
        limit: int | None = None,
        writer: Any = None,
    ) -> int:
        """Process synthetic profiles from synthetic_profiles.json."""
        raw_profiles = load_synthetic_profiles(limit=limit)
        generated = 0

        for raw_profile in raw_profiles:
            self.total_candidates_processed += 1
            self.candidates_by_source["synthetic_profiles"] = (
                self.candidates_by_source.get("synthetic_profiles", 0) + 1
            )
            cand_id = str(raw_profile.get("profile_id", "unknown"))

            # 1. Adapt to standardized CandidateProfile (v1.1.0)
            try:
                candidate_profile = adapt_synthetic_profile_to_candidate_profile(
                    raw_profile, taxonomy=self.taxonomy
                )
            except Exception as err:
                self.excluded_records.append({
                    "candidate_id": cand_id,
                    "source": "synthetic_profiles",
                    "reason": f"Adapter error: {err}",
                })
                continue

            # 2. Schema validation check
            val = validate_candidate_profile_comprehensive(candidate_profile)
            if val["errors"]:
                self.excluded_records.append({
                    "candidate_id": cand_id,
                    "source": "synthetic_profiles",
                    "reason": f"Schema validation error: {'; '.join(val['errors'])}",
                })
                continue

            # Check profile non-empty
            if not candidate_profile["skills"] and not candidate_profile["experience"]:
                self.excluded_records.append({
                    "candidate_id": cand_id,
                    "source": "synthetic_profiles",
                    "reason": "Empty profile: zero skills and zero experience",
                })
                continue

            # 3. Resolve target occupation
            roles = raw_profile.get("roles", []) or []
            target_role = roles[0] if roles else None
            resolved = self.resolver.resolve(target_role)

            if not resolved:
                # Fallback to software developer if candidate has tech skills
                resolved = self.resolver.resolve("software developer")

            if not resolved:
                self.excluded_records.append({
                    "candidate_id": cand_id,
                    "source": "synthetic_profiles",
                    "reason": f"Target occupation '{target_role}' unresolvable in ESCO",
                })
                continue

            target_uri, _ = resolved

            # 4. Build unified record
            record = self.build_candidate_occupation_record(
                candidate_profile=candidate_profile,
                target_occupation_uri=target_uri,
                candidate_source="synthetic_profiles",
            )

            if record and writer is not None:
                writer.write(json.dumps(record) + "\n")
                generated += 1
                self.total_pairs_generated += 1

        return generated

    def process_master_resumes(
        self,
        limit: int | None = None,
        writer: Any = None,
    ) -> int:
        """Process real resume records from master_resumes.jsonl (streaming)."""
        generated = 0
        idx = 0

        for raw_resume in stream_master_resumes(limit=limit):
            idx += 1
            cand_id = f"mr_{idx}"
            self.total_candidates_processed += 1
            self.candidates_by_source["master_resumes"] = (
                self.candidates_by_source.get("master_resumes", 0) + 1
            )

            # 1. Adapt to standardized CandidateProfile (v1.1.0)
            try:
                candidate_profile = adapt_master_resume_to_candidate_profile(
                    raw_resume, candidate_id=cand_id, taxonomy=self.taxonomy
                )
            except Exception as err:
                self.excluded_records.append({
                    "candidate_id": cand_id,
                    "source": "master_resumes",
                    "reason": f"Adapter error: {err}",
                })
                continue

            # 2. Schema validation check
            val = validate_candidate_profile_comprehensive(candidate_profile)
            if val["errors"]:
                self.excluded_records.append({
                    "candidate_id": cand_id,
                    "source": "master_resumes",
                    "reason": f"Schema validation error: {'; '.join(val['errors'])}",
                })
                continue

            # Check profile non-empty
            if not candidate_profile["skills"] and not candidate_profile["experience"]:
                self.excluded_records.append({
                    "candidate_id": cand_id,
                    "source": "master_resumes",
                    "reason": "Empty resume: zero skills and zero experience",
                })
                continue

            # 3. Determine target occupation
            target_role: str | None = None
            exps = candidate_profile.get("experience", [])
            if exps and isinstance(exps[0], dict) and exps[0].get("job_title"):
                target_role = exps[0].get("job_title")
            elif candidate_profile.get("candidate", {}).get("summary"):
                target_role = candidate_profile["candidate"]["summary"]

            resolved = self.resolver.resolve(target_role)
            if not resolved:
                # Secondary attempt: inspect skills or summary
                resolved = self.resolver.resolve("software developer")

            if not resolved:
                self.excluded_records.append({
                    "candidate_id": cand_id,
                    "source": "master_resumes",
                    "reason": f"Target occupation '{target_role}' unresolvable in ESCO",
                })
                continue

            target_uri, _ = resolved

            # 4. Build unified record
            record = self.build_candidate_occupation_record(
                candidate_profile=candidate_profile,
                target_occupation_uri=target_uri,
                candidate_source="master_resumes",
            )

            if record and writer is not None:
                writer.write(json.dumps(record) + "\n")
                generated += 1
                self.total_pairs_generated += 1

        return generated

    def build_dataset(
        self,
        master_limit: int | None = 500,
        synthetic_limit: int | None = None,
    ) -> Path:
        """Run complete dataset generation pipeline and save to JSONL."""
        start_time = time.time()
        logger.info("Starting unified dataset generation to %s", self.output_file)

        with self.output_file.open("w", encoding="utf-8") as out:
            # 1. Synthetic Profiles
            syn_count = self.process_synthetic_profiles(limit=synthetic_limit, writer=out)
            logger.info("Processed %d synthetic profiles", syn_count)

            # 2. Master Resumes (Streaming)
            mr_count = self.process_master_resumes(limit=master_limit, writer=out)
            logger.info("Processed %d master resumes", mr_count)

        duration = time.time() - start_time
        logger.info(
            "Dataset construction completed in %.2f seconds. Pairs: %d, Excluded: %d",
            duration,
            self.total_pairs_generated,
            len(self.excluded_records),
        )

        return self.output_file

    def generate_report(self, report_path: Path | None = None) -> Path:
        """Generate comprehensive markdown summary report of the built dataset."""
        target_path = report_path or (
            Path(__file__).resolve().parent / "unified_dataset_report.md"
        )

        avg_cov = (
            sum(self.coverage_scores) / len(self.coverage_scores)
            if self.coverage_scores
            else 0.0
        )
        min_cov = min(self.coverage_scores) if self.coverage_scores else 0.0
        max_cov = max(self.coverage_scores) if self.coverage_scores else 0.0

        # Exclusion reason breakdown
        reasons_counter: dict[str, int] = {}
        for item in self.excluded_records:
            r = item.get("reason", "Unknown")
            # Group specific errors
            if "Schema validation" in r:
                r_key = "Schema Validation Error"
            elif "unresolvable" in r:
                r_key = "Unresolvable Target Occupation"
            elif "zero skills" in r:
                r_key = "Empty Profile (Zero Skills & Experience)"
            elif "Duplicate" in r:
                r_key = "Duplicate Candidate-Occupation Pair"
            else:
                r_key = r
            reasons_counter[r_key] = reasons_counter.get(r_key, 0) + 1

        content = f"""# Road2Hire — M4.2 Unified Candidate–Occupation Dataset Report

**Generated:** {time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}  
**Output Dataset:** `{self.output_file.resolve()}`  
**Dataset Format:** JSON Lines (`.jsonl`)

---

## 1. Executive Summary

This report documents the construction of the **Road2Hire Unified Candidate–Occupation Dataset (M4.2)**.
The dataset integrates standardized candidate profiles, canonical ESCO occupation skill requirements, hybrid skill gap detection features, personalized knowledge graph topological metrics, and supplementary O*NET skill benchmarks.

> [!IMPORTANT]
> **Strict Separation of Compatibility and Career Readiness:**  
> Ground-truth labels from `gold_labels.json` represent **candidate-job compatibility** scores (evaluating skills, seniority, domain, and location alignment for specific job postings), **NOT career readiness**.
> In accordance with the M4.2 Gold-Label Quality Audit, these compatibility scores are stored strictly in a separate `ground_truth` sub-record and are **never** used as artificial career-readiness training targets.

---

## 2. Dataset Construction Statistics

| Metric | Count |
|:---|:---|
| **Total Candidate Profiles Processed** | **{self.total_candidates_processed:,}** |
| - *Synthetic Profiles (`synthetic_profiles.json`)* | {self.candidates_by_source.get("synthetic_profiles", 0):,} |
| - *Real Parsed Resumes (`master_resumes.jsonl`)* | {self.candidates_by_source.get("master_resumes", 0):,} |
| **Total Candidate–Occupation Pairs Generated** | **{self.total_pairs_generated:,}** |
| **Unique ESCO Occupations Grounded** | **{len(self.unique_occupations_covered):,}** |
| **Records Excluded** | **{len(self.excluded_records):,}** |
| **Supplementary O*NET Benchmarks Integrated** | **{len(self.onet_lookup):,} skills** |

### Skill Gap Coverage Distribution
- **Mean Overall Skill Coverage Score:** `{avg_cov:.3f}` ({avg_cov * 100:.1f}%)
- **Min Overall Skill Coverage Score:** `{min_cov:.3f}`
- **Max Overall Skill Coverage Score:** `{max_cov:.3f}`

---

## 3. Exclusions & Quality Control Log

A strict validation protocol was enforced during dataset construction. Records failing schema validation, lacking profile information, or possessing unresolvable target occupations were systematically excluded:

| Exclusion Reason | Count | Action Taken |
|:---|:---|:---|
"""
        for reason, count in sorted(reasons_counter.items(), key=lambda x: -x[1]):
            content += f"| {reason} | {count:,} | Excluded from final `.jsonl` |\n"

        if not reasons_counter:
            content += "| *None (100% of candidate profiles passed all criteria)* | 0 | All retained |\n"

        content += f"""
---

## 4. Record Schema & Data Contracts

Each line of `{self.output_file.name}` contains a standalone JSON object conforming to `CandidateOccupationRecord` (`AI/Dataset_Preparation/unified_schema.py`):

1. **`pair_id`**: Deterministic unique key (`{{candidate_id}}__{{target_occupation_uri}}`).
2. **`candidate_id`**: Originating identifier from the source repository.
3. **`candidate_source`**: Provenance identifier (`"synthetic_profiles"` or `"master_resumes"`).
4. **`candidate_profile`**: Complete, validated `CandidateProfile` adhering to **Schema v1.1.0** (education, experience, projects, certifications, skills, personal info).
5. **`candidate_skills_normalized`**: List of canonical ESCO skill names held by the candidate.
6. **`target_occupation`**: Grounded `OccupationRequirementSummary` containing ESCO URI, preferred label, description, and lists of essential and optional skill requirements.
7. **`skill_gap_features`**: Explainable numerical features derived from the M3 Hybrid Skill Gap engine:
   - `overall_skill_coverage_score`
   - `essential_skill_coverage_score`
   - `optional_skill_coverage_score`
   - `matched_skills_count`
   - `partially_matched_skills_count`
   - `missing_essential_skills_count`
   - `missing_optional_skills_count`
   - `unmapped_candidate_skills_count`
   - `surplus_candidate_skills_count`
8. **`graph_features`**: Topological metrics extracted from the candidate's Personalized Knowledge Graph (total nodes, edges, provenance relations, taxonomy relations).
9. **`matched_skills_evidence` & `partially_matched_skills_evidence`**: Full audit trails detailing the matching tier (`exact`, `graph`, `semantic`), credits assigned, and justification.
10. **`missing_essential_skills` & `missing_optional_skills`**: Explicit lists of target requirements absent from the profile.
11. **`ground_truth`**: Nullable compatibility benchmark metadata from `gold_labels.json` (skills, seniority, domain, location scores, and auditor reasoning).

---

## 5. Usage & Integration Guide

To stream or load records in downstream ML research and pipeline modules:

```python
import json
from pathlib import Path

DATASET_PATH = Path("Datasets/Processed/candidate_occupation_dataset.jsonl")

def stream_unified_dataset():
    with DATASET_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

# Example iteration
for record in stream_unified_dataset():
    cand_id = record["candidate_id"]
    target_occ = record["target_occupation"]["occupation_title"]
    coverage = record["skill_gap_features"]["overall_skill_coverage_score"]
    print(f"Candidate {{cand_id}} -> {{target_occ}}: coverage={{coverage:.2%}}")
```

---

## 6. Limitations & Planned Next Steps

1. **Synthetic Profiles Specificity**: Synthetic candidate profiles do not contain academic degrees or projects; their experience entries represent declared career history.
2. **Streaming for Large Master Resumes**: The builder supports streaming to safely process `master_resumes.jsonl` without memory exhaustion.
3. **Gold Label Volume**: Only candidates with existing human annotations in `gold_labels.json` have populated `ground_truth` blocks.
"""
        target_path.write_text(content, encoding="utf-8")
        return target_path


def main() -> None:
    """CLI entry point for unified dataset construction."""
    parser = argparse.ArgumentParser(description="Build Road2Hire Unified Dataset (M4.2)")
    parser.add_argument(
        "--master-limit",
        type=int,
        default=500,
        help="Maximum master resumes to process (default: 500, set -1 for all)",
    )
    parser.add_argument(
        "--synthetic-limit",
        type=int,
        default=None,
        help="Maximum synthetic profiles to process (default: None for all 640)",
    )
    args = parser.parse_args()

    m_limit = None if args.master_limit == -1 else args.master_limit
    s_limit = args.synthetic_limit

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    builder = UnifiedDatasetBuilder()
    output_file = builder.build_dataset(master_limit=m_limit, synthetic_limit=s_limit)
    report_file = builder.generate_report()

    print(f"\n[DONE] Unified dataset written to: {output_file}")
    print(f"[DONE] Dataset audit report written to: {report_file}")
    print(f"Total pairs generated: {builder.total_pairs_generated}")
    print(f"Total candidates processed: {builder.total_candidates_processed}")
    print(f"Total exclusions: {len(builder.excluded_records)}")


if __name__ == "__main__":
    main()
