"""Build Road2Hire's occupation-specific O*NET mapping."""

import csv
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOWNLOADS = Path.home() / "Downloads"
OUTPUT_FILE = (
    PROJECT_ROOT
    / "Datasets"
    / "ESCO_ONET"
    / "Mappings"
    / "ONET_Skill_Mapping.csv"
)

SOURCES = {
    "essential_skills.csv": "essential_skill",
    "knowledge.csv": "knowledge",
    "transferable_skills.csv": "transferable_skill",
}


def main() -> None:
    grouped = defaultdict(dict)
    source_row_count = 0

    for filename, skill_type in SOURCES.items():
        source_file = DOWNLOADS / filename

        with source_file.open(
            "r", encoding="utf-8-sig", newline=""
        ) as file:
            rows = csv.DictReader(file)

            for row in rows:
                source_row_count += 1
                occupation_code = row["O*NET-SOC Code"].strip()
                element_id = row["Element ID"].strip()

                if not occupation_code or not element_id:
                    continue

                key = (occupation_code, element_id, skill_type)
                values = grouped[key]

                values["occupation_code"] = occupation_code
                values["skill_name"] = row["Element Name"].strip()
                values["skill_type"] = skill_type

                if row["Scale ID"].strip() == "IM":
                    values["importance"] = row["Data Value"].strip()
                elif row["Scale ID"].strip() == "LV":
                    values["level"] = row["Data Value"].strip()

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "ONET_SOC_Code",
                "ONET_Skill_Id",
                "Skill_Name",
                "Skill_Type",
                "Importance_Score",
                "Level_Score",
            ],
        )
        writer.writeheader()

        for (_, element_id, skill_type), values in grouped.items():
            writer.writerow(
                {
                    "ONET_SOC_Code": values["occupation_code"],
                    "ONET_Skill_Id": element_id,
                    "Skill_Name": values["skill_name"],
                    "Skill_Type": skill_type,
                    "Importance_Score": values.get("importance", ""),
                    "Level_Score": values.get("level", ""),
                }
            )

    print(f"Created: {OUTPUT_FILE}")
    print(f"Source rows processed: {source_row_count}")
    print(f"Occupation-skill records: {len(grouped)}")
    print(
        "Unique occupations:",
        len({key[0] for key in grouped}),
    )
    print(
        "Records by category:",
        {
            skill_type: sum(
                values["skill_type"] == skill_type
                for values in grouped.values()
            )
            for skill_type in SOURCES.values()
        },
    )


if __name__ == "__main__":
    main()