
import json
from pathlib import Path

from skill_graph_matcher import match_skills


HERE = Path(__file__).resolve().parent
DATA_PATH = HERE / "graph_evaluation_data.json"
OUTPUT_PATH = HERE / "graph_evaluation_results.json"


def metrics(expected, predicted):
    expected_set = set(expected)
    predicted_set = set(predicted)

    tp = len(expected_set & predicted_set)
    fp = len(predicted_set - expected_set)
    fn = len(expected_set - predicted_set)

    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and precision + recall
        else None
    )

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def main():
    dataset = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    results = []

    for sample in dataset["samples"]:
        prediction = match_skills(
            sample["candidate_skills"],
            sample["target_skills"],
        )

        checks = {
            "direct_matches": "expected_direct_matches",
            "related_matches": "expected_related_matches",
            "missing_target_skills": "expected_missing_target_skills",
            "unknown_candidate_skills": "expected_unknown_candidate_skills",
        }

        comparisons = {}
        for predicted_key, expected_key in checks.items():
            expected = sample.get(expected_key, [])
            predicted = prediction[predicted_key]
            comparisons[predicted_key] = {
                "expected": expected,
                "predicted": predicted,
                "pass": set(expected) == set(predicted),
            }

        results.append({
            "id": sample["id"],
            "comparisons": comparisons,
            "direct_match_metrics": metrics(
                sample["expected_direct_matches"],
                prediction["direct_matches"],
            ),
            "related_match_metrics": metrics(
                sample["expected_related_matches"],
                prediction["related_matches"],
            ),
            "relationship_evidence": prediction["relationship_evidence"],
        })

    report = {
        "sample_count": len(results),
        "passed_checks": sum(
            check["pass"]
            for result in results
            for check in result["comparisons"].values()
        ),
        "total_checks": sum(
            len(result["comparisons"]) for result in results
        ),
        "results": results,
        "limitations": [
            "Evaluation cases are manually specified and small.",
            "Related skills are not treated as equivalent to required skills.",
            "NDCG is not calculated because the matcher does not currently rank results.",
            "Baseline comparisons require running the baseline implementations on the same cases."
        ]
    }

    OUTPUT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Evaluation saved to: {OUTPUT_PATH}")
    print(f"Passed checks: {report['passed_checks']}/{report['total_checks']}")


if __name__ == "__main__":
    main()
