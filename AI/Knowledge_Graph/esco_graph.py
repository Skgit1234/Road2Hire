"""NetworkX-powered Knowledge Graph for the complete ESCO taxonomy.

Provides directed graph representation of skills, skill groups, hierarchical
relationships (broader/narrower), and semantic skill-to-skill relationships.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import networkx as nx

from AI.Skill_Extraction.esco_taxonomy import (
    ESCOSkill,
    ESCOTaxonomy,
    get_esco_taxonomy,
    normalize_skill_label,
)


class ESCOKnowledgeGraph:
    """Directed graph representation of ESCO skills and taxonomy relations using NetworkX."""

    def __init__(self, taxonomy: ESCOTaxonomy | None = None) -> None:
        self.taxonomy = taxonomy if taxonomy is not None else get_esco_taxonomy()
        self.graph = nx.DiGraph()
        self._build_graph()

    def _build_graph(self) -> None:
        """Populate NetworkX graph with skill nodes, group nodes, and typed edges."""
        # 1. Add skill group nodes
        for uri, group in self.taxonomy.skill_groups.items():
            self.graph.add_node(
                uri,
                kind="skill_group",
                label=group.preferred_label,
                code=group.code,
            )

        # 2. Add skill nodes
        for uri, skill in self.taxonomy.skills.items():
            self.graph.add_node(
                uri,
                kind="skill",
                label=skill.preferred_label,
                skill_type=skill.skill_type,
                reuse_level=skill.reuse_level,
                alt_labels_count=len(skill.alt_labels),
                has_description=bool(skill.description),
            )

        # 3. Add skill-skill relationship edges (optional, essential)
        for orig_uri, rels in self.taxonomy.skill_relations.items():
            for rel in rels:
                target_uri = rel["related_uri"]
                rel_type = rel["relation_type"]
                # Add edge from orig -> target
                self.graph.add_edge(
                    orig_uri,
                    target_uri,
                    relation="related",
                    relation_type=rel_type,
                    skill_type=rel.get("related_skill_type", ""),
                )

        # 4. Add skill-to-skill broader/narrower edges
        for skill_uri, broader_list in self.taxonomy.broader_skills.items():
            for broader_uri in broader_list:
                self.graph.add_edge(
                    skill_uri,
                    broader_uri,
                    relation="broader_skill",
                    relation_type="hierarchy",
                )
                self.graph.add_edge(
                    broader_uri,
                    skill_uri,
                    relation="narrower_skill",
                    relation_type="hierarchy",
                )

        # 5. Add skill-to-group membership edges
        for skill_uri, groups in self.taxonomy.skill_to_groups.items():
            for group_uri in groups:
                self.graph.add_edge(
                    skill_uri,
                    group_uri,
                    relation="member_of_group",
                    relation_type="category",
                )

    def get_graph(self) -> nx.DiGraph:
        """Return the underlying NetworkX DiGraph instance."""
        return self.graph

    def resolve_skill_uri(self, uri_or_label: str) -> str | None:
        """Resolve a URI or label/alias to a canonical ESCO skill URI."""
        if not isinstance(uri_or_label, str) or not uri_or_label.strip():
            return None

        cleaned = uri_or_label.strip()
        if cleaned in self.graph:
            return cleaned

        skill = self.taxonomy.find_skill(cleaned)
        if skill and skill.concept_uri in self.graph:
            return skill.concept_uri

        return None

    def get_skill_node(self, uri_or_label: str) -> dict[str, Any] | None:
        """Return node attributes for a skill."""
        uri = self.resolve_skill_uri(uri_or_label)
        if not uri or uri not in self.graph:
            return None
        return dict(self.graph.nodes[uri], uri=uri)

    def get_related_skills(
        self,
        uri_or_label: str,
        include_hierarchy: bool = True,
    ) -> list[dict[str, Any]]:
        """Return outgoing and incoming related skills for a given skill."""
        uri = self.resolve_skill_uri(uri_or_label)
        if not uri or uri not in self.graph:
            return []

        neighbors: list[dict[str, Any]] = []

        # Outgoing edges
        for target in self.graph.successors(uri):
            edge_data = self.graph.edges[uri, target]
            rel = edge_data.get("relation")
            if not include_hierarchy and rel in ("broader_skill", "narrower_skill", "member_of_group"):
                continue
            target_data = self.graph.nodes[target]
            neighbors.append({
                "target_uri": target,
                "target_label": target_data.get("label", ""),
                "target_kind": target_data.get("kind", ""),
                "relation": rel,
                "relation_type": edge_data.get("relation_type", ""),
                "direction": "outgoing",
            })

        # Incoming edges
        for source in self.graph.predecessors(uri):
            edge_data = self.graph.edges[source, uri]
            rel = edge_data.get("relation")
            if not include_hierarchy and rel in ("broader_skill", "narrower_skill", "member_of_group"):
                continue
            source_data = self.graph.nodes[source]
            neighbors.append({
                "target_uri": source,
                "target_label": source_data.get("label", ""),
                "target_kind": source_data.get("kind", ""),
                "relation": rel,
                "relation_type": edge_data.get("relation_type", ""),
                "direction": "incoming",
            })

        return neighbors

    def find_path(
        self,
        source_skill: str,
        target_skill: str,
    ) -> list[str] | None:
        """Find the shortest directed path between two skills if one exists."""
        src_uri = self.resolve_skill_uri(source_skill)
        tgt_uri = self.resolve_skill_uri(target_skill)

        if not src_uri or not tgt_uri:
            return None

        try:
            return nx.shortest_path(self.graph, source=src_uri, target=tgt_uri)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def get_subgraph(
        self,
        skill_names_or_uris: list[str],
        include_neighbors: bool = False,
    ) -> nx.DiGraph:
        """Extract a subgraph induced by the given skills (and optionally their 1-hop neighbors)."""
        resolved_nodes: set[str] = set()

        for item in skill_names_or_uris:
            uri = self.resolve_skill_uri(item)
            if uri:
                resolved_nodes.add(uri)
                if include_neighbors:
                    resolved_nodes.update(self.graph.successors(uri))
                    resolved_nodes.update(self.graph.predecessors(uri))

        return self.graph.subgraph(resolved_nodes).copy()

    def match_skills(
        self,
        candidate_skills: list[str],
        target_skills: list[str],
    ) -> dict[str, Any]:
        """
        Match candidate skills against target skills using the full ESCO graph.

        Distinguishes:
        - Direct matches (exact canonical skill match)
        - Related matches (linked via skill-skill or hierarchy relations)
        - Missing target skills
        - Unmatched / unrecognized skills
        """
        resolved_candidate = {}
        unknown_candidate = []
        for name in candidate_skills:
            uri = self.resolve_skill_uri(name)
            if uri:
                resolved_candidate[name] = uri
            else:
                unknown_candidate.append(name)

        resolved_target = {}
        unknown_target = []
        for name in target_skills:
            uri = self.resolve_skill_uri(name)
            if uri:
                resolved_target[name] = uri
            else:
                unknown_target.append(name)

        candidate_uris = set(resolved_candidate.values())
        target_uris = set(resolved_target.values())

        # Direct matches
        direct_matched_uris = candidate_uris & target_uris
        direct_matches = [
            self.taxonomy.skills[u].preferred_label
            for u in direct_matched_uris
            if u in self.taxonomy.skills
        ]

        # Related matches
        related_matches = set()
        relationship_evidence = []

        for cand_name, cand_uri in resolved_candidate.items():
            if cand_uri in target_uris:
                continue

            for tgt_name, tgt_uri in resolved_target.items():
                if self.graph.has_edge(cand_uri, tgt_uri):
                    edge = self.graph.edges[cand_uri, tgt_uri]
                    related_matches.add(cand_name)
                    relationship_evidence.append({
                        "candidate_skill": self.taxonomy.skills[cand_uri].preferred_label,
                        "candidate_uri": cand_uri,
                        "target_skill": self.taxonomy.skills[tgt_uri].preferred_label,
                        "target_uri": tgt_uri,
                        "relationship": edge.get("relation"),
                        "relation_type": edge.get("relation_type"),
                        "direction": "candidate_to_target",
                    })
                elif self.graph.has_edge(tgt_uri, cand_uri):
                    edge = self.graph.edges[tgt_uri, cand_uri]
                    related_matches.add(cand_name)
                    relationship_evidence.append({
                        "candidate_skill": self.taxonomy.skills[cand_uri].preferred_label,
                        "candidate_uri": cand_uri,
                        "target_skill": self.taxonomy.skills[tgt_uri].preferred_label,
                        "target_uri": tgt_uri,
                        "relationship": edge.get("relation"),
                        "relation_type": edge.get("relation_type"),
                        "direction": "target_to_candidate",
                    })

        missing_target = [
            self.taxonomy.skills[u].preferred_label
            for u in (target_uris - candidate_uris)
            if u in self.taxonomy.skills
        ]

        unmatched_candidate = [
            cand_name
            for cand_name, cand_uri in resolved_candidate.items()
            if cand_uri not in target_uris and cand_name not in related_matches
        ]

        return {
            "direct_matches": sorted(direct_matches),
            "related_matches": sorted(related_matches),
            "missing_target_skills": sorted(missing_target),
            "unknown_candidate_skills": unknown_candidate,
            "unknown_target_skills": unknown_target,
            "relationship_evidence": relationship_evidence,
            "unmatched_candidate_skills": sorted(unmatched_candidate),
        }


# Module singleton cache
_GRAPH_CACHE: ESCOKnowledgeGraph | None = None


def get_esco_graph(taxonomy: ESCOTaxonomy | None = None, force_reload: bool = False) -> ESCOKnowledgeGraph:
    """Retrieve the cached ESCO knowledge graph instance."""
    global _GRAPH_CACHE
    if _GRAPH_CACHE is None or force_reload:
        _GRAPH_CACHE = ESCOKnowledgeGraph(taxonomy)
    return _GRAPH_CACHE

