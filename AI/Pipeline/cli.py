"""Command-Line Interface for the Central Road2Hire Career Readiness Pipeline.

Usage:
    python -m AI.Pipeline.cli --resume "Tests/AI/sample_resume.pdf"
    python -m AI.Pipeline.cli --resume "Tests/AI/sample_resume.pdf" --occupation "Data Engineer"
    python -m AI.Pipeline.cli --resume "Tests/AI/sample_resume.pdf" --occupation "Data Engineer" --format markdown
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys
import time

from AI.Pipeline.pipeline import PipelineError, Road2HirePipeline
from AI.road2hire_model import PIPELINE_VERSION

logger = logging.getLogger("AI.Pipeline")


def build_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="python -m AI.Pipeline.cli",
        description=(
            "Road2Hire Central Career Readiness Pipeline — End-to-end resume intelligence, "
            "skill gap detection, readiness prediction, SHAP explainability, and learning roadmap."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--resume",
        "-r",
        required=True,
        type=str,
        help="Path to candidate resume PDF file.",
    )
    parser.add_argument(
        "--occupation",
        "-o",
        type=str,
        default=None,
        help=(
            "Target occupation title, concept URI, or search string. "
            "If omitted in interactive terminal sessions, top matching suggestions will be displayed for selection."
        ),
    )
    parser.add_argument(
        "--output",
        "-d",
        type=str,
        default="Outputs",
        help="Base directory where output report folders are saved (default: Outputs/).",
    )
    parser.add_argument(
        "--top-n",
        "-n",
        type=int,
        default=10,
        help="Number of top occupation matches to display or evaluate (default: 10).",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["both", "json", "markdown"],
        default="both",
        help="Output report format to generate (default: both).",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Run in quiet mode, suppressing progress logging.",
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"%(prog)s version {PIPELINE_VERSION}",
    )

    return parser


def print_banner() -> None:
    """Print Road2Hire header banner."""
    print("=" * 70)
    print(" ROAD2HIRE — CAREER READINESS & RESUME INTELLIGENCE PIPELINE")
    print(f" Version: {PIPELINE_VERSION} | ESCO Taxonomy & Knowledge Graph Integrated")
    print("=" * 70)


def print_summary(result: Any) -> None:
    """Print concise terminal summary of execution results."""
    occ = result.selected_occupation
    gap = result.skill_gap_analysis
    readiness = result.readiness_prediction
    shap_exp = result.shap_explanation
    roadmap = result.learning_roadmap
    cand = result.candidate_profile.get("candidate", {}).get("personal_info", {})
    name = cand.get("name") or "Candidate"

    print("\n" + "=" * 70)
    print(" PIPELINE EXECUTION SUMMARY")
    print("=" * 70)
    print(f" Candidate:          {name}")
    print(f" Source File:        {result.source_file} ({result.page_count} page(s))")
    print(f" Target Role:        {occ.occupation_label}")
    print(f" ESCO URI:           {occ.occupation_uri}")
    print("-" * 70)
    print(f" Extracted Skills:   {len(result.extracted_skills)} technical skills verified")
    print(f" Overall Coverage:   {gap.get('overall_skill_coverage_score', 0.0)*100:.1f}%")
    print(f" Essential Coverage: {gap.get('essential_skill_coverage_score', 0.0)*100:.1f}%")
    print(f" Optional Coverage:  {gap.get('optional_skill_coverage_score', 0.0)*100:.1f}%")
    print("-" * 70)

    if readiness:
        prob = readiness.class_probabilities.get(readiness.predicted_class, 0.0)
        print(f" Readiness Class:    {readiness.predicted_class} ({prob*100:.1f}% model confidence)")

    if shap_exp:
        top_pos = [f.get("display_name", f.get("feature")) for f in shap_exp.top_positive_factors[:2]]
        top_neg = [f.get("display_name", f.get("feature")) for f in shap_exp.top_negative_factors[:2]]
        print(f" Supporting Factors: {', '.join(top_pos) if top_pos else 'None'}")
        print(f" Constraining:       {', '.join(top_neg) if top_neg else 'None'}")

    if roadmap:
        print(f" Learning Roadmap:   {roadmap.total_roadmap_skills} skills across {len(roadmap.phases)} phases ({roadmap.total_estimated_weeks})")

    print("-" * 70)
    print(" Generated Report Artifacts:")
    for fmt, p in result.report_paths.items():
        print(f"   [{fmt.upper()}] {p}")
    print("=" * 70 + "\n")


def main(argv: list[str] | None = None) -> int:
    """Execute CLI application."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Configure logging
    log_level = logging.WARNING if args.quiet else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if not args.quiet:
        print_banner()

    resume_path = Path(args.resume)
    if not resume_path.is_file():
        print(f"Error: Resume file not found at '{args.resume}'.", file=sys.stderr)
        return 1

    # Detect interactive mode if occupation is not specified
    is_interactive = (args.occupation is None) and sys.stdin.isatty()

    try:
        pipeline = Road2HirePipeline(base_output_dir=args.output)
        result = pipeline.run(
            resume_path=resume_path,
            target_occupation=args.occupation,
            interactive=is_interactive,
            output_dir=None,
            output_format=args.format,
            top_n_occupations=args.top_n,
        )

        if not args.quiet:
            print_summary(result)
        return 0

    except PipelineError as exc:
        print(f"\n[PIPELINE ERROR] {exc}\n", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nPipeline execution cancelled by user.", file=sys.stderr)
        return 130
    except Exception as exc:
        logger.exception("Unexpected pipeline failure: %s", exc)
        print(f"\n[UNEXPECTED ERROR] {exc}\n", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

