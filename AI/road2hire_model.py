"""Central Road2Hire model pipeline.

Orchestrates all existing AI modules into a single, reusable interface:

    from AI.road2hire_model import Road2HireModel

    model = Road2HireModel()
    result = model.predict("path/to/resume.pdf")

Heavy resources (ESCO taxonomy, knowledge graph, embedding model vocabulary)
are initialised once on first use and reused across subsequent ``predict``
calls.  No algorithms are duplicated here — this module is a pure
orchestrator.

Pipeline version: 3.0.0
"""

from __future__ import annotations

import logging
import warnings
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PIPELINE_VERSION = "3.0.0"
_DEFAULT_TOP_N_OCCUPATIONS = 10


# ---------------------------------------------------------------------------
# Road2HireModel
# ---------------------------------------------------------------------------


class Road2HireModel:
    """Central pipeline that connects resume processing, skill extraction,
    ESCO normalisation, semantic embeddings, occupation matching, and
    candidate-profile construction.

    Parameters
    ----------
    top_n_occupations:
        Maximum number of ranked occupation matches to return.
    """

    def __init__(self, top_n_occupations: int = _DEFAULT_TOP_N_OCCUPATIONS) -> None:
        self._top_n = top_n_occupations

        # Heavy singletons — initialised eagerly so the first ``predict``
        # call does not pay the full cold-start cost.
        logger.info("Road2HireModel: loading ESCO taxonomy …")
        from AI.Skill_Extraction.esco_taxonomy import get_esco_taxonomy

        self._taxonomy = get_esco_taxonomy()

        logger.info("Road2HireModel: loading ESCO knowledge graph …")
        from AI.Knowledge_Graph.esco_graph import get_esco_graph

        self._graph = get_esco_graph(taxonomy=self._taxonomy)

        # Vocabulary is built lazily on the first predict call; subsequent
        # calls reuse the cached list (~13,939 preferred + alt labels).
        self._esco_vocab: list[str] | None = None

        logger.info("Road2HireModel: initialisation complete.")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def predict(self, pdf_path: str | Path) -> dict[str, Any]:
        """Process a PDF résumé and return a structured intelligence result.

        Parameters
        ----------
        pdf_path:
            Absolute or relative path to a PDF résumé.

        Returns
        -------
        dict with keys:
            status, pipeline_version, source_file, page_count,
            extraction_status, sections, section_count, detected_headings,
            extracted_skills, skill_count, esco_mappings, mapped_skill_count,
            occupation_matches, candidate_profile, profile_validation_errors,
            warnings, errors.

        Raises
        ------
        FileNotFoundError
            When the PDF does not exist.
        ValueError
            When the path does not point to a ``.pdf`` file.
        """
        path = Path(pdf_path)

        # Input validation — let existing extractors raise, but surface
        # descriptive errors early so callers get clear messages.
        if not path.exists():
            raise FileNotFoundError(f"Resume file not found: {path}")
        if path.suffix.casefold() != ".pdf":
            raise ValueError(
                f"Expected a .pdf file, got: {path.suffix!r}"
            )

        pipeline_warnings: list[str] = []
        pipeline_errors: list[str] = []

        # 1. Resume processing (text extraction + section detection)
        resume_data = self._run_resume_processing(path, pipeline_warnings)

        # 2. Skill extraction with full ESCO vocabulary
        extracted = self._run_skill_extraction(resume_data, pipeline_warnings)

        # 3. ESCO normalisation
        esco_mappings = self._run_esco_normalisation(extracted["skills"])

        # 4. Semantic embeddings (embed ESCO preferred labels for mapped skills)
        embedding_data = self._run_embeddings(esco_mappings, pipeline_warnings)

        # 5. Occupation matching via knowledge graph
        occupation_matches = self._match_occupations(esco_mappings)

        # 6. Candidate profile construction
        candidate_profile = self._build_profile(
            resume_data, esco_mappings, embedding_data
        )

        # 7. Profile validation
        from AI.Candidate_Profile.profile_validator import validate_candidate_profile

        profile_validation_errors = validate_candidate_profile(candidate_profile)
        if profile_validation_errors:
            pipeline_warnings.append(
                f"Profile validation raised {len(profile_validation_errors)} issue(s)."
            )

        # 8. Determine overall status
        status = "success"
        if resume_data.get("extraction_status") == "needs_ocr":
            status = "warning"
            pipeline_warnings.append(
                "PDF text could not be extracted cleanly; OCR may be required."
            )
        if pipeline_errors:
            status = "error"

        return {
            "status": status,
            "pipeline_version": PIPELINE_VERSION,
            "source_file": resume_data.get("source_file"),
            "page_count": resume_data.get("page_count", 0),
            "extraction_status": resume_data.get("extraction_status"),
            "sections": resume_data.get("sections", {}),
            "section_count": resume_data.get("section_count", 0),
            "detected_headings": resume_data.get("detected_headings", []),
            "extracted_skills": extracted.get("skills", []),
            "skill_count": extracted.get("skill_count", 0),
            "esco_mappings": esco_mappings,
            "mapped_skill_count": len(esco_mappings),
            "occupation_matches": occupation_matches[: self._top_n],
            "candidate_profile": candidate_profile,
            "profile_validation_errors": profile_validation_errors,
            "warnings": pipeline_warnings,
            "errors": pipeline_errors,
        }

    def detect_skill_gap(
        self,
        resume_or_profile: str | Path | dict[str, Any],
        target_occupation: str,
        essential_weight: float = 0.75,
        optional_weight: float = 0.25,
    ) -> dict[str, Any]:
        """Detect skill gaps between a candidate and a target ESCO occupation.

        Parameters
        ----------
        resume_or_profile:
            Either a path to a resume PDF, a prediction dictionary from
            ``model.predict()``, or a ``CandidateProfile`` dictionary.
        target_occupation:
            ESCO occupation concept URI, preferred label, or alternative label.
        essential_weight:
            Weight for essential skills (default 0.75).
        optional_weight:
            Weight for optional skills (default 0.25).

        Returns
        -------
        SkillGapReport dictionary.
        """
        from AI.Skill_Gap.skill_gap_detector import SkillGapDetector

        candidate_profile: dict[str, Any]
        if isinstance(resume_or_profile, (str, Path)):
            p = Path(resume_or_profile)
            if p.suffix.casefold() == ".pdf" and p.exists():
                pred = self.predict(p)
                candidate_profile = pred["candidate_profile"]
            else:
                candidate_profile = {"skills": []}
        elif isinstance(resume_or_profile, dict):
            if "candidate_profile" in resume_or_profile:
                candidate_profile = resume_or_profile["candidate_profile"]
            else:
                candidate_profile = resume_or_profile
        else:
            candidate_profile = {"skills": []}

        detector = SkillGapDetector(
            graph=self._graph,
            taxonomy=self._taxonomy,
            essential_weight=essential_weight,
            optional_weight=optional_weight,
        )
        return detector.detect_gap(candidate_profile, target_occupation)

    # ------------------------------------------------------------------
    # Private pipeline steps
    # ------------------------------------------------------------------

    def _run_resume_processing(
        self,
        path: Path,
        pipeline_warnings: list[str],
    ) -> dict[str, Any]:
        """Extract text and detect sections from the PDF."""
        from AI.Resume_Processing.resume_pipeline import process_resume

        resume_data: dict[str, Any] = process_resume(path)

        if not resume_data.get("text", "").strip():
            pipeline_warnings.append(
                "No readable text found in the PDF. "
                "The document may require OCR."
            )

        return resume_data

    def _run_skill_extraction(
        self,
        resume_data: dict[str, Any],
        pipeline_warnings: list[str],
    ) -> dict[str, Any]:
        """Match vocabulary terms against resume sections.

        Uses the full ESCO preferred + alternative label vocabulary
        (~13,939 concepts).  The vocabulary is built once and cached.
        """
        from AI.Skill_Extraction.skill_extractor import (
            extract_skills,
            load_esco_skill_vocabulary,
        )

        if self._esco_vocab is None:
            # Include alternative labels so e.g. "Python" resolves to
            # "Python (computer programming)" via its ESCO alt-label.
            self._esco_vocab = load_esco_skill_vocabulary(
                taxonomy=self._taxonomy,
                include_alt_labels=True,
            )

        extracted = extract_skills(resume_data, vocabulary=self._esco_vocab)

        if extracted.get("skill_count", 0) == 0:
            pipeline_warnings.append(
                "No skills were detected in the resume. "
                "The document may be image-based or the vocabulary may not "
                "cover the skills present."
            )

        return extracted

    def _run_esco_normalisation(
        self,
        raw_skills: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Normalise extracted skill names to canonical ESCO concepts."""
        from AI.Skill_Extraction.skill_taxonomy_mapper import (
            map_skills_to_complete_esco,
        )

        return map_skills_to_complete_esco(raw_skills, taxonomy=self._taxonomy)

    def _run_embeddings(
        self,
        esco_mappings: list[dict[str, Any]],
        pipeline_warnings: list[str],
    ) -> dict[str, Any]:
        """Generate semantic embeddings for all mapped skills.

        Embeds the ESCO preferred label when available; falls back to the
        raw extracted skill name otherwise.
        """
        from AI.Skill_Extraction.skill_embeddings import generate_skill_embeddings

        skill_names = [
            m.get("ESCO_Skill_Name") or m.get("skill", "")
            for m in esco_mappings
            if isinstance(m, dict) and (m.get("ESCO_Skill_Name") or m.get("skill"))
        ]
        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_names: list[str] = []
        for name in skill_names:
            if name and name not in seen:
                seen.add(name)
                unique_names.append(name)

        if not unique_names:
            pipeline_warnings.append("No skill names available for embedding generation.")
            return {
                "model_name": "sentence-transformers/all-MiniLM-L6-v2",
                "embedding_dimension": 384,
                "skills": [],
            }

        return generate_skill_embeddings(unique_names)

    def _match_occupations(
        self,
        esco_mappings: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Rank ESCO occupations by their overlap with the candidate's skills.

        For every ESCO-mapped skill URI the graph is queried for related
        occupations.  Occupations are ranked by the number of supporting
        skills, with essential-skill matches weighted in the tie-break.
        """
        occ_scores: dict[str, dict[str, Any]] = {}

        for skill in esco_mappings:
            skill_uri = skill.get("ESCO_Skill_Id")
            if not skill_uri:
                continue

            try:
                occupations = self._graph.get_occupations_for_skill(skill_uri)
            except Exception:  # noqa: BLE001
                logger.debug(
                    "get_occupations_for_skill failed for %s", skill_uri, exc_info=True
                )
                continue

            for occ in occupations:
                uri = occ.get("occupation_uri", "")
                if not uri:
                    continue

                if uri not in occ_scores:
                    occ_scores[uri] = {
                        "occupation_uri": uri,
                        "occupation_label": occ.get("occupation_label", ""),
                        "score": 0,
                        "essential_count": 0,
                        "optional_count": 0,
                        "supporting_skills": [],
                    }

                entry = occ_scores[uri]
                entry["score"] += 1

                rel = occ.get("relation_type", "")
                if rel == "essential":
                    entry["essential_count"] += 1
                elif rel == "optional":
                    entry["optional_count"] += 1

                raw_name = skill.get("ESCO_Skill_Name") or skill.get("skill", "")
                if raw_name and raw_name not in entry["supporting_skills"]:
                    entry["supporting_skills"].append(raw_name)

        # Sort by (score desc, essential_count desc)
        ranked = sorted(
            occ_scores.values(),
            key=lambda x: (x["score"], x["essential_count"]),
            reverse=True,
        )
        return ranked

    def _build_profile(
        self,
        resume_data: dict[str, Any],
        esco_mappings: list[dict[str, Any]],
        embedding_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Construct a CandidateProfile-compatible dict from pipeline outputs.

        Uses ESCO-mapped skills (full vocabulary) rather than the small
        9-skill vocabulary used by the legacy ``build_candidate_profile``.
        The returned structure is validated by ``validate_candidate_profile``.
        """
        from AI.Candidate_Profile.profile_builder import assemble_candidate_profile

        # Build a lookup: (esco preferred label or raw name).casefold() → embedding
        embedding_lookup: dict[str, list[float]] = {
            item["skill"].casefold(): item["embedding"]
            for item in embedding_data.get("skills", [])
            if isinstance(item, dict) and isinstance(item.get("embedding"), list)
        }

        profile_skills: list[dict[str, Any]] = []
        for m in esco_mappings:
            if not isinstance(m, dict):
                continue
            embed_key = (m.get("ESCO_Skill_Name") or m.get("skill", "")).casefold()
            profile_skills.append(
                {
                    **m,
                    "embedding": embedding_lookup.get(embed_key),
                }
            )

        return assemble_candidate_profile(
            resume_data=resume_data,
            profile_skills=profile_skills,
            embedding_data=embedding_data,
            pipeline_version=PIPELINE_VERSION,
        )


# ---------------------------------------------------------------------------
# Module-level singleton helpers
# ---------------------------------------------------------------------------

_model_singleton: Road2HireModel | None = None


def get_road2hire_model(
    top_n_occupations: int = _DEFAULT_TOP_N_OCCUPATIONS,
) -> Road2HireModel:
    """Return a module-level cached ``Road2HireModel`` instance.

    Equivalent to constructing ``Road2HireModel()`` once and reusing it.
    Not thread-safe; intended for single-process, single-thread use.
    """
    global _model_singleton  # noqa: PLW0603
    if _model_singleton is None:
        _model_singleton = Road2HireModel(top_n_occupations=top_n_occupations)
    return _model_singleton

