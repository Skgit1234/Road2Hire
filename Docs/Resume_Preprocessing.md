# Resume Preprocessing Pipeline

## 1. Objective

The Road2Hire resume preprocessing pipeline extracts readable text from PDF resumes, cleans the extracted text, detects major resume sections, and generates a structured intermediate representation for downstream skill extraction.

## 2. Pipeline Components

- `AI/Resume_Processing/pdf_extractor.py`: Extracts page-level text from PDF files and normalizes whitespace.
- `AI/Resume_Processing/section_detector.py`: Detects common resume headings using rule-based matching.
- `AI/Resume_Processing/resume_pipeline.py`: Combines extraction and section detection and exports structured JSON.
- `tests/AI/test_resume_processing.py`: Contains automated tests for the pipeline.

## 3. PDF Text Extraction

PyMuPDF is used to extract text from digitally generated PDF resumes.

The extractor:

- Processes PDF pages individually.
- Preserves page-level text and page counts.
- Removes null characters and normalizes whitespace.
- Reports missing files, unsupported file extensions, encrypted PDFs, and unreadable documents.
- Flags PDFs with no extractable text for further OCR processing.

### Limitation

The current implementation does not perform OCR. A PDF containing no extractable text receives the status `needs_ocr`. PDFs with partial or poor-quality text extraction may require additional quality checks.

## 4. Text Cleaning Decisions

- Normalize Windows and carriage-return line endings.
- Replace repeated spaces and tabs with a single space.
- Remove unnecessary spaces around line breaks.
- Reduce three or more consecutive line breaks to two.
- Preserve meaningful line breaks and paragraph separation.
- Remove null characters.

The pipeline does not intentionally remove meaningful resume content such as skill names, qualifications, project descriptions, or work experience.

## 5. Section Detection

The initial detector uses predefined heading aliases to identify:

- Contact Information
- Education
- Experience
- Skills
- Projects
- Certifications

Section detection is rule-based and depends on recognizable headings. Unusual headings, headings embedded in paragraphs, and resumes with complex layouts may not be detected correctly.

Contact information is identified only when a recognized heading is present; automatic extraction of names, email addresses, phone numbers, and addresses is not yet implemented.

## 6. Structured Intermediate Output

The pipeline returns:

- Source filename
- Page count
- Character count
- Extraction status
- Cleaned full text
- Page-level text
- Detected section content
- Detected headings
- Detected section names and section count
- Section detection method
- Pipeline version

The output can be exported to UTF-8 JSON for evaluation and downstream processing.

## 7. Evaluation and Testing

### Automated Tests

Automated tests cover:

- Text cleaning
- Text extraction from a generated PDF
- Empty PDF handling
- Missing PDF handling
- Section detection
- Pipeline execution and JSON export

**Test command:**

```cmd
python -m unittest discover -s tests\AI -p "test_*.py" -v
```

**Result:** All 6 automated tests passed.

### Initial Sample Resume Evaluation

A fictional, single-page PDF resume was generated to evaluate the end-to-end pipeline. It contains a professional summary, education, experience, skills, projects, and certifications.

| Evaluation item      | Result                               |
| -------------------- | ------------------------------------ |
| Input format         | Text-based PDF                       |
| Pages processed      | 1                                    |
| Extracted characters | 667                                  |
| Extraction status    | Success                              |
| Expected sections    | 6                                    |
| Detected sections    | 6                                    |
| Section detection    | Passed for all six expected sections |

**Detected sections:** Summary, Education, Experience, Skills, Projects, and Certifications.

The pipeline extracted the PDF text and correctly identified all six expected sections in this sample.

**Evaluation scope:** This is an initial evaluation using a generated, single-page resume with a simple layout. It does not establish general extraction accuracy across real resumes or complex layouts. Further evaluation is required for multi-column documents, tables, scanned PDFs, alternate headings, headers, and footers.

## 8. Dependencies

The PDF extraction dependency is recorded in `requirements.txt`.

Install project dependencies using:

```cmd
python -m pip install -r requirements.txt
```

## 9. Known Limitations and Future Improvements

- Add OCR support for scanned resumes.
- Evaluate extraction quality on representative resumes with varied layouts.
- Improve section detection for alternate and missing headings.
- Add dedicated contact-information extraction.
- Assess multi-column layouts, tables, headers, and footers.
- Record evaluation findings and known failure cases.

## 10. Privacy Considerations

Use authorized evaluation resumes and avoid committing resumes containing personal information. Prefer synthetic or anonymized samples for automated tests.
