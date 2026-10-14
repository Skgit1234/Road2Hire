
"""Combine PDF extraction and section detection into one pipeline."""

import json
from pathlib import Path
from typing import Any

from AI.Resume_Processing.pdf_extractor import extract_resume_text
from AI.Resume_Processing.section_detector import detect_resume_sections


def process_resume(pdf_path: str | Path) -> dict[str, Any]:
    """Extract, clean, and structure a PDF resume."""
    extraction = extract_resume_text(pdf_path)
    section_result = detect_resume_sections(extraction["text"])

    return {
        "source_file": extraction["source_file"],
        "page_count": extraction["page_count"],
        "character_count": extraction["character_count"],
        "extraction_status": extraction["extraction_status"],
        "text": extraction["text"],
        "pages": extraction["pages"],
        "sections": section_result["sections"],
        "detected_headings": section_result["detected_headings"],
        "detected_section_names": section_result["detected_section_names"],
        "section_count": section_result["section_count"],
        "section_detection_method": section_result["detection_method"],
        "pipeline_version": "1.0.0",
    }


def save_resume_json(
    resume_data: dict[str, Any],
    output_path: str | Path,
) -> Path:
    """Save structured resume data as UTF-8 JSON."""
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    with destination.open("w", encoding="utf-8") as file:
        json.dump(resume_data, file, ensure_ascii=False, indent=2)

    return destination
