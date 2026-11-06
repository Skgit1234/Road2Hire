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
    ) -> UnifiedPipelineResult:
        """Execute the complete end-to-end career readiness pipeline.

        Parameters
        ----------
        resume_path:
            Path to the candidate's PDF resume.
        target_occupation:
            Optional target occupation title, search string, or ESCO URI.
            If None and interactive=True, the user is prompted in console.
            If None and interactive=False, an OccupationSelectionError is raised.
        interactive:
            Whether to prompt user if target_occupation is omitted.
        output_dir:
            Custom output directory path for generated reports.
        output_format:
            'both', 'json', or 'markdown'.
        top_n_occupations:
            Number of top matching occupations to display or rank.

        Returns
        -------
        UnifiedPipelineResult
            The complete, validated pipeline execution result.
        """
        start_total = time.perf_counter()
        timings: dict[str, float] = {}
        warnings: list[str] = []
        errors: list[str] = []

        path = Path(resume_path)
        if not path.is_file():
            raise ResumeValidationError(f"Resume file not found: {path}")
        if path.suffix.casefold() != ".pdf":
            raise ResumeValidationError(f"Expected a .pdf file, got: {path.suffix!r}")

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
            )
        except OccupationSelectionError:
            raise
        except Exception as exc:
            raise OccupationSelectionError(
                f"Failed to resolve target occupation: {exc}"
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
        )

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
            from AI.Readiness_Model.model_trainer import load_persisted_model

            self._readiness_pipeline, self._readiness_metadata = load_persisted_model()
        return self._readiness_pipeline

    def _ensure_shap_explainer(self) -> Any:
        """Load and cache the M4.5 SHAP explainer."""
        if self._shap_explainer is None:
            pipeline = self._ensure_readiness_model()
            from AI.Readiness_Model.shap_explainer import ReadinessModelExplainer

            self._shap_explainer = ReadinessModelExplainer(pipeline=pipeline)
        return self._shap_explainer

    def _extract_evidence_dict(self, resume_result: dict[str, Any]) -> dict[str, str]:
        """Convert resume sections into candidate evidence dictionary for M4."""
        sections = resume_result.get("sections", {})
        return {
            "skills_text": sections.get("skills", ""),
            "experience_text": sections.get("experience", ""),
            "projects_text": sections.get("projects", ""),
            "education_text": sections.get("education", ""),
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

            extractor = pipeline.named_steps["extractor"]
            feat_matrix = extractor.transform([evidence])
            feat_names = get_feature_names()
            feat_values = {
                name: round(float(val), 2)
                for name, val in zip(feat_names, feat_matrix[0])
            }

            model_type = type(pipeline.named_steps["classifier"]).__name__
            version = (self._readiness_metadata or {}).get("model_version", "0.1.0-exploratory")

            return ReadinessPredictionData(
                predicted_class=pred_class,
                class_probabilities=prob_dict,
                model_version=version,
                model_type=model_type,
                feature_values=feat_values,
                is_experimental=True,
                limitations=[
                    "Exploratory supervised model trained on an annotated pilot dataset (N=71).",
                    "Predictions reflect profile depth and structural signals; they do not certify real-world competence.",
                    "Class probabilities are heuristic estimates from regularized multinomial logistic regression.",
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

            return SHAPExplanationData(
                target_class_explained=exp.get("target_class_explained", ""),
                base_value=exp.get("base_value", 0.0),
                top_positive_factors=exp.get("top_positive_factors", []),
                top_negative_factors=exp.get("top_negative_factors", []),
                feature_contributions=exp.get("feature_contributions", []),
                human_readable_summary=exp.get("human_readable_summary", ""),
                waterfall_steps=viz.get("waterfall_steps", []),
                limitations=exp_result.get("limitations", []),
            )
        except Exception as exc:
            logger.warning("SHAP explainability failed: %s", exc)
            warnings.append(f"SHAP explanation skipped due to error: {exc}")
            return None

