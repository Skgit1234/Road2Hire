"""Central Road2Hire Pipeline Orchestrator.

Coordinates the complete end-to-end career readiness workflow:
Resume PDF
  → Resume Processing (M1)
  → Trie-based Skill Extraction & ESCO Normalization (M2)
  → Candidate Profile Assembly (Schema v1.1.0)
  → Knowledge Graph Occupation Matching (M2)
  → Target Occupation Selection & Resolution
  → Hybrid Skill Gap Detection (M3)
  → Personalized Knowledge Graph (M3)
  → Career Readiness Classification (M4)
  → SHAP Explainability (M4.5)
  → Personalized Learning Roadmap
  → Unified Report Generation (Markdown & JSON)
"""

from __future__ import annotations

from datetime import datetime
import logging
from pathlib import Path
import threading
import time
from typing import Any

from AI.Pipeline.pipeline_schema import (
    ReadinessPredictionData,
    SHAPExplanationData,
    UnifiedPipelineResult,
)
from AI.Pipeline.report_generator import ReportGenerator
from AI.Pipeline.roadmap_generator import RoadmapGenerator
from AI.Pipeline.target_occupation_selector import (
    OccupationSelectionError,
    PipelineError,
    TargetOccupationSelector,
)
from AI.road2hire_model import PIPELINE_VERSION, Road2HireModel, get_road2hire_model

logger = logging.getLogger(__name__)


class ResumeValidationError(PipelineError):
    """Raised when the resume input cannot be validated or extracted."""


