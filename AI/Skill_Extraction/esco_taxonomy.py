"""Complete ESCO Skill Taxonomy loader, indexer, and query interface.

Loads the full official ESCO taxonomy from raw CSV files, providing:
- Fast indexed lookups by URI, preferred label, and alternative labels.
- Skill hierarchy (broader/narrower) and related-skill relationships.
- Occupation-to-skill relationships for career readiness and gap analysis.
- Thorough validation and automated loading report generation.
- In-memory caching for high-performance reuse.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
import re
import time
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ESCO_DIR = PROJECT_ROOT / "Datasets" / "Skill_Taxonomy" / "Raw" / "ESCO"


@dataclass(slots=True)
class ESCOSkill:
    """Represents an official ESCO skill or knowledge concept."""

    concept_uri: str
    preferred_label: str
    skill_type: str
    reuse_level: str
    alt_labels: list[str] = field(default_factory=list)
    description: str = ""
    status: str = ""
    modified_date: str = ""
    scope_note: str = ""
    definition: str = ""
    in_scheme: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert skill to dictionary representation."""
        return asdict(self)


@dataclass(slots=True)
class ESCOSkillGroup:
    """Represents an ESCO skill group or ISCED category."""

    concept_uri: str
    preferred_label: str
    code: str = ""
    description: str = ""
    scope_note: str = ""
    status: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ESCOOccupation:
    """Represents an ESCO occupation concept."""

    concept_uri: str
    preferred_label: str
    code: str = ""
    isco_group: str = ""
    description: str = ""
    alt_labels: list[str] = field(default_factory=list)
    status: str = ""
    modified_date: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ESCOOccupationSkillRelation:
    """Represents an association between an occupation and an ESCO skill."""

    occupation_uri: str
    occupation_label: str
    relation_type: str  # 'essential' or 'optional'
    skill_type: str     # 'skill/competence' or 'knowledge'
    skill_uri: str
    skill_label: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ESCOTaxonomyLoadingReport:
    """Detailed taxonomy loading, deduplication, and integrity report."""

    timestamp: str = ""
    load_duration_seconds: float = 0.0
    skills_raw_count: int = 0
    skills_unique_count: int = 0
    duplicate_skill_uris_count: int = 0
    duplicate_skill_uris: list[str] = field(default_factory=list)
    alt_labels_total_count: int = 0
    skills_with_alt_labels_count: int = 0
    skills_with_description_count: int = 0
    missing_fields_summary: dict[str, int] = field(default_factory=dict)
    skill_types_distribution: dict[str, int] = field(default_factory=dict)
    reuse_levels_distribution: dict[str, int] = field(default_factory=dict)
    skill_skill_relations_count: int = 0
    skill_skill_relation_types: dict[str, int] = field(default_factory=dict)
    broader_relations_total: int = 0
    broader_skill_to_skill_count: int = 0
    skill_to_group_count: int = 0
    group_to_group_count: int = 0
    skill_groups_count: int = 0
    occupations_raw_count: int = 0
    occupations_unique_count: int = 0
    duplicate_occupation_uris: list[str] = field(default_factory=list)
    occupation_skill_relations_total: int = 0
    essential_occupation_skill_relations_count: int = 0
    optional_occupation_skill_relations_count: int = 0
    unique_occupations_in_relations: int = 0
    unique_skills_in_relations: int = 0
    loading_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_skill_label(text: str) -> str:
    """Normalize label for case-insensitive and whitespace-insensitive matching."""
    return " ".join(text.strip().split()).casefold()


