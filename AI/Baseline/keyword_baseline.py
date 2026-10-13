import json


def keyword_match(candidate_skills, required_skills):
    candidate = {skill.lower() for skill in candidate_skills}

    present = []
    missing = []

    for skill in required_skills:
        if skill.lower() in candidate:
            present.append(skill)
        else:
            missing.append(skill)

    total_required = len(required_skills)
    matched = len(present)

    score = matched / total_required if total_required else 0

    return {
        "present_skills": present,
        "missing_skills": missing,
        "match_score": round(score, 2)
    }


def main():
    with open("AI/Baseline/sample_evaluation.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    results = []

    for sample in data["samples"]:
        result = keyword_match(
            sample["candidate_skills"],
            sample["required_skills"]
        )

        results.append({
            "id": sample["id"],
            **result
        })

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()