class Road2HirePipeline:
    """Central orchestrator for the complete Road2Hire Career Readiness system.

    Parameters
    ----------
    model:
        Optional pre-initialized Road2HireModel instance. If None, the shared
        module singleton is used to avoid duplicate memory allocation.
    base_output_dir:
        Directory under which output report folders are created.
    """

    def __init__(
        self,
        model: Road2HireModel | None = None,
        base_output_dir: Path | str = "Outputs",
    ) -> None:
        self.model = model if model is not None else get_road2hire_model()
        self.base_output_dir = Path(base_output_dir)

        # Re-entrant thread synchronization lock for lazy model loading
        self._lock = threading.RLock()

        # Sub-components
        self.occupation_selector = TargetOccupationSelector(taxonomy=self.model._taxonomy)
        self.roadmap_generator = RoadmapGenerator(taxonomy=self.model._taxonomy)
        self.report_generator = ReportGenerator(base_output_dir=self.base_output_dir)

        # Lazy references for M4 readiness pipeline & explainer
        self._readiness_pipeline: Any = None
        self._readiness_metadata: dict[str, Any] | None = None
        self._shap_explainer: Any = None

    # -------------------------------------------------------------------------
    # Central Public Entry Point
    # -------------------------------------------------------------------------

    def run(
        self,
        resume_path: str | Path,
        target_occupation: str | None = None,
        interactive: bool = False,
        output_dir: Path | str | None = None,
        output_format: str = "both",
        top_n_occupations: int = 10,
        *,
        auto_select_top_occupation: bool = False,
    ) -> UnifiedPipelineResult:
        """Execute the complete end-to-end career readiness pipeline.

        Parameters
        ----------
        resume_path:
            Path to the candidate's PDF resume.
        target_occupation:
            Optional target occupation title, search string, or ESCO URI.
            If None and auto_select_top_occupation=True, the highest-scoring
            recommendation is automatically resolved.
            If None and interactive=True, the user is prompted in console.
            If None and interactive=False and auto_select_top_occupation=False,
            an OccupationSelectionError is raised with suggested_occupations.
        interactive:
            Whether to prompt user if target_occupation is omitted.
        output_dir:
            Custom output directory path for generated reports.
        output_format:
            'both', 'json', 'markdown', or 'none'.
        top_n_occupations:
            Number of top matching occupations to display or rank.
        auto_select_top_occupation:
            If True and target_occupation is None, automatically select the top
            recommended occupation from resume analysis.

        Returns
        -------
        UnifiedPipelineResult
            The complete, validated pipeline execution result.
        """
        start_total = time.perf_counter()
        timings: dict[str, float] = {}
        warnings: list[str] = []
        errors: list[str] = []

        # -----------------------------------------------------------------
        # Input Validation
        # -----------------------------------------------------------------
        if resume_path is None or (isinstance(resume_path, str) and not resume_path.strip()):
            raise ResumeValidationError("Resume path must be a non-empty string or Path object.")

        if not isinstance(resume_path, (str, Path)):
            raise ResumeValidationError(
                f"Resume path must be a string or Path object, got: {type(resume_path).__name__}"
            )

        if target_occupation is not None and not isinstance(target_occupation, str):
            raise TypeError(
                f"target_occupation must be a string or None, got: {type(target_occupation).__name__}"
            )

        path = Path(resume_path)
        if not path.is_file():
            raise ResumeValidationError(f"Resume file not found: {path}")
        if path.suffix.casefold() != ".pdf":
            raise ResumeValidationError(f"Expected a .pdf file, got: {path.suffix!r}")
        if path.stat().st_size == 0:
            raise ResumeValidationError(f"Failed to process resume '{path}': Resume file is empty (0 bytes)")

        # -----------------------------------------------------------------
        # Stage 1: Resume Processing, Skills, Normalization & Occupation Ranking
        # -----------------------------------------------------------------
        t0 = time.perf_counter()
        try:
            resume_result = self.model.predict(path)
        except Exception as exc:
            raise ResumeValidationError(f"Failed to process resume '{path}': {exc}") from exc
        timings["resume_prediction_seconds"] = round(time.perf_counter() - t0, 4)

        if resume_result.get("status") == "error":
            errors.extend(resume_result.get("errors", []))
            raise ResumeValidationError(
                f"Resume extraction encountered critical errors: {'; '.join(errors)}"
            )

        warnings.extend(resume_result.get("warnings", []))

        # -----------------------------------------------------------------
        # Stage 2: Target Occupation Selection & Resolution
        # -----------------------------------------------------------------
        t0 = time.perf_counter()
        ranked_matches = resume_result.get("occupation_matches", [])
        try:
            selected_occ = self.occupation_selector.resolve_selection(
                query=target_occupation,
                ranked_matches=ranked_matches,
                interactive=interactive,
                top_n=top_n_occupations,
                auto_select_top=auto_select_top_occupation,
            )
        except OccupationSelectionError:
            raise
        except Exception as exc:
            raise OccupationSelectionError(
                f"Failed to resolve target occupation: {exc}",
                suggested_occupations=ranked_matches[:top_n_occupations],
            ) from exc
        timings["target_occupation_resolution_seconds"] = round(time.perf_counter() - t0, 4)

        # -----------------------------------------------------------------
        # Stage 3: Hybrid Skill Gap Detection (M3)
        # -----------------------------------------------------------------
        t0 = time.perf_counter()
        try:
            gap_report = self.model.detect_skill_gap(
                resume_or_profile=resume_result,
                target_occupation=selected_occ.occupation_uri,
            )
        except Exception as exc:
            logger.error("Skill gap detection failed: %s", exc, exc_info=True)
            errors.append(f"Skill gap detection failed: {exc}")
            gap_report = {"error": str(exc), "overall_skill_coverage_score": 0.0}
        timings["skill_gap_detection_seconds"] = round(time.perf_counter() - t0, 4)

        # -----------------------------------------------------------------
        # Stage 4: Personalized Knowledge Graph (M3)
        # -----------------------------------------------------------------
        t0 = time.perf_counter()
        pg_summary: dict[str, Any] = {}
        try:
            pg = self.model.build_personalized_graph(
                resume_or_profile=resume_result,
                target_occupation=selected_occ.occupation_uri,
                gap_report=gap_report,
            )
            pg_summary = pg.get_summary()
        except Exception as exc:
            logger.warning("Personalized knowledge graph construction failed: %s", exc)
            warnings.append(f"Personalized graph creation failed: {exc}")
        timings["personalized_graph_seconds"] = round(time.perf_counter() - t0, 4)

        # -----------------------------------------------------------------
        # Stage 5: Career Readiness Prediction (M4)
        # -----------------------------------------------------------------
        t0 = time.perf_counter()
        readiness_data = self._predict_readiness(
            resume_result=resume_result,
            warnings=warnings,
        )
        timings["readiness_prediction_seconds"] = round(time.perf_counter() - t0, 4)

        # -----------------------------------------------------------------
        # Stage 6: SHAP Explainability (M4.5)
        # -----------------------------------------------------------------
        t0 = time.perf_counter()
        shap_data = self._explain_readiness(
            resume_result=resume_result,
            predicted_class=(
                readiness_data.predicted_class if readiness_data else None
            ),
            warnings=warnings,
        )
        timings["shap_explainability_seconds"] = round(time.perf_counter() - t0, 4)

        # -----------------------------------------------------------------
        # Stage 7: Personalized Learning Roadmap
        # -----------------------------------------------------------------
        t0 = time.perf_counter()
        roadmap = None
        if "error" not in gap_report:
            try:
                roadmap = self.roadmap_generator.generate_roadmap(
                    gap_report=gap_report,
                    target_occupation_title=selected_occ.occupation_label,
                    target_occupation_uri=selected_occ.occupation_uri,
                )
            except Exception as exc:
                logger.warning("Roadmap generation failed: %s", exc)
                warnings.append(f"Roadmap generation failed: {exc}")
        timings["roadmap_generation_seconds"] = round(time.perf_counter() - t0, 4)

        timings["total_pipeline_seconds"] = round(time.perf_counter() - start_total, 4)

        # -----------------------------------------------------------------
        # Stage 8: Unified Output Construction & File Reporting
        # -----------------------------------------------------------------
        status = (
            "error"
            if errors
            else "warning"
            if (warnings or resume_result.get("status") == "warning")
            else "success"
        )

        result = UnifiedPipelineResult(
            pipeline_version=PIPELINE_VERSION,
            timestamp=datetime.now().isoformat(),
            source_file=str(path),
            page_count=resume_result.get("page_count", 1),
            extraction_status=resume_result.get("extraction_status", "success"),
            candidate_profile=resume_result.get("candidate_profile", {}),
            extracted_skills=resume_result.get("extracted_skills", []),
            esco_mappings=resume_result.get("esco_mappings", []),
            occupation_matches=ranked_matches,
            selected_occupation=selected_occ,
            skill_gap_analysis=gap_report,
            personalized_graph_summary=pg_summary,
            readiness_prediction=readiness_data,
            shap_explanation=shap_data,
            learning_roadmap=roadmap,
            execution_timings_seconds=timings,
            warnings=warnings,
            errors=errors,
            status=status,
        )

        if output_format.casefold() != "none":
            try:
                self.report_generator.save_reports(
                    result=result,
                    output_dir=output_dir,
                    output_format=output_format,
                )
            except Exception as exc:
                logger.error("Failed to save report artifacts: %s", exc)
                warnings.append(f"Report artifact saving failed: {exc}")

        return result

    # -------------------------------------------------------------------------
    # Internal Inference & Explainability Helpers
    # -------------------------------------------------------------------------

    def _ensure_readiness_model(self) -> Any:
        """Load and cache the persisted M4 readiness model pipeline."""
        if self._readiness_pipeline is None:
            with self._lock:
                if self._readiness_pipeline is None:
                    from AI.Readiness_Model.model_trainer import load_persisted_model

                    self._readiness_pipeline, self._readiness_metadata = load_persisted_model()
        return self._readiness_pipeline

    def _ensure_shap_explainer(self) -> Any:
        """Load and cache the M4.5 SHAP explainer."""
        if self._shap_explainer is None:
            pipeline = self._ensure_readiness_model()
            if pipeline is None:
                raise RuntimeError("Cannot initialize SHAP explainer without readiness model pipeline.")
            with self._lock:
                if self._shap_explainer is None:
                    from AI.Readiness_Model.shap_explainer import ReadinessModelExplainer

                    self._shap_explainer = ReadinessModelExplainer(pipeline=pipeline)
        return self._shap_explainer

    def _extract_evidence_dict(self, resume_result: dict[str, Any]) -> dict[str, str]:
        """Convert candidate profile and sections into evidence dictionary for M4.

        Ensures consistency between inference evidence and M4 training evidence schema:
        - skills_text: comma-separated list of candidate skills.
        - experience_text: newline-delimited list of distinct professional positions.
        - projects_text: newline-delimited list of projects with (Tech: ...) tags.
        - education_text: newline-delimited list of academic qualifications.
        """
        prof = resume_result.get("candidate_profile", {})
        sections = resume_result.get("sections", {})

        # 1. Skills Text: Prefer normalized skills from candidate profile, fallback to raw section
        prof_skills = prof.get("skills", [])
        if prof_skills and isinstance(prof_skills, list):
            skill_names = [
                s.get("ESCO_Skill_Name") or s.get("skill")
                for s in prof_skills
                if isinstance(s, dict) and (s.get("ESCO_Skill_Name") or s.get("skill"))
            ]
            skills_text = ", ".join(skill_names)
        else:
            skills_text = sections.get("skills", "")

        # 2. Experience Text: Format distinct position lines to avoid raw-line explosion
        prof_exps = prof.get("experience", [])
        if prof_exps and isinstance(prof_exps, list):
            exp_lines = []
            for e in prof_exps:
                if not isinstance(e, dict):
                    continue
                title = e.get("job_title") or "Professional"
                org = e.get("organization") or ""
                org_str = f" at {org}" if org else ""
                resps = e.get("responsibilities", [])
                resp_str = f" - {resps[0][:100]}" if (resps and isinstance(resps, list)) else ""
                skills_used = e.get("skills_used", [])
                skills_str = (
                    f" [Skills: {', '.join(skills_used[:4])}]"
                    if (skills_used and isinstance(skills_used, list))
                    else ""
                )
                exp_lines.append(f"• {title}{org_str}{resp_str}{skills_str}")
            experience_text = "\n".join(exp_lines)
        else:
            experience_text = sections.get("experience", "")

        # 3. Projects Text: Format with (Tech: ...) tags consistent with training data
        prof_projs = prof.get("projects", [])
        if prof_projs and isinstance(prof_projs, list):
            proj_lines = []
            for p in prof_projs:
                if not isinstance(p, dict):
                    continue
                p_name = p.get("project_name") or "Project"
                desc = p.get("description") or ""
                desc_short = f": {desc[:100]}..." if desc else ""
                techs = p.get("technologies", [])
                tech_str = (
                    f" (Tech: {', '.join(techs[:5])})"
                    if (techs and isinstance(techs, list))
                    else ""
                )
                proj_lines.append(f"• {p_name}{desc_short}{tech_str}")
            projects_text = "\n".join(proj_lines)
        else:
            projects_text = sections.get("projects", "")

        # 4. Education Text: Format degree, field, and institution lines
        prof_edus = prof.get("education", [])
        if prof_edus and isinstance(prof_edus, list):
            edu_lines = []
            for ed in prof_edus:
                if not isinstance(ed, dict):
                    continue
                deg = ed.get("degree") or "Degree"
                field = ed.get("field_of_study") or ""
                inst = ed.get("institution") or ""
                inst_str = f" at {inst}" if inst else ""
                field_str = f" in {field}" if field else ""
                edu_lines.append(f"• {deg}{field_str}{inst_str}".strip())
            education_text = "\n".join(edu_lines)
        else:
            education_text = sections.get("education", "")

        return {
            "skills_text": skills_text,
            "experience_text": experience_text,
            "projects_text": projects_text,
            "education_text": education_text,
        }

    def _predict_readiness(
        self,
        resume_result: dict[str, Any],
        warnings: list[str],
    ) -> ReadinessPredictionData | None:
        """Run M4 supervised readiness prediction on candidate evidence."""
        try:
            pipeline = self._ensure_readiness_model()
            evidence = self._extract_evidence_dict(resume_result)

            pred_class = str(pipeline.predict([evidence])[0])
            probs = pipeline.predict_proba([evidence])[0]
            classes = [str(c) for c in pipeline.classes_]
            prob_dict = {c: round(float(p), 4) for c, p in zip(classes, probs)}

            # Extract numeric feature values for transparency
            from AI.Readiness_Model.feature_extractor import get_feature_names
            from AI.Readiness_Model.ood_detector import get_default_ood_detector

            extractor = pipeline.named_steps["extractor"]
            feat_matrix = extractor.transform([evidence])
            feat_names = get_feature_names()
            feat_values = {
                name: round(float(val), 2)
                for name, val in zip(feat_names, feat_matrix[0])
            }

            # Out-of-Distribution (OOD) Detection
            ood_detector = get_default_ood_detector()
            ood_result = ood_detector.detect(feat_values)
            if ood_result.is_ood:
                for ood_w in ood_result.ood_warnings:
                    warnings.append(f"M4 OOD Notice: {ood_w}")

            model_type = type(pipeline.named_steps["classifier"]).__name__
            meta = self._readiness_metadata or {}
            version = meta.get("model_version", "0.1.0-exploratory")
            sample_count = int(meta.get("training_sample_count", 71))
            class_dist = meta.get("class_distribution", {"Developing": 52, "Job Ready": 16, "Not Ready": 3})

            return ReadinessPredictionData(
                predicted_class=pred_class,
                class_probabilities=prob_dict,
                model_version=version,
                model_type=model_type,
                feature_values=feat_values,
                is_experimental=True,
                is_ood=ood_result.is_ood,
                ood_warnings=ood_result.ood_warnings,
                training_sample_count=sample_count,
                training_class_distribution=class_dist,
                feature_diagnostics=ood_result.feature_diagnostics,
                limitations=[
                    "Exploratory supervised model trained on an annotated pilot dataset (N=71).",
                    "Predictions reflect profile depth and structural signals; they do not certify real-world competence.",
                    "Class probabilities are heuristic estimates from regularized multinomial logistic regression and are not fully calibrated.",
                ],
            )
        except Exception as exc:
            logger.warning("M4 Readiness prediction failed: %s", exc)
            warnings.append(f"M4 Readiness prediction skipped due to error: {exc}")
            return None

    def _explain_readiness(
        self,
        resume_result: dict[str, Any],
        predicted_class: str | None,
        warnings: list[str],
    ) -> SHAPExplanationData | None:
        """Generate SHAP explanations for candidate evidence using M4.5 explainer."""
        if not predicted_class:
            return None

        try:
            explainer = self._ensure_shap_explainer()
            evidence = self._extract_evidence_dict(resume_result)

            exp_result = explainer.explain_instance(
                instance=evidence,
                target_class=predicted_class,
                top_k=3,
            )

            exp = exp_result["explanation"]
            viz = exp_result["visualization_data"]

            # Load global feature importance if available
            global_importance: list[dict[str, Any]] = []
            if hasattr(explainer, "load_global_importance"):
                try:
                    global_data = explainer.load_global_importance()
                    global_importance = global_data.get("overall_feature_importance", [])
                except Exception as exc:
                    logger.debug("Could not retrieve global SHAP importance: %s", exc)

            return SHAPExplanationData(
                target_class_explained=exp.get("target_class_explained", ""),
                base_value=exp.get("base_value", 0.0),
                top_positive_factors=exp.get("top_positive_factors", []),
                top_negative_factors=exp.get("top_negative_factors", []),
                feature_contributions=exp.get("feature_contributions", []),
                human_readable_summary=exp.get("human_readable_summary", ""),
                waterfall_steps=viz.get("waterfall_steps", []),
                global_importance_ranking=global_importance,
                limitations=exp_result.get("limitations", []),
            )
        except Exception as exc:
            logger.warning("SHAP explainability failed: %s", exc)
            warnings.append(f"SHAP explanation skipped due to error: {exc}")
            return None


