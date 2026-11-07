"""Command-Line Interface for the Central Road2Hire Career Readiness Pipeline.

Usage:
    python -m AI.Pipeline.cli --resume "Tests/AI/sample_resume.pdf"
    python -m AI.Pipeline.cli --resume "Tests/AI/sample_resume.pdf" --occupation "Data Engineer"
    python -m AI.Pipeline.cli --resume "Tests/AI/sample_resume.pdf" --occupation "Data Engineer" --format markdown
    python -m AI.Pipeline.cli --resume "Tests/AI/sample_resume.pdf" --verbose
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
import sys
from typing import Any
import warnings

# Suppress symlinks warning on Windows, tokenizer parallelism, and tqdm by default
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("TQDM_DISABLE", "1")

from AI.Pipeline.pipeline import PipelineError, Road2HirePipeline
from AI.Pipeline.pipeline_schema import UnifiedPipelineResult
from AI.road2hire_model import PIPELINE_VERSION

logger = logging.getLogger("AI.Pipeline")

_NOISY_LOGGERS = [
    "httpx",
    "httpcore",
    "huggingface_hub",
    "sentence_transformers",
    "transformers",
    "urllib3",
    "AI.road2hire_model",
    "AI.Pipeline",
    "AI.Pipeline.report_generator",
    "AI.Pipeline.pipeline",
    "AI.Skill_Extraction",
    "AI.Skill_Normalization",
    "AI.Knowledge_Graph",
    "AI.Candidate_Profile",
    "AI.Skill_Gap",
    "AI.Readiness_Model",
]


def configure_logging(verbose: bool = False, quiet: bool = False) -> None:
    """Configure terminal logging, warning filters, and progress bar verbosity."""
    if verbose:
        # Verbose diagnostic mode: re-enable progress bars, expose INFO/DEBUG logs
        os.environ["ROAD2HIRE_VERBOSE"] = "1"
        os.environ.pop("TQDM_DISABLE", None)
        try:
            import transformers.utils.logging as t_logging
            t_logging.set_verbosity_info()
        except ImportError:
            pass

        try:
            import huggingface_hub.utils.logging as hf_logging
            hf_logging.set_verbosity_info()
        except ImportError:
            pass

        log_level = logging.INFO
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
            force=True,
        )
        for name in _NOISY_LOGGERS:
            logging.getLogger(name).setLevel(logging.INFO)
    else:
        # Clean mode: suppress third-party HTTP logs, progress bars, and token warnings
        os.environ["ROAD2HIRE_VERBOSE"] = "0"
        os.environ["TQDM_DISABLE"] = "1"

        # Suppress Hugging Face unauthenticated request warnings and info notices
        warnings.filterwarnings(
            "ignore",
            message=r".*unauthenticated requests to the HF Hub.*",
        )
        warnings.filterwarnings(
            "ignore",
            category=UserWarning,
            module=r"huggingface_hub.*",
        )

        try:
            import transformers.utils.logging as t_logging
            t_logging.set_verbosity_error()
        except ImportError:
            pass

        try:
            import huggingface_hub.utils.logging as hf_logging
            hf_logging.set_verbosity_error()
        except ImportError:
            pass

        log_level = logging.ERROR if quiet else logging.WARNING
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
            force=True,
        )
        for name in _NOISY_LOGGERS:
            logging.getLogger(name).setLevel(logging.ERROR)


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
        "--verbose",
        action="store_true",
        help="Enable detailed diagnostic logging, model-loading output, and full tracebacks.",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Run in quiet mode, suppressing progress logging and terminal banner/summary.",
    )
    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version=f"%(prog)s version {PIPELINE_VERSION}",
    )

    return parser


def extract_candidate_name(candidate_profile: Any) -> str:
    """Extract candidate name from profile; fallback to 'Not provided'.

    Never derives candidate name from resume filename.
    """
    if isinstance(candidate_profile, dict):
        cand = candidate_profile.get("candidate", {})
        if isinstance(cand, dict):
            name = cand.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
    return "Not provided"


def print_banner() -> None:
    """Print clean Road2Hire header banner."""
    print("=" * 70)
    print(" ROAD2HIRE — CAREER READINESS & RESUME INTELLIGENCE PIPELINE")
    print(f" Version: {PIPELINE_VERSION} | ESCO Taxonomy & Knowledge Graph Integrated")
    print("=" * 70)


def print_summary(result: UnifiedPipelineResult) -> None:
    """Print clean, professional terminal summary of execution results."""
    occ = result.selected_occupation
    gap = result.skill_gap_analysis
    readiness = result.readiness_prediction
    shap_exp = result.shap_explanation
    roadmap = result.learning_roadmap
    candidate_name = extract_candidate_name(result.candidate_profile)

    status_label = "Success"
    if result.errors:
        status_label = f"Failed ({len(result.errors)} error(s))"
    elif result.warnings:
        status_label = f"Completed with warnings ({len(result.warnings)} warning(s))"

    print("\n" + "=" * 70)
    print(" ROAD2HIRE — PIPELINE EXECUTION SUMMARY")
    print(f" Version: {result.pipeline_version}")
    print("=" * 70)
    print(f" Processing Status:   {status_label}")
    print(f" Candidate Name:      {candidate_name}")
    print(f" Source File:         {result.source_file} ({result.page_count} page(s))")
    print(f" Target Occupation:   {occ.occupation_label}")
    print(f" ESCO Concept URI:    {occ.occupation_uri}")
    print("-" * 70)
    print(f" Extracted Skills:    {len(result.extracted_skills)} technical skills verified")
    print(f" Overall Coverage:    {gap.get('overall_skill_coverage_score', 0.0)*100:.1f}%")
    print(f" Essential Coverage:  {gap.get('essential_skill_coverage_score', 0.0)*100:.1f}%")
    print(f" Optional Coverage:   {gap.get('optional_skill_coverage_score', 0.0)*100:.1f}%")
    print("-" * 70)

    if readiness:
        prob = readiness.class_probabilities.get(readiness.predicted_class, 0.0)
        print(f" Readiness Class:     {readiness.predicted_class} ({prob*100:.1f}% model probability)")
        if getattr(readiness, "is_ood", False):
            print(f" Readiness Caution:   Feature values outside training bounds ({len(readiness.ood_warnings)} warning(s))")

    if shap_exp:
        top_pos = [f.get("display_name", f.get("feature")) for f in shap_exp.top_positive_factors[:2]]
        top_neg = [f.get("display_name", f.get("feature")) for f in shap_exp.top_negative_factors[:2]]
        print(f" Supporting Factors:  {', '.join(top_pos) if top_pos else 'None'}")
        print(f" Constraining:        {', '.join(top_neg) if top_neg else 'None'}")

    if roadmap:
        print(f" Learning Roadmap:    {roadmap.total_roadmap_skills} skills across {len(roadmap.phases)} phases ({roadmap.total_estimated_weeks})")

    print("-" * 70)
    print(" Generated Report Artifacts:")
    for fmt, p in result.report_paths.items():
        print(f"   [{fmt.upper()}] {p}")
    print("=" * 70 + "\n")


def main(argv: list[str] | None = None) -> int:
    """Execute CLI application."""
    parser = build_parser()
    args = parser.parse_args(argv)

    configure_logging(verbose=args.verbose, quiet=args.quiet)

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

        if result.errors:
            print(
                f"\n[PIPELINE ERROR] Pipeline completed with errors: {'; '.join(result.errors)}\n",
                file=sys.stderr,
            )
            return 1

        return 0

    except PipelineError as exc:
        if args.verbose:
            logger.exception("Pipeline failure trace:")
        print(f"\n[PIPELINE ERROR] {exc}\n", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nPipeline execution cancelled by user.", file=sys.stderr)
        return 130
    except Exception as exc:
        if args.verbose:
            logger.exception("Unexpected pipeline failure: %s", exc)
        print(f"\n[ERROR] {exc}\n", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
