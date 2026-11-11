
"""Map normalized Road2Hire skills to curated ESCO concepts."""

import csv
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ESCO_MAPPING_PATH = (
    PROJECT_ROOT
    / "Datasets"
    / "Skill_Taxonomy"
    / "Processed"
    / "Road2Hire_ESCO_Mapping.csv"
)


def load_esco_mapping(
    mapping_path: str | Path = ESCO_MAPPING_PATH,
) -> dict[str, dict[str, str]]:
    """Load curated mappings, including entries without an ESCO match."""
    path = Path(mapping_path)

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        required_columns = {
            "Road2Hire_Skill",
            "ESCO_Skill_Id",
            "ESCO_Skill_Name",
            "Mapping_Type",
        }

        if not required_columns.issubset(reader.fieldnames or []):
            raise ValueError("ESCO mapping CSV is missing required columns.")

        mappings = {}

        for row in reader:
            skill_name = (row["Road2Hire_Skill"] or "").strip()
            if not skill_name:
                continue

            key = skill_name.casefold()
            if key in mappings:
                raise ValueError(f"Duplicate mapping for skill: {skill_name}")

            mappings[key] = {
                "Road2Hire_Skill": skill_name,
                "ESCO_Skill_Id": (row["ESCO_Skill_Id"] or "").strip(),
                "ESCO_Skill_Name": (row["ESCO_Skill_Name"] or "").strip(),
                "Mapping_Type": (row["Mapping_Type"] or "").strip(),
            }

    return mappings


def map_skills_to_esco(
    extracted_skills: list[dict[str, Any]],
    mapping_path: str | Path = ESCO_MAPPING_PATH,
) -> list[dict[str, Any]]:
    """Enrich extracted skills with curated ESCO mapping information."""
    mappings = load_esco_mapping(mapping_path)
    results = []

    for item in extracted_skills:
        if not isinstance(item, dict):
            continue

        skill_name = item.get("skill")
        if not isinstance(skill_name, str) or not skill_name.strip():
            continue

        mapping = mappings.get(skill_name.strip().casefold())

        results.append({
            **item,
            "ESCO_Skill_Id": mapping["ESCO_Skill_Id"] if mapping else "",
            "ESCO_Skill_Name": mapping["ESCO_Skill_Name"] if mapping else "",
            "ESCO_Mapping_Type": (
                mapping["Mapping_Type"] if mapping else "unmapped"
            ),
        })

    return results


def map_skills_to_complete_esco(
    extracted_skills: list[dict],
    taxonomy=None,
) -> list[dict]:
    """Enrich extracted skills using the complete ESCO taxonomy."""
    from AI.Skill_Extraction.esco_taxonomy import get_esco_taxonomy

    tax = taxonomy if taxonomy is not None else get_esco_taxonomy()
    results = []

    for item in extracted_skills:
        if not isinstance(item, dict):
            continue

        skill_name = item.get("skill")
        if not isinstance(skill_name, str) or not skill_name.strip():
            continue

        skill_name = skill_name.strip()
        skill_obj = tax.find_skill(skill_name)

        if skill_obj:
            preferred_match = tax.get_skill_by_preferred_label(skill_name)
            is_preferred = (
                preferred_match is not None
                and preferred_match.concept_uri == skill_obj.concept_uri
            )

            results.append({
                **item,
                "ESCO_Skill_Id": skill_obj.concept_uri,
                "ESCO_Skill_Name": skill_obj.preferred_label,
                "ESCO_Skill_Type": skill_obj.skill_type,
                "ESCO_Reuse_Level": skill_obj.reuse_level,
                "ESCO_Mapping_Type": (
                    "exact_preferred" if is_preferred
                    else "alternative_label"
                ),
            })
        else:
            results.append({
                **item,
                "ESCO_Skill_Id": "",
                "ESCO_Skill_Name": "",
                "ESCO_Skill_Type": "",
                "ESCO_Reuse_Level": "",
                "ESCO_Mapping_Type": "unmapped",
            })

    return results
