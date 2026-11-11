"""Extract skills from processed Road2Hire resume data."""

import json
import re
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILL_GRAPH_PATH = PROJECT_ROOT / "AI" / "Knowledge_Graph" / "skill_graph_v1.json"

# Resume sections in which skills may appear.
SKILL_SECTIONS = {
    "skills",
    "experience",
    "projects",
    "summary",
    "education",
    "certifications",
}


# Explicit aliases for normalizing common skill-name variations.
SKILL_SYNONYMS = {
    "python": "Python",
    "ml": "Machine Learning",
    "machine learning": "Machine Learning",
    "sklearn": "Scikit-learn",
    "scikit learn": "Scikit-learn",
    "scikit-learn": "Scikit-learn",
    "numpy": "NumPy",
    "pandas": "Pandas",
}




class SkillMatcher:
    """Trie-based, case-insensitive whole-phrase skill matcher."""

    def __init__(
        self,
        vocabulary: list[str],
        synonyms: dict[str, str] | None = None,
    ) -> None:
        synonym_map = synonyms if synonyms is not None else SKILL_SYNONYMS
        reverse_synonyms: dict[str, list[str]] = {}

        for alias, canonical in synonym_map.items():
            if isinstance(alias, str) and isinstance(canonical, str):
                reverse_synonyms.setdefault(canonical.casefold(), []).append(alias)

        self.trie: dict[str, Any] = {}

        for skill in vocabulary:
            if not isinstance(skill, str) or not skill.strip():
                continue

            canonical_name = skill.strip()
            variations = [canonical_name]
            variations.extend(
                reverse_synonyms.get(canonical_name.casefold(), [])
            )

            for variation in dict.fromkeys(variations):
                node = self.trie

                for character in variation.casefold():
                    node = node.setdefault(character, {})

                registered = node.setdefault("__skills__", [])
                if canonical_name not in registered:
                    registered.append(canonical_name)

    @staticmethod
    def _is_word_character(character: str) -> bool:
        return character == "_" or character.isalnum()

    def find_in_text(self, text: str) -> dict[str, list[dict[str, Any]]]:
        """Find skill occurrences while retaining original text offsets."""
        matches: dict[str, list[dict[str, Any]]] = {}
        text_length = len(text)

        for start in range(text_length):
            if (
                start > 0
                and self._is_word_character(text[start - 1])
            ):
                continue

            node = self.trie

            for end in range(start, text_length):
                folded_character = text[end].casefold()
                failed = False

                # Consume a complete original character before checking
                # terminal matches, preserving original string offsets.
                for folded_part in folded_character:
                    if folded_part not in node:
                        failed = True
                        break
                    node = node[folded_part]

                if failed:
                    break

                if "__skills__" not in node:
                    continue

                if (
                    end + 1 < text_length
                    and self._is_word_character(text[end + 1])
                ):
                    continue

                occurrence = {
                    "text": text[start:end + 1],
                    "start": start,
                    "end": end + 1,
                }

                for canonical_name in node["__skills__"]:
                    matches.setdefault(canonical_name, []).append(
                        occurrence.copy()
                    )

        return matches


_MATCHER_CACHE: dict[
    tuple[tuple[str, ...], tuple[tuple[str, str], ...]],
    SkillMatcher,
] = {}


def get_skill_matcher(
    vocabulary: list[str],
    synonyms: dict[str, str] | None = None,
) -> SkillMatcher:
    """Return a cached matcher keyed by complete vocabulary contents."""
    valid_vocabulary = tuple(
        name.strip()
        for name in vocabulary
        if isinstance(name, str) and name.strip()
    )

    synonym_map = synonyms if synonyms is not None else SKILL_SYNONYMS
    synonym_key = tuple(sorted(
        (alias.casefold(), canonical)
        for alias, canonical in synonym_map.items()
        if isinstance(alias, str) and isinstance(canonical, str)
    ))

    cache_key = (valid_vocabulary, synonym_key)
    matcher = _MATCHER_CACHE.get(cache_key)

    if matcher is None:
        matcher = SkillMatcher(
            list(valid_vocabulary),
            synonyms=synonym_map,
        )

        if len(_MATCHER_CACHE) >= 16:
            _MATCHER_CACHE.clear()

        _MATCHER_CACHE[cache_key] = matcher

    return matcher

