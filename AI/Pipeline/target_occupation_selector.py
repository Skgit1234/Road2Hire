"""Target Occupation Selection and Resolution Interface (Road2Hire).

Handles resolving target occupations from:
1. Direct CLI query (URI, preferred label, alternative label).
2. Ranked matches from resume intelligence.
3. Interactive console selection with formatted rankings.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

from AI.Pipeline.pipeline_schema import SelectedOccupation

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    """Base exception for Road2Hire pipeline errors."""


class OccupationSelectionError(PipelineError):
    """Raised when an occupation selection is missing, invalid, or cannot be resolved."""

    def __init__(
        self,
        message: str,
        suggested_occupations: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.suggested_occupations: list[dict[str, Any]] = (
            suggested_occupations if suggested_occupations is not None else []
        )


class TargetOccupationSelector:
    """Selects and resolves canonical ESCO occupations for pipeline execution."""

    def __init__(self, taxonomy: Any) -> None:
        self.taxonomy = taxonomy

    def resolve_selection(
        self,
        query: str | None,
        ranked_matches: list[dict[str, Any]],
        interactive: bool = False,
        top_n: int = 10,
        auto_select_top: bool = False,
    ) -> SelectedOccupation:
        """Resolve a target occupation from a query string, auto-selection, or interactive user choice.

        Parameters
        ----------
        query:
            Target occupation concept URI, exact title, or search term.
        ranked_matches:
            List of ranked occupation dictionaries returned by `Road2HireModel.predict()`.
        interactive:
            Whether to prompt user if query is None.
        top_n:
            Number of suggestions to display in interactive mode or error prompts.
        auto_select_top:
            If True and query is None, automatically selects the highest-scoring
            occupation recommendation from ranked_matches without raising an error.

        Returns
        -------
        SelectedOccupation
            Validated and resolved occupation object.

        Raises
        ------
        OccupationSelectionError
            When no occupation is selected or query cannot be resolved.
        """
        # Case 1: An explicit query was passed
        if query and isinstance(query, str) and query.strip():
            return self._resolve_explicit_query(query.strip(), ranked_matches, top_n=top_n)

        # Case 2: Auto-select top recommendation if requested
        if auto_select_top:
            if ranked_matches:
                top_item = ranked_matches[0]
                return SelectedOccupation(
                    occupation_uri=top_item.get("occupation_uri", ""),
                    occupation_label=top_item.get("occupation_label", ""),
                    match_score=top_item.get("score", 0),
                    essential_matched=top_item.get("essential_count", 0),
                    optional_matched=top_item.get("optional_count", 0),
                    supporting_skills=top_item.get("supporting_skills", []),
                    resolution_source="top_recommendation",
                )
            raise OccupationSelectionError(
                "Cannot auto-select top occupation because no occupation recommendations were found for this candidate.",
                suggested_occupations=[],
            )

        # Case 3: Interactive mode requested without query
        if interactive:
            return self._prompt_interactive_selection(ranked_matches, top_n=top_n)

        # Case 4: Non-interactive mode without query -> Must NOT default silently!
        top_suggestions = [
            f"  {idx+1}. {m.get('occupation_label', 'Unknown')} (Score: {m.get('score', 0)}, URI: {m.get('occupation_uri')})"
            for idx, m in enumerate(ranked_matches[:top_n])
        ]
        suggestions_text = "\n".join(top_suggestions) if top_suggestions else "  (No matches found)"

        raise OccupationSelectionError(
            "No target occupation specified. In non-interactive mode, an explicit occupation must be provided.\n"
            "Pass --occupation <title_or_uri> or set auto_select_top_occupation=True to select one of the top suggestions:\n"
            f"{suggestions_text}",
            suggested_occupations=ranked_matches[:top_n],
        )

    def _resolve_explicit_query(
        self,
        query: str,
        ranked_matches: list[dict[str, Any]],
        top_n: int = 10,
    ) -> SelectedOccupation:
        """Resolve a string query against ranked matches or global ESCO taxonomy."""
        cleaned = query.strip()
        lower_cleaned = cleaned.casefold()

        # 1. Check exact match in ranked matches by URI or Label
        for item in ranked_matches:
            uri = item.get("occupation_uri", "")
            label = item.get("occupation_label", "")
            if cleaned == uri or lower_cleaned == label.casefold():
                return SelectedOccupation(
                    occupation_uri=uri,
                    occupation_label=label,
                    match_score=item.get("score", 0),
                    essential_matched=item.get("essential_count", 0),
                    optional_matched=item.get("optional_count", 0),
                    supporting_skills=item.get("supporting_skills", []),
                    resolution_source="suggestion",
                )

        # 2. Check exact concept URI in ESCO taxonomy
        if cleaned in self.taxonomy.occupations:
            occ_obj = self.taxonomy.occupations[cleaned]
            return SelectedOccupation(
                occupation_uri=occ_obj.concept_uri,
                occupation_label=occ_obj.preferred_label,
                resolution_source="direct_uri",
            )

        # 3. Check taxonomy find_occupation (preferred label or alternative label)
        occ_obj = self.taxonomy.find_occupation(cleaned)
        if occ_obj:
            # Check if it was among ranked matches to inherit scores
            matched_item = next(
                (m for m in ranked_matches if m.get("occupation_uri") == occ_obj.concept_uri),
                None,
            )
            return SelectedOccupation(
                occupation_uri=occ_obj.concept_uri,
                occupation_label=occ_obj.preferred_label,
                match_score=matched_item.get("score", 0) if matched_item else 0,
                essential_matched=matched_item.get("essential_count", 0) if matched_item else 0,
                optional_matched=matched_item.get("optional_count", 0) if matched_item else 0,
                supporting_skills=matched_item.get("supporting_skills", []) if matched_item else [],
                resolution_source="taxonomy_lookup",
            )

        # 4. Partial / substring match in ranked matches
        for item in ranked_matches:
            label = item.get("occupation_label", "")
            if lower_cleaned in label.casefold():
                return SelectedOccupation(
                    occupation_uri=item.get("occupation_uri", ""),
                    occupation_label=label,
                    match_score=item.get("score", 0),
                    essential_matched=item.get("essential_count", 0),
                    optional_matched=item.get("optional_count", 0),
                    supporting_skills=item.get("supporting_skills", []),
                    resolution_source="suggestion",
                )

        raise OccupationSelectionError(
            f"Could not resolve target occupation '{query}' to any valid ESCO occupation concept.\n"
            "Please verify the spelling, use canonical ESCO titles (e.g. 'data engineer'), or pass a valid ESCO URI.",
            suggested_occupations=ranked_matches[:top_n],
        )

    def _prompt_interactive_selection(
        self,
        ranked_matches: list[dict[str, Any]],
        top_n: int = 10,
    ) -> SelectedOccupation:
        """Display ranked matches in terminal and prompt user for selection."""
        candidates = ranked_matches[:top_n]
        if not candidates:
            raise OccupationSelectionError(
                "No occupation suggestions were generated from the candidate resume.\n"
                "Please specify an explicit occupation using --occupation <title_or_uri>."
            )

        print("\n" + "=" * 65)
        print(" TOP OCCUPATION SUGGESTIONS (Based on Extracted Resume Skills)")
        print("=" * 65)
        print(f" {'#':<3} | {'Occupation Title':<32} | {'Score':<6} | {'Essential':<9}")
        print("-" * 65)

        for idx, item in enumerate(candidates, start=1):
            title = item.get("occupation_label", "Unknown")[:32]
            score = item.get("score", 0)
            ess = item.get("essential_count", 0)
            print(f" {idx:<3} | {title:<32} | {score:<6} | {ess:<9}")

        print("-" * 65)
        print("Enter 1-10 to select a suggested role, or enter a custom occupation title/URI:")

        try:
            choice = input("\nSelect Target Occupation: ").strip()
        except (EOFError, KeyboardInterrupt):
            raise OccupationSelectionError("Interactive occupation selection was aborted by user.")

        if not choice:
            raise OccupationSelectionError("No occupation selection was entered.")

        # Check numeric index selection
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(candidates):
                item = candidates[idx]
                return SelectedOccupation(
                    occupation_uri=item.get("occupation_uri", ""),
                    occupation_label=item.get("occupation_label", ""),
                    match_score=item.get("score", 0),
                    essential_matched=item.get("essential_count", 0),
                    optional_matched=item.get("optional_count", 0),
                    supporting_skills=item.get("supporting_skills", []),
                    resolution_source="suggestion",
                )
            raise OccupationSelectionError(
                f"Selection '{choice}' is out of range (1 - {len(candidates)})."
            )

        # Fallback to string query resolution
        return self._resolve_explicit_query(choice, ranked_matches)

