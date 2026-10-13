
"""Tests for the Road2Hire resume preprocessing pipeline."""

import tempfile
import unittest
from pathlib import Path

import pymupdf

from AI.Resume_Processing.pdf_extractor import (
    clean_text,
    extract_resume_text,
)
from AI.Resume_Processing.section_detector import detect_resume_sections
from AI.Resume_Processing.resume_pipeline import (
    process_resume,
    save_resume_json,
)


class TestResumeProcessing(unittest.TestCase):

    def create_pdf(self, path: Path, text: str = "") -> None:
        """Create a small temporary PDF for testing."""
        document = pymupdf.open()
        page = document.new_page()
        if text:
            page.insert_text((72, 72), text)
        document.save(path)
        document.close()

    def test_clean_text(self):
        self.assertEqual(
            clean_text("Skills   Python\n\n\nExperience"),
            "Skills Python\n\nExperience",
        )

    def test_extract_text_from_pdf(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "resume.pdf"
            self.create_pdf(pdf_path, "Skills\nPython SQL")

            result = extract_resume_text(pdf_path)

            self.assertEqual(result["extraction_status"], "success")
            self.assertIn("Python", result["text"])
            self.assertEqual(result["page_count"], 1)

    def test_empty_pdf_needs_ocr(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "empty.pdf"
            self.create_pdf(pdf_path)

            result = extract_resume_text(pdf_path)

            self.assertEqual(result["extraction_status"], "needs_ocr")
            self.assertEqual(result["text"], "")

    def test_missing_pdf_raises_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_path = Path(temp_dir) / "missing.pdf"

            with self.assertRaises(FileNotFoundError):
                extract_resume_text(missing_path)

    def test_section_detection(self):
        text = (
            "Alex Kumar\n"
            "Skills\nPython, SQL\n"
            "Education\nB.Tech Computer Science\n"
            "Projects\nResume Analyzer"
        )

        result = detect_resume_sections(text)

        self.assertEqual(result["section_count"], 3)
        self.assertIn("Python, SQL", result["sections"]["skills"])
        self.assertIn(
            "B.Tech Computer Science",
            result["sections"]["education"],
        )
        self.assertIn("Resume Analyzer", result["sections"]["projects"])

    def test_pipeline_and_json_export(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "resume.pdf"
            output_path = Path(temp_dir) / "output" / "resume.json"

            self.create_pdf(
                pdf_path,
                "Alex Kumar\nSkills\nPython SQL\nEducation\nB.Tech",
            )

            result = process_resume(pdf_path)
            saved_path = save_resume_json(result, output_path)

            self.assertTrue(saved_path.exists())
            self.assertIn("skills", result["sections"])
            self.assertEqual(result["pipeline_version"], "1.0.0")


if __name__ == "__main__":
    unittest.main()