def normalize_skill_name(
    skill_name: str,
    vocabulary: list[str] | None = None,
) -> str | None:
    """Return the canonical skill name for a recognized skill or alias."""
    if not isinstance(skill_name, str) or not skill_name.strip():
        return None

    cleaned = " ".join(skill_name.strip().split())
    key = cleaned.casefold()

    if key in SKILL_SYNONYMS:
        return SKILL_SYNONYMS[key]

    if vocabulary is None:
        vocabulary = load_skill_vocabulary()

    canonical_names = {
        name.casefold(): name
        for name in vocabulary
        if isinstance(name, str) and name.strip()
    }

    return canonical_names.get(key)


def load_skill_vocabulary(
    graph_path: str | Path = SKILL_GRAPH_PATH,
) -> list[str]:
    """Load the initial skill vocabulary from the existing knowledge graph."""
    path = Path(graph_path)

    with path.open("r", encoding="utf-8") as file:
        graph = json.load(file)

    return [
        item["name"].strip()
        for item in graph.get("skills", [])
        if isinstance(item, dict)
        and isinstance(item.get("name"), str)
        and item["name"].strip()
    ]


def _find_skill_occurrences(
    text: str,
    skill: str,
) -> list[dict[str, Any]]:
    """Find case-insensitive whole-phrase matches."""
    pattern = re.compile(
        rf"(?<!\w){re.escape(skill)}(?!\w)",
        flags=re.IGNORECASE,
    )

    return [
        {
            "text": match.group(0),
            "start": match.start(),
            "end": match.end(),
        }
        for match in pattern.finditer(text)
    ]


def _get_skill_variations(canonical_name: str) -> list[str]:
    """Return the canonical name and aliases that normalize to it."""
    variations = [canonical_name]

    for alias, canonical in SKILL_SYNONYMS.items():
        if canonical.casefold() == canonical_name.casefold():
            variations.append(alias)

    # Remove duplicate spellings without changing order.
    return list(dict.fromkeys(variations))


def extract_skills(
    resume_data: dict[str, Any],
    vocabulary: list[str] | None = None,
) -> dict[str, Any]:
    """
    Extract vocabulary-based skill matches from processed resume data.

    Expected input is the dictionary returned by process_resume().
    Each skill records its source sections and text occurrences.
    Canonical names and configured synonyms are both recognized.
    """
    if not isinstance(resume_data, dict):
        raise TypeError("resume_data must be a dictionary.")

    sections = resume_data.get("sections", {})
    if not isinstance(sections, dict):
        raise ValueError("resume_data['sections'] must be a dictionary.")

    if vocabulary is None:
        vocabulary = load_skill_vocabulary()

    matcher = get_skill_matcher(vocabulary)
    extracted: dict[str, dict[str, Any]] = {}

    for section_name, section_text in sections.items():
        if section_name not in SKILL_SECTIONS:
            continue

        if not isinstance(section_text, str):
            continue

        section_matches = matcher.find_in_text(section_text)

        for canonical_name, occurrences in section_matches.items():
            if not occurrences:
                continue

            unique_occurrences = {
                (item["start"], item["end"]): item
                for item in occurrences
            }

            sorted_occurrences = [
                unique_occurrences[position]
                for position in sorted(unique_occurrences)
            ]

            key = canonical_name.casefold()

            if key not in extracted:
                extracted[key] = {
                    "skill": canonical_name,
                    "source_sections": [],
                    "occurrences": [],
                }

            if section_name not in extracted[key]["source_sections"]:
                extracted[key]["source_sections"].append(section_name)

            for occurrence in sorted_occurrences:
                extracted[key]["occurrences"].append({
                    "section": section_name,
                    **occurrence,
                })

    return {
        "source_file": resume_data.get("source_file"),
        "extraction_method": "knowledge_graph_keyword_matching",
        "skills": list(extracted.values()),
        "skill_count": len(extracted),
    }


def load_esco_skill_vocabulary(
    taxonomy=None,
    include_alt_labels: bool = False,
) -> list[str]:
    """Load the complete vocabulary from the ESCO taxonomy."""
    from AI.Skill_Extraction.esco_taxonomy import get_esco_taxonomy

    tax = taxonomy if taxonomy is not None else get_esco_taxonomy()
    return tax.get_vocabulary(include_alt_labels=include_alt_labels)
