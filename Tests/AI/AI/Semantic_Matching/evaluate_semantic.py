"""Evaluation Pipeline comparing Keyword, Taxonomy, and Semantic Skill Matching.

Evaluates the benchmark suite in semantic_evaluation_data.json, computes
sample-level and macro-aggregated metrics, and compares results against
Issue #16 baselines. Saves machine-readable results to semantic_matching_results.json.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from AI.Baseline.evaluation_metrics import aggregate_metrics
from AI.Baseline.keyword_baseline import keyword_match_with_metrics
from AI.Baseline.taxonomy_baseline import taxonomy_match
from AI.Semantic_Matching.semantic_matcher import (
    PROVISIONAL_MATCH_THRESHOLD,
    PROVISIONAL_UNCERTAIN_THRESHOLD,
    compute_ranking_ndcg,
    semantic_match,
)
from AI.Semantic_Matching.threshold_analysis import run_threshold_analysis

EVAL_DATA_PATH = Path(__file__).parent / "semantic_evaluation_data.json"
RESULTS_JSON_PATH = Path(__file__).parent / "semantic_matching_results.json"


def run_evaluation(
    eval_data_path: Path = EVAL_DATA_PATH,
    results_path: Path = RESULTS_JSON_PATH,
) -> dict[str, Any]:
    """Run full comparative evaluation and persist results."""
    with open(eval_data_path, "r", encoding="utf-8") as f:
        benchmark = json.load(f)

    samples = benchmark.get("samples", [])
    benchmark_size = len(samples)

    keyword_sample_results = []
    taxonomy_sample_results = []
    semantic_sample_results = []

    ranked_ndcg_results = []

    for sample in samples:
        cand = sample.get("candidate_skills", [])
        req = sample.get("required_skills", [])
        sample_id = sample.get("id")

        # 1. Keyword baseline
        kw_res = keyword_match_with_metrics(cand, req)
        keyword_sample_results.append(
            {
                "id": sample_id,
                "category": sample.get("category"),
                "present_skills": kw_res["present_skills"],
                "missing_skills": kw_res["missing_skills"],
                "match_score": kw_res["match_score"],
                "tp": kw_res["tp"],
                "fp": kw_res["fp"],
                "fn": kw_res["fn"],
                "precision": kw_res["precision"],
                "recall": kw_res["recall"],
                "f1": kw_res["f1"],
                "ndcg": kw_res["ndcg"],
            }
        )

        # 2. Taxonomy baseline
        tax_res = taxonomy_match(cand, req)
        taxonomy_sample_results.append(
            {
                "id": sample_id,
                "category": sample.get("category"),
                "present_skills": tax_res["present_skills"],
                "missing_skills": tax_res["missing_skills"],
                "unrecognized_candidate": tax_res["unrecognized_candidate"],
                "unrecognized_required": tax_res["unrecognized_required"],
                "match_score": tax_res["match_score"],
                "tp": tax_res["tp"],
                "fp": tax_res["fp"],
                "fn": tax_res["fn"],
                "precision": tax_res["precision"],
                "recall": tax_res["recall"],
                "f1": tax_res["f1"],
                "ndcg": tax_res["ndcg"],
            }
        )

        # 3. Semantic matcher
        sem_res = semantic_match(
            cand,
            req,
            match_threshold=PROVISIONAL_MATCH_THRESHOLD,
            uncertain_threshold=PROVISIONAL_UNCERTAIN_THRESHOLD,
        )

        # Evaluate NDCG only when ranked query is explicitly defined
        ndcg_val = None
        if "ranked_query" in sample:
            rq = sample["ranked_query"]
            pool = rq.get("candidate_pool", [])
            rel_judgments = rq.get("ground_truth_relevance", {})
            k = rq.get("k", 3)
            # Rank candidate pool using semantic similarity to target query
            from AI.Skill_Extraction.skill_embeddings import (
                cosine_similarity,
                generate_skill_embeddings,
            )

            q_text = rq["query_required_skill"]
            all_t = [q_text] + pool
            emb = {
                item["skill"]: item["embedding"]
                for item in generate_skill_embeddings(all_t)["skills"]
            }
            q_vec = emb.get(q_text)
            scored = []
            for item in pool:
                sim = cosine_similarity(q_vec, emb.get(item)) if q_vec else 0.0
                scored.append((item, sim))
            scored.sort(key=lambda x: x[1], reverse=True)
            ranked_names = [s[0] for s in scored]
            ndcg_val = compute_ranking_ndcg(ranked_names, rel_judgments, k=k)
            ranked_ndcg_results.append(
                {
                    "sample_id": sample_id,
                    "query": q_text,
                    "ranked_candidates": ranked_names,
                    "ndcg": ndcg_val,
                }
            )

        semantic_sample_results.append(
            {
                "id": sample_id,
                "category": sample.get("category"),
                "present_skills": sem_res["present_skills"],
                "missing_skills": sem_res["missing_skills"],
                "related_skills": sem_res["related_skills"],
                "unresolved_skills": sem_res["unresolved_skills"],
                "unrecognized_skills": sem_res["unrecognized_skills"],
                "match_score": sem_res["match_score"],
                "tp": sem_res["tp"],
                "fp": sem_res["fp"],
                "fn": sem_res["fn"],
                "precision": sem_res["precision"],
                "recall": sem_res["recall"],
                "f1": sem_res["f1"],
                "ndcg": ndcg_val,  # None unless ranked query exists
            }
        )

    # Macro aggregation
    macro_kw = aggregate_metrics(keyword_sample_results)
    macro_tax = aggregate_metrics(taxonomy_sample_results)
    macro_sem = aggregate_metrics(semantic_sample_results)

    # Average match score
    avg_score_kw = round(sum(r["match_score"] for r in keyword_sample_results) / benchmark_size, 4)
    avg_score_tax = round(sum(r["match_score"] for r in taxonomy_sample_results) / benchmark_size, 4)
    avg_score_sem = round(sum(r["match_score"] for r in semantic_sample_results) / benchmark_size, 4)

    # Run threshold sweep
    sweep_results = run_threshold_analysis()

    output = {
        "benchmark_metadata": {
            "name": "Road2Hire Issue #17 Semantic Skill Matching Benchmark",
            "benchmark_size": benchmark_size,
            "is_synthetic": True,
            "disclaimer": (
                "This benchmark is composed of hand-crafted synthetic cases for calibration "
                "and regression testing. Precision, recall, and F1 reported here reflect "
                "performance on these curated cases and do NOT establish real-world production "
                "accuracy."
            ),
        },
        "provisional_thresholds": {
            "match_threshold": sweep_results["provisional_threshold_selection"]["selected_match_threshold"],
            "uncertain_threshold": sweep_results["provisional_threshold_selection"]["selected_uncertain_threshold"],
            "selection_rationale": sweep_results["provisional_threshold_selection"]["rationale"],
        },
        "baseline_comparison": {
            "keyword_baseline": {
                "macro_precision": macro_kw["macro_precision"],
                "macro_recall": macro_kw["macro_recall"],
                "macro_f1": macro_kw["macro_f1"],
                "average_match_score": avg_score_kw,
                "precision_undefined_count": macro_kw["precision_undefined_count"],
            },
            "taxonomy_baseline": {
                "macro_precision": macro_tax["macro_precision"],
                "macro_recall": macro_tax["macro_recall"],
                "macro_f1": macro_tax["macro_f1"],
                "average_match_score": avg_score_tax,
                "precision_undefined_count": macro_tax["precision_undefined_count"],
            },
            "semantic_matching": {
                "macro_precision": macro_sem["macro_precision"],
                "macro_recall": macro_sem["macro_recall"],
                "macro_f1": macro_sem["macro_f1"],
                "average_match_score": avg_score_sem,
                "precision_undefined_count": macro_sem["precision_undefined_count"],
            },
        },
        "ranked_ndcg_evaluation": {
            "description": "NDCG is evaluated exclusively on test cases with explicit ranked candidate pools and graded relevance judgments.",
            "results": ranked_ndcg_results,
        },
        "threshold_sweep_summary": {
            "sweep_range": sweep_results["sweep_range"],
            "thresholds_evaluated": sweep_results["thresholds_evaluated"],
            "calibration_results": [
                {
                    "threshold": r["threshold"],
                    "tp": r["tp"],
                    "fp": r["fp"],
                    "fn": r["fn"],
                    "tn": r["tn"],
                    "precision": r["precision"],
                    "recall": r["recall"],
                    "f1": r["f1"],
                }
                for r in sweep_results["pairwise_calibration"]
            ],
            "sample_macro_sweep": sweep_results["sample_macro_metrics"],
        },
        "detailed_sample_results": {
            "keyword": keyword_sample_results,
            "taxonomy": taxonomy_sample_results,
            "semantic": semantic_sample_results,
        },
        "limitations": [
            "Synthetic Data: Calibrated on curated synthetic examples; results cannot be extrapolated to unconstrained text without empirical field testing.",
            "Short Polysemous Tokens: Single-letter or common English verbs (e.g. Go, C, R) require domain context expansion to avoid semantic drift.",
            "Related vs Equivalent: High cosine similarity alone does not guarantee interchangeable competence; domain guards are required.",
            "One-to-One Assumption: Bipartite assignment assumes 1-to-1 skill pairing; multi-skill subsumption requires future graph/ontology integration.",
        ],
    }

    # Save to disk
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    return output


if __name__ == "__main__":
    print("=" * 75)
    print("Running Comparative Evaluation: Keyword vs Taxonomy vs Semantic (Issue #17)")
    print("=" * 75)
    res = run_evaluation()

    comp = res["baseline_comparison"]
    print("\nBenchmark Macro Comparison:")
    print(f"{'Matcher':<20} | {'Macro Prec':>11} | {'Macro Recall':>13} | {'Macro F1':>9} | {'Avg Score':>10}")
    print("-" * 75)
    for name, key in [
        ("Keyword Baseline", "keyword_baseline"),
        ("Taxonomy Baseline", "taxonomy_baseline"),
        ("Semantic Matching", "semantic_matching"),
    ]:
        m = comp[key]
        p_str = f"{m['macro_precision']:.3f}" if m['macro_precision'] is not None else "   None"
        r_str = f"{m['macro_recall']:.3f}" if m['macro_recall'] is not None else "   None"
        f_str = f"{m['macro_f1']:.3f}" if m['macro_f1'] is not None else "   None"
        s_str = f"{m['average_match_score']:.3f}"
        print(f"{name:<20} | {p_str:>11} | {r_str:>13} | {f_str:>9} | {s_str:>10}")

    print(f"\nResults persisted to: {RESULTS_JSON_PATH}")