class ESCOTaxonomy:
    """In-memory indexer for the complete ESCO taxonomy dataset."""

    def __init__(self, raw_dir: Path | str = DEFAULT_ESCO_DIR) -> None:
        self.raw_dir = Path(raw_dir)
        self.skills: dict[str, ESCOSkill] = {}
        self.skills_by_preferred_label: dict[str, ESCOSkill] = {}
        self.skills_by_alt_label: dict[str, list[ESCOSkill]] = {}
        self.skills_by_type: dict[str, list[ESCOSkill]] = {}
        self.skills_by_reuse_level: dict[str, list[ESCOSkill]] = {}

        self.skill_groups: dict[str, ESCOSkillGroup] = {}
        self.occupations: dict[str, ESCOOccupation] = {}
        self.occupations_by_label: dict[str, ESCOOccupation] = {}
        self.occupations_by_alt_label: dict[str, list[ESCOOccupation]] = {}

        # Skill-skill relations (original -> related, and incoming)
        self.skill_relations: dict[str, list[dict[str, str]]] = {}
        self.incoming_skill_relations: dict[str, list[dict[str, str]]] = {}

        # Broader/narrower relations between skills
        self.broader_skills: dict[str, list[str]] = {}
        self.narrower_skills: dict[str, list[str]] = {}
        # Skill to SkillGroup relations
        self.skill_to_groups: dict[str, list[str]] = {}
        self.group_to_skills: dict[str, list[str]] = {}

        # Occupation-skill relations
        self.occupation_to_skills: dict[str, list[dict[str, str]]] = {}
        self.skill_to_occupations: dict[str, list[dict[str, str]]] = {}

        self.report = ESCOTaxonomyLoadingReport()
        self._load()

    def _load(self) -> None:
        """Load and index all ESCO CSV datasets with verification."""
        start_time = time.perf_counter()
        self.report.timestamp = datetime.now().isoformat()

        if not self.raw_dir.is_dir():
            error_msg = f"ESCO directory does not exist: {self.raw_dir}"
            self.report.loading_errors.append(error_msg)
            raise FileNotFoundError(error_msg)

        # 1. Load skill groups
        self._load_skill_groups()

        # 2. Load skills
        self._load_skills()

        # 3. Load skill-skill relations
        self._load_skill_skill_relations()

        # 4. Load broader relations
        self._load_broader_relations()

        # 5. Load occupations
        self._load_occupations()

        # 6. Load occupation-skill relations
        self._load_occupation_skill_relations()

        self.report.load_duration_seconds = round(
            time.perf_counter() - start_time, 4
        )

    def _load_skill_groups(self) -> None:
        path = self.raw_dir / "skillGroups_en.csv"
        if not path.is_file():
            self.report.loading_errors.append(f"Missing file: {path.name}")
            return

        with path.open("r", encoding="utf-8-sig", newline="") as fp:
            reader = csv.DictReader(fp)
            for row in reader:
                uri = (row.get("conceptUri") or "").strip()
                if not uri:
                    continue
                label = (row.get("preferredLabel") or "").strip()
                group = ESCOSkillGroup(
                    concept_uri=uri,
                    preferred_label=label,
                    code=(row.get("code") or "").strip(),
                    description=(row.get("description") or "").strip(),
                    scope_note=(row.get("scopeNote") or "").strip(),
                    status=(row.get("status") or "").strip(),
                )
                self.skill_groups[uri] = group

        self.report.skill_groups_count = len(self.skill_groups)

    def _load_skills(self) -> None:
        path = self.raw_dir / "skills_en.csv"
        if not path.is_file():
            raise FileNotFoundError(f"Missing required skills file: {path}")

        raw_rows_count = 0
        duplicate_uris: dict[str, list[dict[str, str]]] = {}
        missing_fields = {
            "conceptUri": 0,
            "preferredLabel": 0,
            "description": 0,
            "skillType": 0,
            "reuseLevel": 0,
        }

        skill_records: dict[str, dict[str, Any]] = {}

        with path.open("r", encoding="utf-8-sig", newline="") as fp:
            reader = csv.DictReader(fp)
            for row in reader:
                raw_rows_count += 1
                uri = (row.get("conceptUri") or "").strip()
                if not uri:
                    missing_fields["conceptUri"] += 1
                    continue

                pref_label = (row.get("preferredLabel") or "").strip()
                if not pref_label:
                    missing_fields["preferredLabel"] += 1

                description = (row.get("description") or "").strip()
                if not description:
                    missing_fields["description"] += 1

                skill_type = (row.get("skillType") or "").strip()
                if not skill_type:
                    missing_fields["skillType"] += 1

                reuse_level = (row.get("reuseLevel") or "").strip()
                if not reuse_level:
                    missing_fields["reuseLevel"] += 1

                if uri in skill_records:
                    if uri not in duplicate_uris:
                        duplicate_uris[uri] = [skill_records[uri]["row"]]
                    duplicate_uris[uri].append(row)
                    # Deduplicate by choosing the row with latest modifiedDate
                    existing_mod = skill_records[uri]["row"].get("modifiedDate", "")
                    current_mod = row.get("modifiedDate", "")
                    if current_mod > existing_mod:
                        skill_records[uri] = {"row": row}
                else:
                    skill_records[uri] = {"row": row}

        self.report.skills_raw_count = raw_rows_count
        self.report.skills_unique_count = len(skill_records)
        self.report.duplicate_skill_uris_count = len(duplicate_uris)
        self.report.duplicate_skill_uris = sorted(duplicate_uris.keys())
        self.report.missing_fields_summary = missing_fields

        total_alt_labels = 0
        skills_with_alt_labels = 0
        skills_with_desc = 0
        type_counts: dict[str, int] = {}
        reuse_counts: dict[str, int] = {}

        for uri, item in skill_records.items():
            row = item["row"]
            pref_label = (row.get("preferredLabel") or "").strip()
            skill_type = (row.get("skillType") or "").strip()
            reuse_level = (row.get("reuseLevel") or "").strip()
            description = (row.get("description") or "").strip()

            raw_alts = row.get("altLabels") or ""
            # ESCO altLabels are newline-delimited in skills_en.csv
            alt_list = [
                line.strip()
                for line in raw_alts.replace("\r\n", "\n").split("\n")
                if line.strip()
            ]

            if alt_list:
                skills_with_alt_labels += 1
                total_alt_labels += len(alt_list)

            if description:
                skills_with_desc += 1

            type_counts[skill_type or "unspecified"] = (
                type_counts.get(skill_type or "unspecified", 0) + 1
            )
            reuse_counts[reuse_level or "unspecified"] = (
                reuse_counts.get(reuse_level or "unspecified", 0) + 1
            )

            skill = ESCOSkill(
                concept_uri=uri,
                preferred_label=pref_label,
                skill_type=skill_type,
                reuse_level=reuse_level,
                alt_labels=alt_list,
                description=description,
                status=(row.get("status") or "").strip(),
                modified_date=(row.get("modifiedDate") or "").strip(),
                scope_note=(row.get("scopeNote") or "").strip(),
                definition=(row.get("definition") or "").strip(),
                in_scheme=(row.get("inScheme") or "").strip(),
            )

            self.skills[uri] = skill

            # Index by preferred label
            pref_key = normalize_skill_label(pref_label)
            if pref_key:
                self.skills_by_preferred_label[pref_key] = skill

            # Index by alternative labels
            for alt in alt_list:
                alt_key = normalize_skill_label(alt)
                if alt_key:
                    if alt_key not in self.skills_by_alt_label:
                        self.skills_by_alt_label[alt_key] = []
                    self.skills_by_alt_label[alt_key].append(skill)

            # Index by skill type
            if skill_type not in self.skills_by_type:
                self.skills_by_type[skill_type] = []
            self.skills_by_type[skill_type].append(skill)

            # Index by reuse level
            if reuse_level not in self.skills_by_reuse_level:
                self.skills_by_reuse_level[reuse_level] = []
            self.skills_by_reuse_level[reuse_level].append(skill)

        self.report.alt_labels_total_count = total_alt_labels
        self.report.skills_with_alt_labels_count = skills_with_alt_labels
        self.report.skills_with_description_count = skills_with_desc
        self.report.skill_types_distribution = type_counts
        self.report.reuse_levels_distribution = reuse_counts

    def _load_skill_skill_relations(self) -> None:
        path = self.raw_dir / "skillSkillRelations_en.csv"
        if not path.is_file():
            self.report.loading_errors.append(f"Missing file: {path.name}")
            return

        relation_count = 0
        type_counts: dict[str, int] = {}

        with path.open("r", encoding="utf-8-sig", newline="") as fp:
            reader = csv.DictReader(fp)
            for row in reader:
                orig_uri = (row.get("originalSkillUri") or "").strip()
                rel_uri = (row.get("relatedSkillUri") or "").strip()
                rel_type = (row.get("relationType") or "related").strip()

                if not orig_uri or not rel_uri:
                    continue

                relation_count += 1
                type_counts[rel_type] = type_counts.get(rel_type, 0) + 1

                if orig_uri not in self.skill_relations:
                    self.skill_relations[orig_uri] = []
                self.skill_relations[orig_uri].append({
                    "related_uri": rel_uri,
                    "relation_type": rel_type,
                    "related_skill_type": (row.get("relatedSkillType") or "").strip(),
                    "direction": "outgoing",
                })

                if rel_uri not in self.incoming_skill_relations:
                    self.incoming_skill_relations[rel_uri] = []
                self.incoming_skill_relations[rel_uri].append({
                    "related_uri": orig_uri,
                    "relation_type": rel_type,
                    "related_skill_type": (row.get("originalSkillType") or "").strip(),
                    "direction": "incoming",
                })

        self.report.skill_skill_relations_count = relation_count
        self.report.skill_skill_relation_types = type_counts

    def _load_broader_relations(self) -> None:
        path = self.raw_dir / "broaderRelationsSkillPillar_en.csv"
        if not path.is_file():
            self.report.loading_errors.append(f"Missing file: {path.name}")
            return

        total_rows = 0
        skill_to_skill = 0
        skill_to_group = 0
        group_to_group = 0

        with path.open("r", encoding="utf-8-sig", newline="") as fp:
            reader = csv.DictReader(fp)
            for row in reader:
                total_rows += 1
                c_type = (row.get("conceptType") or "").strip()
                c_uri = (row.get("conceptUri") or "").strip()
                b_type = (row.get("broaderType") or "").strip()
                b_uri = (row.get("broaderUri") or "").strip()

                if not c_uri or not b_uri:
                    continue

                if c_type == "KnowledgeSkillCompetence" and b_type == "KnowledgeSkillCompetence":
                    skill_to_skill += 1
                    # c_uri has broader skill b_uri
                    if c_uri not in self.broader_skills:
                        self.broader_skills[c_uri] = []
                    self.broader_skills[c_uri].append(b_uri)

                    # b_uri has narrower skill c_uri
                    if b_uri not in self.narrower_skills:
                        self.narrower_skills[b_uri] = []
                    self.narrower_skills[b_uri].append(c_uri)

                elif c_type == "KnowledgeSkillCompetence" and b_type == "SkillGroup":
                    skill_to_group += 1
                    if c_uri not in self.skill_to_groups:
                        self.skill_to_groups[c_uri] = []
                    self.skill_to_groups[c_uri].append(b_uri)

                    if b_uri not in self.group_to_skills:
                        self.group_to_skills[b_uri] = []
                    self.group_to_skills[b_uri].append(c_uri)

                elif c_type == "SkillGroup" and b_type == "SkillGroup":
                    group_to_group += 1

        self.report.broader_relations_total = total_rows
        self.report.broader_skill_to_skill_count = skill_to_skill
        self.report.skill_to_group_count = skill_to_group
        self.report.group_to_group_count = group_to_group

    def _load_occupations(self) -> None:
        path = self.raw_dir / "occupations_en.csv"
        if not path.is_file():
            self.report.loading_errors.append(f"Missing file: {path.name}")
            return

        raw_count = 0
        occ_records: dict[str, dict[str, str]] = {}
        dups = []

        with path.open("r", encoding="utf-8-sig", newline="") as fp:
            reader = csv.DictReader(fp)
            for row in reader:
                raw_count += 1
                uri = (row.get("conceptUri") or "").strip()
                if not uri:
                    continue

                if uri in occ_records:
                    dups.append(uri)
                    # keep latest
                    if row.get("modifiedDate", "") > occ_records[uri].get("modifiedDate", ""):
                        occ_records[uri] = row
                else:
                    occ_records[uri] = row

        self.report.occupations_raw_count = raw_count
        self.report.occupations_unique_count = len(occ_records)
        self.report.duplicate_occupation_uris = sorted(set(dups))

        for uri, row in occ_records.items():
            label = (row.get("preferredLabel") or "").strip()
            alts = [
                line.strip()
                for line in (row.get("altLabels") or "").replace("\r\n", "\n").split("\n")
                if line.strip()
            ]
            occ = ESCOOccupation(
                concept_uri=uri,
                preferred_label=label,
                code=(row.get("code") or "").strip(),
                isco_group=(row.get("iscoGroup") or "").strip(),
                description=(row.get("description") or "").strip(),
                alt_labels=alts,
                status=(row.get("status") or "").strip(),
                modified_date=(row.get("modifiedDate") or "").strip(),
            )
            self.occupations[uri] = occ
            if label:
                self.occupations_by_label[normalize_skill_label(label)] = occ

            for alt in alts:
                alt_key = normalize_skill_label(alt)
                if alt_key:
                    if alt_key not in self.occupations_by_alt_label:
                        self.occupations_by_alt_label[alt_key] = []
                    self.occupations_by_alt_label[alt_key].append(occ)

    def _load_occupation_skill_relations(self) -> None:
        path = self.raw_dir / "occupationSkillRelations_en.csv"
        if not path.is_file():
            self.report.loading_errors.append(f"Missing file: {path.name}")
            return

        total_relations = 0
        essential_count = 0
        optional_count = 0
        seen_occs = set()
        seen_skills = set()

        with path.open("r", encoding="utf-8-sig", newline="") as fp:
            reader = csv.DictReader(fp)
            for row in reader:
                occ_uri = (row.get("occupationUri") or "").strip()
                skill_uri = (row.get("skillUri") or "").strip()
                rel_type = (row.get("relationType") or "").strip()

                if not occ_uri or not skill_uri:
                    continue

                total_relations += 1
                seen_occs.add(occ_uri)
                seen_skills.add(skill_uri)

                if rel_type == "essential":
                    essential_count += 1
                elif rel_type == "optional":
                    optional_count += 1

                occ_label = (row.get("occupationLabel") or "").strip()
                skill_label = (row.get("skillLabel") or "").strip()
                skill_type = (row.get("skillType") or "").strip()

                if occ_uri not in self.occupation_to_skills:
                    self.occupation_to_skills[occ_uri] = []
                self.occupation_to_skills[occ_uri].append({
                    "skill_uri": skill_uri,
                    "skill_label": skill_label,
                    "relation_type": rel_type,
                    "skill_type": skill_type,
                })

                if skill_uri not in self.skill_to_occupations:
                    self.skill_to_occupations[skill_uri] = []
                self.skill_to_occupations[skill_uri].append({
                    "occupation_uri": occ_uri,
                    "occupation_label": occ_label,
                    "relation_type": rel_type,
                })

        self.report.occupation_skill_relations_total = total_relations
        self.report.essential_occupation_skill_relations_count = essential_count
        self.report.optional_occupation_skill_relations_count = optional_count
        self.report.unique_occupations_in_relations = len(seen_occs)
        self.report.unique_skills_in_relations = len(seen_skills)

    # -------------------------------------------------------------------------
    # Query & Retrieval Interface
    # -------------------------------------------------------------------------

    def get_skill_by_uri(self, uri: str) -> ESCOSkill | None:
        """Lookup skill by exact ESCO concept URI."""
        return self.skills.get(uri.strip())

    def get_skill_by_preferred_label(self, label: str) -> ESCOSkill | None:
        """Lookup skill by preferred label (case-insensitive)."""
        return self.skills_by_preferred_label.get(normalize_skill_label(label))

    def find_skill(
        self,
        query: str,
        match_alt_labels: bool = True,
    ) -> ESCOSkill | None:
        """
        Find an ESCO skill matching a name or alias.
        1. Checks preferred label exact match (normalized).
        2. If not found and match_alt_labels is True, checks altLabels.
        """
        if not isinstance(query, str) or not query.strip():
            return None

        key = normalize_skill_label(query)

        # 1. Preferred label exact match
        if key in self.skills_by_preferred_label:
            return self.skills_by_preferred_label[key]

        # 2. Alternative label match
        if match_alt_labels and key in self.skills_by_alt_label:
            matches = self.skills_by_alt_label[key]
            if matches:
                return matches[0]

        return None

    def find_all_skills(self, query: str) -> list[ESCOSkill]:
        """Find all skills matching a query across preferred labels and alt labels."""
        if not isinstance(query, str) or not query.strip():
            return []

        key = normalize_skill_label(query)
        results: list[ESCOSkill] = []
        seen = set()

        if key in self.skills_by_preferred_label:
            skill = self.skills_by_preferred_label[key]
            results.append(skill)
            seen.add(skill.concept_uri)

        for match in self.skills_by_alt_label.get(key, []):
            if match.concept_uri not in seen:
                results.append(match)
                seen.add(match.concept_uri)

        return results

    def find_occupation(
        self,
        query: str,
        match_alt_labels: bool = True,
    ) -> ESCOOccupation | None:
        """Find an ESCO occupation matching a URI, preferred label, or alias."""
        if not isinstance(query, str) or not query.strip():
            return None

        cleaned = query.strip()
        if cleaned in self.occupations:
            return self.occupations[cleaned]

        key = normalize_skill_label(cleaned)
        if key in self.occupations_by_label:
            return self.occupations_by_label[key]

        if match_alt_labels and key in self.occupations_by_alt_label:
            matches = self.occupations_by_alt_label[key]
            if matches:
                return matches[0]

        return None

    def get_vocabulary(self, include_alt_labels: bool = False) -> list[str]:
        """Return the complete available ESCO skill vocabulary list."""
        labels = [skill.preferred_label for skill in self.skills.values()]
        if not include_alt_labels:
            return sorted(labels)

        all_terms = set(labels)
        for skill in self.skills.values():
            all_terms.update(skill.alt_labels)
        return sorted(all_terms)

    def get_related_skills(
        self,
        skill_uri: str,
        relation_type: str | None = None,
        direction: str = "both",
    ) -> list[dict[str, Any]]:
        """Return related skills from ESCO skill-skill relations."""
        cleaned_uri = skill_uri.strip()
        candidates: list[dict[str, str]] = []

        if direction in ("outgoing", "both"):
            candidates.extend(self.skill_relations.get(cleaned_uri, []))
        if direction in ("incoming", "both"):
            candidates.extend(self.incoming_skill_relations.get(cleaned_uri, []))

        results = []
        for rel in candidates:
            if relation_type and rel["relation_type"] != relation_type:
                continue
            target_skill = self.skills.get(rel["related_uri"])
            results.append({
                "skill_uri": rel["related_uri"],
                "preferred_label": target_skill.preferred_label if target_skill else "",
                "relation_type": rel["relation_type"],
                "skill_type": rel.get("related_skill_type", ""),
                "direction": rel.get("direction", "outgoing"),
            })
        return results

    def get_broader_skills(self, skill_uri: str) -> list[ESCOSkill]:
        """Return direct broader skill concepts for a given skill."""
        broader_uris = self.broader_skills.get(skill_uri.strip(), [])
        return [self.skills[u] for u in broader_uris if u in self.skills]

    def get_narrower_skills(self, skill_uri: str) -> list[ESCOSkill]:
        """Return direct narrower skill concepts for a given skill."""
        narrower_uris = self.narrower_skills.get(skill_uri.strip(), [])
        return [self.skills[u] for u in narrower_uris if u in self.skills]

    def get_skill_groups_for_skill(self, skill_uri: str) -> list[ESCOSkillGroup]:
        """Return skill groups that contain this skill."""
        group_uris = self.skill_to_groups.get(skill_uri.strip(), [])
        return [self.skill_groups[u] for u in group_uris if u in self.skill_groups]

    def get_skills_in_group(self, group_uri: str) -> list[ESCOSkill]:
        """Return all skills belonging to a skill group."""
        skill_uris = self.group_to_skills.get(group_uri.strip(), [])
        return [self.skills[u] for u in skill_uris if u in self.skills]

    def get_skills_for_occupation(
        self,
        occupation_uri_or_label: str,
        relation_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return all skills associated with an occupation."""
        cleaned = occupation_uri_or_label.strip()
        occ_uri = cleaned
        if cleaned not in self.occupations:
            occ = self.find_occupation(cleaned)
            if occ:
                occ_uri = occ.concept_uri
            else:
                return []

        relations = self.occupation_to_skills.get(occ_uri, [])
        if not relation_type:
            return relations
        return [r for r in relations if r["relation_type"] == relation_type]

    def get_occupations_for_skill(
        self,
        skill_uri_or_label: str,
        relation_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return all occupations that require or recommend this skill."""
        cleaned = skill_uri_or_label.strip()
        skill_uri = cleaned
        if cleaned not in self.skills:
            skill = self.find_skill(cleaned)
            if skill:
                skill_uri = skill.concept_uri
            else:
                return []

        relations = self.skill_to_occupations.get(skill_uri, [])
        if not relation_type:
            return relations
        return [r for r in relations if r["relation_type"] == relation_type]

    def get_report(self) -> ESCOTaxonomyLoadingReport:
        """Return the loading and validation report."""
        return self.report


# Module singleton cache
_TAXONOMY_CACHE: ESCOTaxonomy | None = None


def get_esco_taxonomy(
    raw_dir: Path | str | None = None,
    force_reload: bool = False,
) -> ESCOTaxonomy:
    """Retrieve the cached ESCO taxonomy instance, or load it once."""
    global _TAXONOMY_CACHE
    if _TAXONOMY_CACHE is None or force_reload or (raw_dir is not None and Path(raw_dir) != _TAXONOMY_CACHE.raw_dir):
        target_dir = Path(raw_dir) if raw_dir is not None else DEFAULT_ESCO_DIR
        _TAXONOMY_CACHE = ESCOTaxonomy(target_dir)
    return _TAXONOMY_CACHE
