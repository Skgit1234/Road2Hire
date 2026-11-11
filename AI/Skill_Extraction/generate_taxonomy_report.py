"""Generate a comprehensive ESCO Taxonomy loading and data integrity report.

Outputs:
- AI/Skill_Extraction/esco_loading_report.json
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from AI.Skill_Extraction.esco_taxonomy import get_esco_taxonomy


def main() -> None:
    print("Loading complete ESCO taxonomy...")
    taxonomy = get_esco_taxonomy(force_reload=True)
    report = taxonomy.get_report()

    report_dict = report.to_dict()

    # Add extra context & summary
    report_dict["project"] = "Road2Hire"
    report_dict["phase"] = "Phase 1: Complete ESCO Taxonomy Integration"
    report_dict["esco_raw_dir"] = str(taxonomy.raw_dir.relative_to(PROJECT_ROOT))

    # Add sample loaded skills
    sample_skills = []
    for skill_name in ["Python (computer programming)", "machine learning", "SQL", "data analysis"]:
        skill = taxonomy.find_skill(skill_name)
        if skill:
            sample_skills.append({
                "query": skill_name,
                "preferred_label": skill.preferred_label,
                "uri": skill.concept_uri,
                "skill_type": skill.skill_type,
                "reuse_level": skill.reuse_level,
                "alt_labels_count": len(skill.alt_labels),
                "has_description": bool(skill.description),
            })
    report_dict["sample_verified_skills"] = sample_skills

    output_file = PROJECT_ROOT / "AI" / "Skill_Extraction" / "esco_loading_report.json"
    with output_file.open("w", encoding="utf-8") as fp:
        json.dump(report_dict, fp, indent=2)

    print(f"Report generated successfully: {output_file}")
    print("\n--- Summary ---")
    print(f"Raw skill rows: {report.skills_raw_count}")
    print(f"Unique skill URIs: {report.skills_unique_count}")
    print(f"Duplicate skill URIs: {report.duplicate_skill_uris_count}")
    print(f"Total alternative labels: {report.alt_labels_total_count}")
    print(f"Skills with description: {report.skills_with_description_count}")
    print(f"Missing fields: {report.missing_fields_summary}")
    print(f"Skill-skill relations: {report.skill_skill_relations_count}")
    print(f"Broader relations: {report.broader_relations_total}")
    print(f"Unique occupations: {report.occupations_unique_count}")
    print(f"Occupation-skill relations: {report.occupation_skill_relations_total}")
    print(f"Load duration: {report.load_duration_seconds}s")
    print(f"Loading errors: {report.loading_errors}")


if __name__ == "__main__":
    main()
