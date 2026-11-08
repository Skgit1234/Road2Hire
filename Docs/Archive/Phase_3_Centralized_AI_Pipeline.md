# Phase 3 — Centralized Road2Hire AI Prediction Pipeline

## 1. Overview

**Project:** Road2Hire  
**Module:** AI/ML  
**Phase:** 3 — Central Model Pipeline  
**Status:** Completed  
**Implementation Commit:** `71c6d27`  
**Branch:** `main`

### Objective

Develop a centralized AI/ML prediction pipeline that integrates the existing resume intelligence modules into a single processing workflow.

The pipeline accepts a candidate's resume PDF, processes its contents, extracts and normalizes skills, identifies relevant ESCO occupations, and generates a structured candidate profile.

The purpose is to provide a single entry point for the Road2Hire AI/ML resume intelligence system instead of requiring individual modules to be executed separately.

---

## 2. Implementation Scope

The following components were integrated:

1. PDF resume validation and text extraction.
2. Resume section detection.
3. Skill extraction.
4. ESCO skill normalization.
5. Semantic skill matching.
6. ESCO occupation matching through the knowledge graph.
7. Candidate profile generation.
8. Candidate profile validation.
9. Pipeline error handling.
10. Integration and unit testing.

The implementation reuses existing AI/ML modules instead of duplicating their functionality.

---

## 3. Architecture

### Central Pipeline Architecture

The central pipeline connects the existing resume intelligence components.

```text
                 Resume PDF
                     |
                     v
             PDF Validation
                     |
                     v
              Text Extraction
                     |
                     v
             Section Detection
                     |
                     v
              Skill Extraction
                     |
                     v
             ESCO Normalization
                     |
                     v
             Semantic Matching
                     |
                     v
          ESCO Occupation Matching
                     |
                     v
          Candidate Profile Builder
                     |
                     v
          Candidate Profile Validator
                     |
                     v
             Structured Output
```

### Processing Description

**Step 1 — PDF Validation**

The pipeline receives a resume PDF and validates the input before processing.

**Step 2 — Text Extraction**

The existing PDF extraction module extracts text from the uploaded resume.

**Step 3 — Section Detection**

The extracted text is analyzed to identify sections such as:

- Professional Summary
- Education
- Experience
- Skills
- Projects
- Certifications

**Step 4 — Skill Extraction**

The skill extraction module identifies technical and professional skills from the extracted resume content.

**Step 5 — ESCO Normalization**

Extracted skills are mapped to standardized ESCO skill concepts.

The mapping provides standardized skill information, including:

- ESCO Skill ID
- ESCO Skill Name
- ESCO Skill Type
- ESCO Reuse Level
- ESCO Mapping Type

**Step 6 — Semantic Matching**

The semantic matching module uses the existing Sentence Transformers model to generate and compare skill embeddings.

The implementation uses:

`sentence-transformers/all-MiniLM-L6-v2`

Embedding dimension: **384**

The pretrained model is reused; custom model training or fine-tuning is not part of this phase.

**Step 7 — Occupation Matching**

The occupation matching component uses the ESCO knowledge graph to identify occupations related to the candidate's normalized skills.

The matching output includes:

- Occupation URI
- Occupation label
- Matching score
- Essential skill count
- Optional skill count
- Supporting skills

**Step 8 — Candidate Profile Generation**

The candidate profile builder combines the extracted and processed resume information into a structured candidate profile.

**Step 9 — Profile Validation**

The profile validator checks the generated profile against the existing candidate profile schema.

**Step 10 — Structured Output**

The pipeline returns a structured result containing processing information, extracted skills, ESCO mappings, occupation matches, candidate profile information, validation errors, warnings, and pipeline errors.

---

## 4. Implementation Files

### New Files

| File | Purpose |
|---|---|
| `AI/road2hire_model.py` | Central AI/ML prediction pipeline |
| `Tests/AI/test_road2hire_model.py` | Tests for the central prediction pipeline |

### Integrated Existing Modules

| Module | Responsibility |
|---|---|
| `AI/Resume_Processing/pdf_extractor.py` | PDF text extraction |
| `AI/Resume_Processing/section_detector.py` | Resume section detection |
| `AI/Resume_Processing/resume_pipeline.py` | Resume processing workflow |
| `AI/Skill_Extraction/skill_extractor.py` | Skill extraction |
| `AI/Skill_Extraction/skill_taxonomy_mapper.py` | Skill normalization |
| `AI/Skill_Extraction/esco_taxonomy.py` | ESCO taxonomy integration |
| `AI/Semantic_Matching/semantic_matcher.py` | Semantic skill matching |
| `AI/Knowledge_Graph/esco_graph.py` | ESCO occupation and skill graph |
| `AI/Knowledge_Graph/skill_graph_matcher.py` | Knowledge graph skill matching |
| `AI/Candidate_Profile/profile_builder.py` | Candidate profile generation |
| `AI/Candidate_Profile/profile_validator.py` | Candidate profile validation |

---