# ---------------------------------------------------------------------------
# Module-level cached pipeline singleton & public backend integration entry points
# ---------------------------------------------------------------------------

_pipeline_singleton: Road2HirePipeline | None = None
_pipeline_lock = threading.RLock()


def get_pipeline(
    base_output_dir: Path | str = "Outputs",
) -> Road2HirePipeline:
    """Return a cached, thread-safe module-level Road2HirePipeline instance.

    Reuses the underlying Road2HireModel singleton and M4 models to eliminate
    redundant initialization overhead across multiple inference requests.
    Thread-safe and suitable for FastAPI server processes.
    """
    global _pipeline_singleton  # noqa: PLW0603
    if _pipeline_singleton is None:
        with _pipeline_lock:
            if _pipeline_singleton is None:
                _pipeline_singleton = Road2HirePipeline(base_output_dir=base_output_dir)
    return _pipeline_singleton


def process_resume(
    resume_path: str | Path,
    target_occupation: str | None = None,
    *,
    auto_select_top_occupation: bool = False,
    output_dir: Path | str | None = None,
    output_format: str = "both",
    top_n_occupations: int = 10,
    pipeline: Road2HirePipeline | None = None,
) -> UnifiedPipelineResult:
    """Process a candidate resume and return canonical pipeline results.

    This is the primary Python integration interface for the Road2Hire AI/ML
    pipeline, designed for direct invocation by backend services (e.g. FastAPI
    route handlers or async Celery/rq task workers).

    Parameters
    ----------
    resume_path:
        Path to candidate PDF resume file on disk.
    target_occupation:
        Target occupation title, ESCO URI, or search string. If None and
        `auto_select_top_occupation` is True, the highest-ranking role is used.
    auto_select_top_occupation:
        If True and target_occupation is None, automatically selects the #1
        occupation recommendation derived from extracted skills.
    output_dir:
        Optional destination directory for JSON and Markdown report artifacts.
    output_format:
        'both' (default), 'json', 'markdown', or 'none'.
    top_n_occupations:
        Number of ranked occupation recommendations to compute (default 10).
    pipeline:
        Optional custom Road2HirePipeline instance. If None, the shared
        thread-safe pipeline instance from `get_pipeline()` is used.

    Returns
    -------
    UnifiedPipelineResult
        The validated, structured pipeline result object. Call `.to_canonical_dict()`
        or `.to_json()` to produce Draft-07 compliant JSON for HTTP responses.

    Raises
    ------
    ResumeValidationError:
        If the resume file is missing, empty, not a PDF, or extraction fails.
    OccupationSelectionError:
        If target occupation is invalid or omitted when auto_select_top_occupation is False.
    PipelineError:
        If any fatal pipeline orchestration error occurs.
    """
    active_pipeline = pipeline if pipeline is not None else get_pipeline()
    return active_pipeline.run(
        resume_path=resume_path,
        target_occupation=target_occupation,
        interactive=False,
        output_dir=output_dir,
        output_format=output_format,
        top_n_occupations=top_n_occupations,
        auto_select_top_occupation=auto_select_top_occupation,
    )
