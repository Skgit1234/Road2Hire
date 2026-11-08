"""Build the ESCO skill-to-occupation mapping CSV."""

import csv
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ESCO_DIR = PROJECT_ROOT / "Datasets" / "Skill_Taxonomy" / "Raw" / "ESCO"
OUTPUT_FILE = (
    PROJECT_ROOT
    / "Datasets"
    / "ESCO_ONET"
    / "Mappings"
    / "ESCO_Skill_Mapping.csv"
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def main() -> None:
    skills = read_csv(ESCO_DIR / "skills_en.csv")
    relationships = read_csv(ESCO_DIR / "occupationSkillRelations_en.csv")
    occupations = read_csv(ESCO_DIR / "occupations_en.csv")

    occupation_labels = {
        row["conceptUri"]: row.get("preferredLabel", "")
        for row in occupations
        if row.get("conceptUri")
    }

    relationships_by_skill: dict[str, list[dict[str, str]]] = defaultdict(list)

    for relationship in relationships:
        skill_uri = relationship.get("skillUri", "").strip()
        if skill_uri:
            relationships_by_skill[skill_uri].append(relationship)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    output_rows = 0
    skills_with_relationships = 0

    with OUTPUT_FILE.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "ESCO_Skill_Id",
                "Skill_Name",
                "Skill_Category",
                "Occupation",
                "Importance",
            ],
        )
        writer.writeheader()

        for skill in skills:
            skill_uri = skill.get("conceptUri", "").strip()
            skill_name = skill.get("preferredLabel", "").strip()

            if not skill_uri or not skill_name:
                continue

            matches = relationships_by_skill.get(skill_uri, [])

            if matches:
                skills_with_relationships += 1

                for relationship in matches:
                    writer.writerow(
                        {
                            "ESCO_Skill_Id": skill_uri,
                            "Skill_Name": skill_name,
                            "Skill_Category": skill.get("skillType", ""),
                            "Occupation": (
                                relationship.get("occupationLabel", "").strip()
                                or occupation_labels.get(
                                    relationship.get("occupationUri", ""), ""
                                )
                            ),
                            "Importance": relationship.get("relationType", ""),
                        }
                    )
                    output_rows += 1
            else:
                writer.writerow(
                    {
                        "ESCO_Skill_Id": skill_uri,
                        "Skill_Name": skill_name,
                        "Skill_Category": skill.get("skillType", ""),
                        "Occupation": "",
                        "Importance": "",
                    }
                )
                output_rows += 1

    print(f"Created: {OUTPUT_FILE}")
    print(f"Mapping rows: {output_rows}")
    print(f"Skills with occupation relationships: {skills_with_relationships}")
    print(f"Source relationship rows: {len(relationships)}")


if __name__ == "__main__":
    main()