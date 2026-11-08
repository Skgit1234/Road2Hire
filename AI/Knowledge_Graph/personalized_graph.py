"""Personalized Knowledge Graph Construction for Road2Hire (M3).

Constructs candidate-specific directed knowledge graphs in NetworkX combining:
1. Structured candidate profile entities (education, experience, projects, certifications, skills).
2. ESCO taxonomy grounding (occupation, skills, hierarchical and semantic relationships).
3. Hybrid skill gap detection results (matched, partially matched, missing, surplus, unmapped).

Enforces node uniqueness, collision-free edge merging, and preserves canonical ESCO URIs
without duplicating the global 17,000+ node taxonomy graph.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import networkx as nx

from AI.Candidate_Profile.profile_schema import CandidateProfile
from AI.Knowledge_Graph.esco_graph import ESCOKnowledgeGraph, get_esco_graph
from AI.Skill_Extraction.esco_taxonomy import ESCOTaxonomy, get_esco_taxonomy
from AI.Skill_Gap.gap_schema import SkillGapReport

if TYPE_CHECKING:
    from AI.Skill_Gap.skill_gap_detector import SkillGapDetector

logger = logging.getLogger(__name__)


class PersonalizedKnowledgeGraph:
    """Directed graph representation of a candidate's profile, career goal, and skill gap alignment.

    Parameters
    ----------
    candidate:
        Structured candidate profile dictionary or CandidateProfile object.
    target_occupation:
        ESCO occupation preferred label, alternative label, or concept URI.
    esco_graph:
        Optional pre-loaded ESCOKnowledgeGraph instance (reuses cached singleton by default).
    taxonomy:
        Optional pre-loaded ESCOTaxonomy instance.
    gap_report:
        Optional pre-computed SkillGapReport. If None, automatically computed.
    detector:
        Optional SkillGapDetector instance.
    """

    def __init__(
        self,
        candidate: CandidateProfile | dict[str, Any],
        target_occupation: str,
        esco_graph: ESCOKnowledgeGraph | None = None,
        taxonomy: ESCOTaxonomy | None = None,
        gap_report: SkillGapReport | dict[str, Any] | None = None,
        detector: SkillGapDetector | None = None,
    ) -> None:
        self.candidate = candidate
        self.target_occupation_input = target_occupation
        self.taxonomy = taxonomy if taxonomy is not None else get_esco_taxonomy()
        self.esco_graph = esco_graph if esco_graph is not None else get_esco_graph(self.taxonomy)
        if detector is not None:
            self.detector = detector
        else:
            from AI.Skill_Gap.skill_gap_detector import get_skill_gap_detector
            self.detector = get_skill_gap_detector()

        # Compute or reuse skill gap report
        if gap_report is not None:
            self.gap_report: SkillGapReport | dict[str, Any] = gap_report
        else:
            self.gap_report = self.detector.detect_gap(candidate, target_occupation)

        self.graph = nx.DiGraph()
        self._build_graph()

    # ------------------------------------------------------------------
    # Edge and Node Helpers (Duplicate and Collision Prevention)
    # ------------------------------------------------------------------

    def _add_or_update_node(self, node_id: str, **attrs: Any) -> None:
        """Add a node or update its attributes without overwriting existing data."""
        if self.graph.has_node(node_id):
            self.graph.nodes[node_id].update(attrs)
        else:
            self.graph.add_node(node_id, **attrs)

    def _add_or_merge_edge(
        self,
        source: str,
        target: str,
        relation: str,
        relation_type: str = "relationship",
        **extra_attrs: Any,
    ) -> None:
        """Add a directed edge or merge relationship information if edge already exists."""
        entry = {
            "relation": relation,
            "relation_type": relation_type,
            **extra_attrs,
        }

        if self.graph.has_edge(source, target):
            edge_data = self.graph.edges[source, target]
            if "relations" not in edge_data:
                existing_entry = {
                    "relation": edge_data.get("relation"),
                    "relation_type": edge_data.get("relation_type", "relationship"),
                }
                for k, v in edge_data.items():
                    if k not in ("relation", "relation_type", "relations", "relation_names"):
                        existing_entry[k] = v
                edge_data["relations"] = [existing_entry]
                edge_data["relation_names"] = [existing_entry["relation"]]

            if not any(
                r.get("relation") == relation and r.get("relation_type") == relation_type
                for r in edge_data["relations"]
            ):
                edge_data["relations"].append(entry)
                if relation not in edge_data["relation_names"]:
                    edge_data["relation_names"].append(relation)
            # Update top-level attributes for immediate convenience
            for k, v in extra_attrs.items():
                edge_data[k] = v
        else:
            self.graph.add_edge(
                source,
                target,
                relation=relation,
                relation_type=relation_type,
                relations=[entry],
                relation_names=[relation],
                **extra_attrs,
            )

    # ------------------------------------------------------------------
    # Graph Construction Pipeline
    # ------------------------------------------------------------------

    def _build_graph(self) -> None:
        """Construct the candidate personalized knowledge graph."""
        # 1. Candidate Entity Root Node
        candidate_info = self.candidate.get("candidate", {}) if isinstance(self.candidate, dict) else {}
        cand_name = candidate_info.get("name") or "Candidate"
        cand_root_id = "candidate:root"

        self._add_or_update_node(
            cand_root_id,
            kind="candidate",
            name=cand_name,
            email=candidate_info.get("email"),
            phone=candidate_info.get("phone"),
            location=candidate_info.get("location"),
            summary=candidate_info.get("summary"),
            schema_version=self.candidate.get("schema_version", "1.1.0") if isinstance(self.candidate, dict) else "1.1.0",
        )

        # 2. Target Occupation Node
        target_info = self.gap_report.get("target_occupation", {})
        occ_uri = target_info.get("uri") or self.esco_graph.resolve_occupation_uri(self.target_occupation_input)
        occ_label = target_info.get("preferred_label") or self.target_occupation_input
        occ_desc = target_info.get("description")

        if occ_uri:
            self._add_or_update_node(
                occ_uri,
                kind="occupation",
                label=occ_label,
                uri=occ_uri,
                description=occ_desc,
                essential_skills_count=target_info.get("essential_skills_count", 0),
                optional_skills_count=target_info.get("optional_skills_count", 0),
                total_skills_count=target_info.get("total_skills_count", 0),
            )

            # Connect Candidate to Target Occupation
            self._add_or_merge_edge(
                cand_root_id,
                occ_uri,
                relation="targets_occupation",
                relation_type="career_goal",
                overall_coverage_score=self.gap_report.get("overall_skill_coverage_score", 0.0),
                essential_coverage_score=self.gap_report.get("essential_skill_coverage_score", 0.0),
                optional_coverage_score=self.gap_report.get("optional_skill_coverage_score"),
            )

        # 3. Add Candidate Profile Components (Education, Experience, Projects, Certifications)
        self._add_profile_components(cand_root_id)

        # 4. Add Candidate Skills and link to Profile Components & ESCO
        candidate_skill_nodes = self._add_candidate_skills(cand_root_id)

        # 5. Add Occupation Requirement Skills and Missing Skills
        target_skill_uris = self._add_target_skills(occ_uri)

        # 6. Add Skill Gap Match and Alignment Edges
        self._add_gap_alignment_edges(candidate_skill_nodes)

        # 7. Preserve ESCO Taxonomy Relationships between relevant graph skills
        self._preserve_esco_skill_relationships(target_skill_uris, candidate_skill_nodes)

    def _add_profile_components(self, cand_root_id: str) -> None:
        """Add education, experience, project, and certification nodes."""
        if not isinstance(self.candidate, dict):
            return

        # Education
        education_list = self.candidate.get("education", [])
        for idx, edu in enumerate(education_list):
            if not isinstance(edu, dict):
                continue
            edu_id = f"candidate:education:{idx}"
            self._add_or_update_node(
                edu_id,
                kind="education",
                degree=edu.get("degree"),
                field_of_study=edu.get("field_of_study"),
                institution=edu.get("institution"),
                start_year=edu.get("start_year"),
                end_year=edu.get("end_year"),
                grade=edu.get("cgpa") if edu.get("cgpa") is not None else edu.get("percentage"),
                academic_level=edu.get("academic_level"),
                raw_text=edu.get("raw_text", ""),
            )
            self._add_or_merge_edge(
                cand_root_id,
                edu_id,
                relation="has_education",
                relation_type="profile_component",
            )

        # Experience
        exp_list = self.candidate.get("experience", [])
        for idx, exp in enumerate(exp_list):
            if not isinstance(exp, dict):
                continue
            exp_id = f"candidate:experience:{idx}"
            self._add_or_update_node(
                exp_id,
                kind="experience",
                job_title=exp.get("job_title"),
                organization=exp.get("organization"),
                employment_type=exp.get("employment_type"),
                start_date=exp.get("start_date"),
                end_date=exp.get("end_date"),
                responsibilities=exp.get("responsibilities", []),
                skills_used=exp.get("skills_used", []),
                raw_text=exp.get("raw_text", ""),
            )
            self._add_or_merge_edge(
                cand_root_id,
                exp_id,
                relation="has_experience",
                relation_type="profile_component",
            )

        # Projects
        proj_list = self.candidate.get("projects", [])
        for idx, proj in enumerate(proj_list):
            if not isinstance(proj, dict):
                continue
            proj_id = f"candidate:project:{idx}"
            self._add_or_update_node(
                proj_id,
                kind="project",
                project_name=proj.get("project_name"),
                description=proj.get("description"),
                technologies=proj.get("technologies", []),
                related_skills=proj.get("related_skills", []),
                raw_text=proj.get("raw_text", ""),
            )
            self._add_or_merge_edge(
                cand_root_id,
                proj_id,
                relation="has_project",
                relation_type="profile_component",
            )

        # Certifications
        cert_list = self.candidate.get("certifications", [])
        for idx, cert in enumerate(cert_list):
            if not isinstance(cert, dict):
                continue
            cert_id = f"candidate:certification:{idx}"
            self._add_or_update_node(
                cert_id,
                kind="certification",
                name=cert.get("name"),
                issuing_organization=cert.get("issuing_organization"),
                issue_date=cert.get("issue_date"),
                expiration_date=cert.get("expiration_date"),
                credential_id=cert.get("credential_id"),
                raw_text=cert.get("raw_text", ""),
            )
            self._add_or_merge_edge(
                cand_root_id,
                cert_id,
                relation="has_certification",
                relation_type="profile_component",
            )

    def _add_candidate_skills(self, cand_root_id: str) -> dict[str, str]:
        """Add candidate skill nodes and connect them to profile components and ESCO.

        Returns mapping from candidate skill normalized name to candidate skill node id.
        """
        raw_skills: list[Any] = []
        if isinstance(self.candidate, dict):
            raw_skills = self.candidate.get("skills", [])
        elif isinstance(self.candidate, list):
            raw_skills = self.candidate

        name_to_node_id: dict[str, str] = {}
        surplus_names = {s.casefold() for s in self.gap_report.get("surplus_candidate_skills", [])}
        unmapped_names = {s.casefold() for s in self.gap_report.get("unmapped_candidate_skills", [])}

        for item in raw_skills:
            name: str = ""
            esco_uri: str | None = None

            if isinstance(item, dict):
                name = (item.get("ESCO_Skill_Name") or item.get("skill") or "").strip()
                esco_uri = item.get("ESCO_Skill_Id") or None
                if not esco_uri and name:
                    esco_uri = self.esco_graph.resolve_skill_uri(name)
            elif isinstance(item, str):
                name = item.strip()
                if name:
                    esco_uri = self.esco_graph.resolve_skill_uri(name)

            if not name:
                continue

            name_norm = name.casefold()
            skill_node_id = f"candidate:skill:{name_norm}"
            name_to_node_id[name_norm] = skill_node_id

            # Determine initial status
            is_surplus = name_norm in surplus_names
            is_unmapped = (name_norm in unmapped_names) or (not esco_uri)

            gap_status = "surplus" if is_surplus else ("unmapped" if is_unmapped else "evaluated")

            self._add_or_update_node(
                skill_node_id,
                kind="candidate_skill",
                label=name,
                name=name,
                esco_uri=esco_uri,
                is_esco_mapped=bool(esco_uri),
                is_unmapped=is_unmapped,
                gap_status=gap_status,
            )

            # Connect Candidate to CandidateSkill
            self._add_or_merge_edge(
                cand_root_id,
                skill_node_id,
                relation="has_skill",
                relation_type="possession",
            )

            # If surplus, tag the edge
            if is_surplus:
                self._add_or_merge_edge(
                    cand_root_id,
                    skill_node_id,
                    relation="has_surplus_skill",
                    relation_type="skill_gap",
                )

            # Connect CandidateSkill to ESCO canonical skill node if mapped
            if esco_uri and esco_uri in self.esco_graph.graph:
                esco_node = self.esco_graph.get_skill_node(esco_uri)
                esco_label = esco_node.get("label", name) if esco_node else name
                skill_type = esco_node.get("skill_type", "skill/competence") if esco_node else "skill/competence"

                self._add_or_update_node(
                    esco_uri,
                    kind="esco_skill",
                    label=esco_label,
                    uri=esco_uri,
                    skill_type=skill_type,
                    requirement_type="candidate_grounding",
                    gap_status="candidate_grounding",
                )

                self._add_or_merge_edge(
                    skill_node_id,
                    esco_uri,
                    relation="maps_to_esco",
                    relation_type="taxonomy_grounding",
                )

        # Link Profile Components (Experience & Projects) to Candidate Skills
        self._link_components_to_skills(name_to_node_id)

        return name_to_node_id

    def _link_components_to_skills(self, name_to_node_id: dict[str, str]) -> None:
        """Connect experience and project nodes to candidate skill nodes."""
        if not isinstance(self.candidate, dict):
            return

        # Link Experience
        for idx, exp in enumerate(self.candidate.get("experience", [])):
            if not isinstance(exp, dict):
                continue
            exp_id = f"candidate:experience:{idx}"
            for skill_used in exp.get("skills_used", []):
                norm = skill_used.strip().casefold()
                if norm in name_to_node_id:
                    self._add_or_merge_edge(
                        exp_id,
                        name_to_node_id[norm],
                        relation="applies_skill",
                        relation_type="provenance",
                    )

        # Link Projects
        for idx, proj in enumerate(self.candidate.get("projects", [])):
            if not isinstance(proj, dict):
                continue
            proj_id = f"candidate:project:{idx}"
            techs = proj.get("technologies", []) + proj.get("related_skills", [])
            for tech in techs:
                norm = tech.strip().casefold()
                if norm in name_to_node_id:
                    self._add_or_merge_edge(
                        proj_id,
                        name_to_node_id[norm],
                        relation="uses_skill",
                        relation_type="provenance",
                    )

    def _add_target_skills(self, occ_uri: str | None) -> set[str]:
        """Add ESCO skill nodes required by target occupation and record missing skills.

        Returns set of target skill URIs added to graph.
        """
        if not occ_uri:
            return set()

        target_skill_uris: set[str] = set()

        # Add missing essential skills
        for item in self.gap_report.get("missing_essential_skills", []):
            s_uri = item.get("skill_uri")
            if not s_uri:
                continue
            target_skill_uris.add(s_uri)
            self._add_or_update_node(
                s_uri,
                kind="esco_skill",
                label=item.get("skill_label", ""),
                uri=s_uri,
                skill_type=item.get("skill_type", "skill/competence"),
                requirement_type="essential",
                gap_status="missing",
            )
            # Edge from Occupation to Missing Skill
            self._add_or_merge_edge(
                occ_uri,
                s_uri,
                relation="requires_essential_skill",
                relation_type="occupation_requirement",
            )
            self._add_or_merge_edge(
                occ_uri,
                s_uri,
                relation="has_missing_skill",
                relation_type="skill_gap",
                gap_severity="essential",
            )

        # Add missing optional skills
        for item in self.gap_report.get("missing_optional_skills", []):
            s_uri = item.get("skill_uri")
            if not s_uri:
                continue
            target_skill_uris.add(s_uri)
            self._add_or_update_node(
                s_uri,
                kind="esco_skill",
                label=item.get("skill_label", ""),
                uri=s_uri,
                skill_type=item.get("skill_type", "skill/competence"),
                requirement_type="optional",
                gap_status="missing",
            )
            self._add_or_merge_edge(
                occ_uri,
                s_uri,
                relation="requires_optional_skill",
                relation_type="occupation_requirement",
            )
            self._add_or_merge_edge(
                occ_uri,
                s_uri,
                relation="has_missing_skill",
                relation_type="skill_gap",
                gap_severity="optional",
            )

        return target_skill_uris

    def _add_gap_alignment_edges(self, candidate_skill_nodes: dict[str, str]) -> None:
        """Add match and partial match edges between candidate skills and target ESCO skills."""
        occ_uri = self.gap_report.get("target_occupation", {}).get("uri")

        # 1. Matched skills
        for match in self.gap_report.get("matched_skills", []):
            c_name = match.get("candidate_skill", "")
            c_norm = c_name.strip().casefold()
            t_uri = match.get("target_uri", "")
            t_label = match.get("target_skill", "")
            t_type = match.get("target_skill_type", "essential")
            credit = match.get("credit_assigned", 1.0)
            tier = match.get("tier", "exact")

            # Ensure target ESCO skill node exists
            if t_uri:
                self._add_or_update_node(
                    t_uri,
                    kind="esco_skill",
                    label=t_label,
                    uri=t_uri,
                    requirement_type=t_type,
                    gap_status="matched",
                )
                if occ_uri:
                    self._add_or_merge_edge(
                        occ_uri,
                        t_uri,
                        relation=f"requires_{t_type}_skill",
                        relation_type="occupation_requirement",
                    )

            # Update candidate skill node gap_status
            c_node_id = candidate_skill_nodes.get(c_norm)
            if not c_node_id:
                c_node_id = f"candidate:skill:{c_norm}"
                self._add_or_update_node(
                    c_node_id,
                    kind="candidate_skill",
                    label=c_name,
                    name=c_name,
                    is_esco_mapped=bool(match.get("candidate_uri")),
                    gap_status="matched",
                )

            self.graph.nodes[c_node_id]["gap_status"] = "matched"

            # Connect CandidateSkill to TargetESCOSkill
            if t_uri:
                self._add_or_merge_edge(
                    c_node_id,
                    t_uri,
                    relation="matches_skill",
                    relation_type="skill_gap_alignment",
                    tier=tier,
                    credit_assigned=credit,
                    similarity_score=match.get("similarity_score", 1.0),
                    explanation=match.get("explanation", ""),
                )

        # 2. Partially matched skills
        for part in self.gap_report.get("partially_matched_skills", []):
            c_name = part.get("candidate_skill", "")
            c_norm = c_name.strip().casefold()
            t_uri = part.get("target_uri", "")
            t_label = part.get("target_skill", "")
            t_type = part.get("target_skill_type", "essential")
            credit = part.get("credit_assigned", 0.5)
            tier = part.get("tier", "semantic")
            graph_rel = part.get("graph_relationship")

            if t_uri:
                self._add_or_update_node(
                    t_uri,
                    kind="esco_skill",
                    label=t_label,
                    uri=t_uri,
                    requirement_type=t_type,
                    gap_status="partially_matched",
                )
                if occ_uri:
                    self._add_or_merge_edge(
                        occ_uri,
                        t_uri,
                        relation=f"requires_{t_type}_skill",
                        relation_type="occupation_requirement",
                    )

            c_node_id = candidate_skill_nodes.get(c_norm)
            if not c_node_id:
                c_node_id = f"candidate:skill:{c_norm}"
                self._add_or_update_node(
                    c_node_id,
                    kind="candidate_skill",
                    label=c_name,
                    name=c_name,
                    is_esco_mapped=bool(part.get("candidate_uri")),
                    gap_status="partially_matched",
                )

            self.graph.nodes[c_node_id]["gap_status"] = "partially_matched"

            if t_uri:
                self._add_or_merge_edge(
                    c_node_id,
                    t_uri,
                    relation="partially_matches_skill",
                    relation_type="skill_gap_alignment",
                    tier=tier,
                    graph_relationship=graph_rel,
                    credit_assigned=credit,
                    similarity_score=part.get("similarity_score"),
                    explanation=part.get("explanation", ""),
                )

    def _preserve_esco_skill_relationships(
        self,
        target_skill_uris: set[str],
        candidate_skill_nodes: dict[str, str],
    ) -> None:
        """Preserve broader, narrower, and related edges between ESCO skills in the graph."""
        esco_nodes_in_graph = {
            node for node, data in self.graph.nodes.items()
            if data.get("kind") == "esco_skill" and node in self.esco_graph.graph
        }

        # Check all pairs of ESCO skills in the personalized graph
        for u in esco_nodes_in_graph:
            for v in esco_nodes_in_graph:
                if u == v:
                    continue
                if self.esco_graph.graph.has_edge(u, v):
                    edge_data = self.esco_graph.graph.edges[u, v]
                    rel_names = edge_data.get("relation_names", [edge_data.get("relation")])
                    for rel in rel_names:
                        if rel in ("broader_skill", "narrower_skill", "related"):
                            self._add_or_merge_edge(
                                u,
                                v,
                                relation=rel,
                                relation_type="esco_taxonomy",
                            )

    # ------------------------------------------------------------------
    # Query & Analysis Interface
    # ------------------------------------------------------------------

    def get_summary(self) -> dict[str, Any]:
        """Return quantitative summary metrics of the personalized graph."""
        node_kinds: dict[str, int] = {}
        for _, data in self.graph.nodes(data=True):
            k = data.get("kind", "unknown")
            node_kinds[k] = node_kinds.get(k, 0) + 1

        edge_relations: dict[str, int] = {}
        for _, _, data in self.graph.edges(data=True):
            for rel in data.get("relation_names", [data.get("relation", "unknown")]):
                edge_relations[rel] = edge_relations.get(rel, 0) + 1

        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "node_counts_by_kind": node_kinds,
            "edge_counts_by_relation": edge_relations,
            "overall_skill_coverage_score": self.gap_report.get("overall_skill_coverage_score", 0.0),
            "essential_skill_coverage_score": self.gap_report.get("essential_skill_coverage_score", 0.0),
            "optional_skill_coverage_score": self.gap_report.get("optional_skill_coverage_score"),
        }

    def get_missing_skills(self) -> list[dict[str, Any]]:
        """Return list of missing required skills with attributes."""
        missing: list[dict[str, Any]] = []
        for node, data in self.graph.nodes(data=True):
            if data.get("kind") == "esco_skill" and data.get("gap_status") == "missing":
                missing.append({
                    "uri": node,
                    "label": data.get("label"),
                    "requirement_type": data.get("requirement_type"),
                    "skill_type": data.get("skill_type"),
                })
        return missing

    def get_matched_skills(self) -> list[dict[str, Any]]:
        """Return list of matched skills with match evidence."""
        matched: list[dict[str, Any]] = []
        for u, v, data in self.graph.edges(data=True):
            if "matches_skill" in data.get("relation_names", []):
                matched.append({
                    "candidate_skill_node": u,
                    "target_skill_uri": v,
                    "candidate_skill": self.graph.nodes[u].get("label"),
                    "target_skill": self.graph.nodes[v].get("label"),
                    "tier": data.get("tier"),
                    "credit_assigned": data.get("credit_assigned"),
                    "similarity_score": data.get("similarity_score"),
                    "explanation": data.get("explanation"),
                })
        return matched

    def get_partially_matched_skills(self) -> list[dict[str, Any]]:
        """Return list of partially matched skills with match evidence."""
        partial: list[dict[str, Any]] = []
        for u, v, data in self.graph.edges(data=True):
            if "partially_matches_skill" in data.get("relation_names", []):
                partial.append({
                    "candidate_skill_node": u,
                    "target_skill_uri": v,
                    "candidate_skill": self.graph.nodes[u].get("label"),
                    "target_skill": self.graph.nodes[v].get("label"),
                    "tier": data.get("tier"),
                    "graph_relationship": data.get("graph_relationship"),
                    "credit_assigned": data.get("credit_assigned"),
                    "similarity_score": data.get("similarity_score"),
                    "explanation": data.get("explanation"),
                })
        return partial

    def to_dict(self) -> dict[str, Any]:
        """Serialize personalized graph to dictionary structure suitable for JSON APIs."""
        nodes = []
        for node_id, data in self.graph.nodes(data=True):
            node_dict = {"id": node_id, **data}
            nodes.append(node_dict)

        edges = []
        for u, v, data in self.graph.edges(data=True):
            edge_dict = {"source": u, "target": v, **data}
            edges.append(edge_dict)

        return {
            "summary": self.get_summary(),
            "nodes": nodes,
            "edges": edges,
        }


def build_personalized_graph(
    candidate: CandidateProfile | dict[str, Any],
    target_occupation: str,
    esco_graph: ESCOKnowledgeGraph | None = None,
    gap_report: SkillGapReport | dict[str, Any] | None = None,
) -> PersonalizedKnowledgeGraph:
    """Convenience factory function to build a PersonalizedKnowledgeGraph."""
    return PersonalizedKnowledgeGraph(
        candidate=candidate,
        target_occupation=target_occupation,
        esco_graph=esco_graph,
        gap_report=gap_report,
    )