## 5. Structured Pipeline Output

The central pipeline returns a structured result with the following information:

| Field | Description |
|---|---|
| `status` | Overall processing status |
| `pipeline_version` | Pipeline version |
| `source_file` | Input resume file |
| `page_count` | Number of PDF pages |
| `extraction_status` | PDF extraction result |
| `sections` | Detected resume sections |
| `section_count` | Number of detected sections |
| `detected_headings` | Identified section headings |
| `extracted_skills` | Extracted skill information |
| `skill_count` | Number of extracted skills |
| `esco_mappings` | Normalized ESCO skill mappings |
| `mapped_skill_count` | Number of mapped skills |
| `occupation_matches` | Matching ESCO occupations |
| `candidate_profile` | Structured candidate profile |
| `profile_validation_errors` | Profile validation errors |
| `warnings` | Non-fatal processing warnings |
| `errors` | Pipeline processing errors |

The result supports downstream integration with the Road2Hire backend and frontend.

---

## 6. Error Handling

The central pipeline handles different processing scenarios, including:

- Invalid or missing PDF input.
- Empty extracted resume text.
- Missing or unavailable resume sections.
- Skills that cannot be mapped to ESCO.
- No matching occupations.
- Embedding-related processing errors.
- Candidate profile validation errors.

Warnings and errors are included in the structured output to make processing results easier to inspect.

---

## 7. Testing and Validation

A dedicated test file was created:

`Tests/AI/test_road2hire_model.py`

It contains 40 tests covering the central pipeline and its integration with the existing modules.

### Test Execution

New pipeline tests:

```powershell
python -m pytest Tests/AI/test_road2hire_model.py -v
```

**Result:** 40 passed.

Complete AI test suite:

```powershell
python -m pytest Tests/AI -v
```

**Result:** 150 passed.

### Test Summary

| Test Category | Result |
|---|---|
| Central pipeline tests | 40 passed |
| Existing AI tests | 110 passed |
| Total AI tests | 150 passed |
| Failed tests | 0 |

---

## 8. Sample Resume Execution

The pipeline was manually tested using:

`Tests/AI/sample_resume.pdf`

Execution:

```powershell
python -c "from AI.road2hire_model import Road2HireModel; import json; model = Road2HireModel(); result = model.predict('Tests/AI/sample_resume.pdf'); print(json.dumps(result, indent=2, default=str))"
```

### Observed Results

- PDF extraction completed successfully.
- Six resume sections were detected.
- Six skills were extracted.
- ESCO skill normalization was successful for mapped skills.
- Sentence Transformer embeddings were generated.
- Occupation matching returned ten occupation results.
- Candidate profile validation returned no errors.
- Pipeline warnings were empty.
- Pipeline errors were empty.

### Example Occupation Matches

| Occupation | Matching Score |
|---|---:|
| Data Engineer | 3 |
| Mathematician | 3 |
| ICT Application Configurator | 3 |
| ICT Application Developer | 3 |
| Software Developer | 3 |
| IoT Developer | 2 |
| Computer Vision Engineer | 2 |

These are sample results from the test resume, not final career recommendations.

The occupation matching score is based on the current skill-matching implementation. It should not be interpreted as a probability or a candidate's career-readiness percentage.

---

## 9. Current Limitations and Future Improvements

The following improvements are outside the scope of Phase 3 and can be addressed in subsequent phases:

1. Enhance candidate profile fields and structured information.
2. Implement skill gap analysis.
3. Improve occupation ranking and matching relevance.
4. Introduce confidence scores for skill extraction and normalization.
5. Develop career readiness prediction.
6. Add SHAP-based explainability.
7. Develop personalized learning recommendations.
8. Integrate RAG-based career guidance.
9. Optimize the output for backend API responses, including avoiding unnecessary embedding-vector payloads.
10. Evaluate the pipeline using real-world resumes and a larger evaluation dataset.

The current implementation uses a sample resume for manual integration validation. Testing on diverse real-world resumes and evaluating extraction quality remain important future tasks.

---

## 10. Git and Repository Status

### Files Added

```text
AI/
    road2hire_model.py

Tests/
    AI/
        test_road2hire_model.py
```

### Commit Information

**Commit message:**

```text
Add centralized Road2Hire AI prediction pipeline
```

**Commit ID:**

```text
71c6d27
```

**Branch:** `main`

**Remote:** `origin/main`

The implementation was successfully committed and pushed to GitHub.

---

## 11. Final Outcome

Phase 3 successfully established a centralized AI/ML prediction pipeline for Road2Hire.

The pipeline integrates the existing resume processing, skill extraction, ESCO normalization, semantic matching, occupation matching, and candidate profile components into one workflow.

It provides a foundation for subsequent AI/ML development, including candidate profile enhancement, skill gap analysis, career readiness prediction, occupation recommendations, and personalized learning roadmaps.

**Phase Status: COMPLETED**

**Validation Status: 150 AI tests passed.**

**Repository Status: Committed and pushed to GitHub.**