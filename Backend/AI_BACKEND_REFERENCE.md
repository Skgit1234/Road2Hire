# Road2Hire AI backend reference

This reference describes the AI and resume-processing functions used by the
current backend integration candidate. It is based on source inspection and
contract tests; it does not claim database-backed or live AI-service behavior.

## Current callable processing

GET /resume/{resume_id}/analysis is the backend entry point for resume
processing. It requires bearer authentication and restricts the resume lookup
to the authenticated user. It reads the stored PDF and calls
AI.Resume_Processing.resume_pipeline.process_resume, then
AI.Skill_Extraction.skill_extractor.extract_skills.

The pipeline accepts a PDF path. PyMuPDF extracts selectable page text and
metadata; OCR is not integrated, so a PDF with no extractable text is reported
as requiring OCR. section_detector.detect_resume_sections uses a fixed set of
heading aliases and rules to group following text into named sections. The
result includes page count, extraction status, text, section text, detected
headings and section names, method metadata, and pipeline version.

The skill extractor scans selected section text for vocabulary entries and
configured aliases from AI/Knowledge_Graph/skill_graph_v1.json. It returns
canonical skill names, source sections, text occurrences, count, and the
knowledge_graph_keyword_matching method identifier. These are keyword
matches; they are not verified employment, education, or skill facts.

The HTTP analysis response is a subset of the internal pipeline result. It
contains resume metadata, extraction status, page count, sections, detected
section names, extracted skills, count, pipeline version, and method name. It
does not include raw source paths or a structured candidate profile.

## Skill-gap matching

GET /skill-gaps/ accepts an owned resume_id, target_role, and one or more
required_skills query values. It extracts candidate skills using the same
local processing functions and applies
AI.Baseline.keyword_baseline.keyword_match, which performs case-insensitive
exact skill-name comparison. The route persists its result and may return a
cached result for identical resume content and request inputs. This is a
rule-based baseline, not semantic or embedding similarity.

## Planned or unavailable capabilities

The frontend's resume-extraction.v1 type describes planned structured fields,
evidence, confidence, and provenance. The backend does not currently emit that
contract. Its PDF text extraction, rule-based section grouping, and vocabulary
matches must remain distinct from that future structured extraction.

There is no registered Career Assistant endpoint in this candidate and no
RAG, retrieval index, chat model client, or LLM orchestration. The frontend
assistant is a local demo with predefined responses. Embedding helpers that
exist elsewhere in the repository are not called by the registered API and
do not make the assistant operational.

Jobs matching is also not registered in the candidate app and is not called
by the frontend API client. The upstream backend branch's Jobs and Assistant
routers are therefore not included as active contracts here.

## Verification boundary

Database-independent API contract tests use dependency overrides and validate
route schemas, authentication behavior, ownership filters, upload validation,
response serialization, generic errors, and CORS. They do not contact
PostgreSQL, run migrations, or verify live model/AI service connectivity.