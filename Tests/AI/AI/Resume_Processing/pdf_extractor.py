
"""Extract readable text from PDF resumes using PyMuPDF."""

from pathlib import Path
import re
from typing import Any

import pymupdf


def clean_text(text: str) -> str:
    """Normalize whitespace while preserving meaningful line breaks."""
    text = text.replace("\x00", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_resume_text(pdf_path: str | Path) -> dict[str, Any]:
    """
    Extract and clean text from a PDF resume.

    Returns metadata, page-level text, cleaned text, and extraction status.
    Scanned/image-only PDFs are flagged for OCR rather than silently
    treated as successfully extracted.
    """
    path = Path(pdf_path)

    if not path.exists():
        raise FileNotFoundError(f"Resume PDF not found: {path}")

    if not path.is_file():
        raise ValueError(f"Expected a PDF file, got a directory: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf file: {path}")

    page_results: list[dict[str, Any]] = []
    all_pages: list[str] = []

    try:
        with pymupdf.open(path) as document:
            if document.is_encrypted:
                raise ValueError("Encrypted PDFs are not supported.")

            for page_number, page in enumerate(document, start=1):
                raw_text = page.get_text("text", sort=True)
                page_text = clean_text(raw_text)

                page_results.append(
                    {
                        "page": page_number,
                        "text": page_text,
                        "character_count": len(page_text),
                    }
                )
                all_pages.append(page_text)

    except (FileNotFoundError, ValueError):
        raise
    except Exception as exc:
        raise ValueError(f"Unable to read PDF '{path.name}': {exc}") from exc

    cleaned_text = clean_text("\n\n".join(all_pages))
    has_text = bool(cleaned_text)

    return {
        "source_file": path.name,
        "page_count": len(page_results),
        "pages": page_results,
        "text": cleaned_text,
        "character_count": len(cleaned_text),
        "extraction_status": (
            "success" if has_text else "needs_ocr"
        ),
    }
