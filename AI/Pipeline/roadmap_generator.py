"""Personalized Learning Roadmap Generator (Road2Hire).

Constructs a structured, prioritized 4-phase learning roadmap tailored to
candidate skill gaps identified against canonical ESCO occupation requirements.
"""

from __future__ import annotations

import logging
from typing import Any

from AI.Pipeline.pipeline_schema import LearningRoadmap, RoadmapItem, RoadmapPhase

logger = logging.getLogger(__name__)

ROADMAP_DISCLAIMERS = [
    "This learning roadmap is generated algorithmically from candidate resume evidence against the ESCO occupational framework.",
    "Completion of recommended learning items builds domain competency but does not guarantee employment, interviews, or certified Job Ready status.",
    "Estimated durations are guidelines for deliberate practice and may vary depending on individual background and prior experience.",
    "Suggested activities and projects are illustrative portfolio scenarios; no specific commercial course or provider is endorsed.",
]


class RoadmapGenerator:
    """Generates a structured, prioritized 4-phase learning roadmap from skill gap results."""

    def __init__(self, taxonomy: Any = None) -> None:
        self.taxonomy = taxonomy

    def generate_roadmap(
        self,
        gap_report: dict[str, Any],
        target_occupation_title: str,
        target_occupation_uri: str,
        max_items_per_phase: int = 5,
    ) -> LearningRoadmap:
        """Construct the 4-phase personalized learning roadmap.

        Parameters
        ----------
        gap_report:
            SkillGapReport dictionary produced by `Road2HireModel.detect_skill_gap()`.
        target_occupation_title:
            Resolved title of the target occupation.
        target_occupation_uri:
            ESCO URI of the target occupation.
        max_items_per_phase:
            Maximum recommended learning items per phase to keep learning actionable.

        Returns
        -------
        LearningRoadmap
            Complete structured learning roadmap.
        """
        missing_essential = gap_report.get("missing_essential_skills", [])
        partially_matched = gap_report.get("partially_matched_skills", [])
        missing_optional = gap_report.get("missing_optional_skills", [])

        seen_uris: set[str] = set()
        seen_names: set[str] = set()

        # Phase 1: Foundational Skills & Core Knowledge
        # Group missing essential skills that are classified as 'knowledge' or have broader relationships
        p1_candidates = []
        p2_candidates = []

        for item in missing_essential:
            s_name = item.get("skill_label") or item.get("skill_name") or ""
            s_uri = item.get("skill_uri") or ""
            s_type = item.get("skill_type") or ""

            if not s_name or s_name.casefold() in seen_names:
                continue

            if s_type == "knowledge":
                p1_candidates.append(item)
            else:
                p2_candidates.append(item)

        # If few knowledge items exist, take the first 2-3 essential skills as foundational
        if len(p1_candidates) < 2 and len(p2_candidates) > 3:
            p1_candidates.extend(p2_candidates[:2])
            p2_candidates = p2_candidates[2:]

        # Phase 1 Items
        p1_items: list[RoadmapItem] = []
        for raw in p1_candidates[:max_items_per_phase]:
            s_name = raw.get("skill_label") or raw.get("skill_name") or ""
            s_uri = raw.get("skill_uri") or ""
            seen_names.add(s_name.casefold())
            if s_uri:
                seen_uris.add(s_uri)

            p1_items.append(self._build_roadmap_item(
                skill_name=s_name,
                esco_uri=s_uri,
                status="missing_essential",
                priority="Critical",
                target_occupation=target_occupation_title,
                phase_type="foundational",
            ))

        # Phase 2: Core Technical Competencies (Remaining Missing Essential Skills)
        p2_items: list[RoadmapItem] = []
        for raw in p2_candidates[:max_items_per_phase]:
            s_name = raw.get("skill_label") or raw.get("skill_name") or ""
            s_uri = raw.get("skill_uri") or ""
            if s_name.casefold() in seen_names:
                continue
            seen_names.add(s_name.casefold())
            if s_uri:
                seen_uris.add(s_uri)

            p2_items.append(self._build_roadmap_item(
                skill_name=s_name,
                esco_uri=s_uri,
                status="missing_essential",
                priority="Critical",
                target_occupation=target_occupation_title,
                phase_type="core_technical",
            ))

        # Phase 3: Practical Application & Projects (Partially Matched Skills to Deepen)
        p3_items: list[RoadmapItem] = []
        for raw in partially_matched[:max_items_per_phase]:
            s_name = raw.get("occupation_skill") or raw.get("candidate_skill") or ""
            s_uri = raw.get("skill_uri") or ""
            if not s_name or s_name.casefold() in seen_names:
                continue
            seen_names.add(s_name.casefold())
            if s_uri:
                seen_uris.add(s_uri)

            p3_items.append(self._build_roadmap_item(
                skill_name=s_name,
                esco_uri=s_uri,
                status="partially_matched_essential",
                priority="High",
                target_occupation=target_occupation_title,
                phase_type="practical_deepening",
                sim_score=raw.get("similarity_score", 0.0),
            ))

        # Phase 4: Advanced Specialization & Optional Skills
        p4_items: list[RoadmapItem] = []
        for raw in missing_optional[:max_items_per_phase]:
            s_name = raw.get("skill_label") or raw.get("skill_name") or ""
            s_uri = raw.get("skill_uri") or ""
            if not s_name or s_name.casefold() in seen_names:
                continue
            seen_names.add(s_name.casefold())
            if s_uri:
                seen_uris.add(s_uri)

            p4_items.append(self._build_roadmap_item(
                skill_name=s_name,
                esco_uri=s_uri,
                status="missing_optional",
                priority="Medium",
                target_occupation=target_occupation_title,
                phase_type="advanced_optional",
            ))

        # Assemble Phases
        phases = [
            RoadmapPhase(
                phase_number=1,
                phase_name="Phase 1: Foundational Competencies & Core Knowledge",
                description=(
                    "Establish essential theoretical principles, standards, and conceptual foundations "
                    f"required for the {target_occupation_title} occupation."
                ),
                estimated_weeks="2 – 4 Weeks",
                items=p1_items,
            ),
            RoadmapPhase(
                phase_number=2,
                phase_name="Phase 2: Core Technical Implementation Skills",
                description=(
                    "Acquire practical engineering tools, workflows, and core techniques directly "
                    f"mandated by {target_occupation_title} industry requisitions."
                ),
                estimated_weeks="4 – 8 Weeks",
                items=p2_items,
            ),
            RoadmapPhase(
                phase_number=3,
                phase_name="Phase 3: Applied Systems & Portfolio Project Execution",
                description=(
                    "Bridge partially demonstrated skills into verified hands-on production capability "
                    "through end-to-end applied projects."
                ),
                estimated_weeks="4 – 6 Weeks",
                items=p3_items,
            ),
            RoadmapPhase(
                phase_number=4,
                phase_name="Phase 4: Advanced Specialization & Optional Capabilities",
                description=(
                    "Expand professional differentiation through specialized optional technologies "
                    "and enterprise architecture patterns."
                ),
                estimated_weeks="2 – 4 Weeks",
                items=p4_items,
            ),
        ]

        total_skills = sum(len(p.items) for p in phases)
        estimated_weeks = (
            "0 Weeks (Candidate profile fulfills all target occupation requirements)"
            if total_skills == 0
            else "12 – 22 Weeks"
        )

        return LearningRoadmap(
            target_occupation_title=target_occupation_title,
            target_occupation_uri=target_occupation_uri,
            total_roadmap_skills=total_skills,
            total_estimated_weeks=estimated_weeks,
            phases=phases,
            disclaimers=ROADMAP_DISCLAIMERS,
        )

    def _build_roadmap_item(
        self,
        skill_name: str,
        esco_uri: str | None,
        status: str,
        priority: str,
        target_occupation: str,
        phase_type: str,
        sim_score: float = 0.0,
    ) -> RoadmapItem:
        """Construct detailed learning metadata for a single skill item."""
        prerequisites: list[str] = []
        if self.taxonomy and esco_uri:
            try:
                broader = self.taxonomy.get_broader_skills(esco_uri)
                prerequisites = [b.preferred_label for b in broader[:2]]
            except Exception:
                prerequisites = []

        if phase_type == "foundational":
            duration = "1 – 2 Weeks"
            rationale = (
                f"Essential prerequisite knowledge for '{target_occupation}' to ensure sound architectural "
                "reasoning and standard compliance."
            )
            outcome = f"Explain core concepts, lifecycle principles, and standard methodologies for {skill_name}."
            activities = [
                f"Study standard technical documentation, RFCs, and architecture patterns for {skill_name}.",
                f"Diagram system architecture and data flows reflecting {skill_name} best practices.",
            ]
            project = (
                f"Author a design document or comprehensive technical specification integrating {skill_name}."
            )
            criteria = f"Pass conceptual self-assessments and articulate operational trade-offs for {skill_name}."

        elif phase_type == "core_technical":
            duration = "2 – 3 Weeks"
            rationale = (
                f"Mandatory technical skill for '{target_occupation}'. Industry requisitions demand "
                "hands-on implementation fluency."
            )
            outcome = f"Build, test, and deploy functional modules implementing {skill_name} in production."
            activities = [
                f"Implement hands-on laboratory exercises and pipelines utilizing {skill_name}.",
                f"Write unit and integration test suites validating edge-case behavior for {skill_name}.",
            ]
            project = (
                f"Develop an end-to-end functional pipeline or service incorporating {skill_name} with automated CI/CD."
            )
            criteria = f"Deliver documented, working code with >80% test coverage implementing {skill_name}."

        elif phase_type == "practical_deepening":
            duration = "1 – 2 Weeks"
            rationale = (
                f"Candidate exhibits related background ({sim_score:.0%} similarity), but direct "
                f"canonical evidence for '{skill_name}' is incomplete."
            )
            outcome = f"Demonstrate production-grade application of {skill_name} bridging previous experience."
            activities = [
                f"Refactor existing code or projects to use standardized {skill_name} interfaces.",
                f"Profile performance bottlenecks and apply optimization techniques for {skill_name}.",
            ]
            project = (
                f"Integrate {skill_name} into an existing portfolio project and document performance metrics."
            )
            criteria = "Demonstrate public code repository commit or portfolio case study showcasing practical mastery."

        else:  # advanced_optional
            duration = "1 – 2 Weeks"
            rationale = (
                f"Optional specialization skill for '{target_occupation}' that distinguishes high-tier candidates."
            )
            outcome = f"Integrate advanced patterns, cloud tooling, or extensions for {skill_name}."
            activities = [
                f"Explore enterprise configurations, scalability patterns, and extensions of {skill_name}.",
                f"Review open-source production implementations utilizing {skill_name}.",
            ]
            project = (
                f"Implement a proof-of-concept demonstrating advanced capabilities of {skill_name}."
            )
            criteria = "Successfully execute a proof-of-concept and document enterprise deployment patterns."

        resource_categories = [
            {
                "category": "Official Documentation & Standards",
                "recommended_search": f"{skill_name} official documentation architecture guide",
            },
            {
                "category": "Hands-on Practice & Sandboxes",
                "recommended_search": f"{skill_name} tutorial open source project examples",
            },
            {
                "category": "Industry Best Practices",
                "recommended_search": f"{skill_name} production best practices enterprise deployment",
            },
        ]

        return RoadmapItem(
            skill_name=skill_name,
            esco_uri=esco_uri or None,
            current_status=status,  # type: ignore
            priority=priority,      # type: ignore
            importance_rationale=rationale,
            learning_outcome=outcome,
            suggested_activities=activities,
            practical_project=project,
            estimated_duration_weeks=duration,
            prerequisites=prerequisites,
            completion_criteria=criteria,
            resource_categories=resource_categories,
        )
