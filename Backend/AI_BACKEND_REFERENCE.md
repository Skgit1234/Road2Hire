# Road2Hire AI backend reference

This reference describes the active AI and resume-processing functions in the
integrated backend. Source and dependency-injected contract tests are the basis
for these notes; live database and model connectivity are environment-dependent.

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

## Job matching

POST /jobs/{job_id}/matches requires bearer authentication and verifies that
both the job and resume belong to the caller. It runs and saves one unified
pipeline result against the job's target occupation. The response keeps this
occupation-based analysis separate from job-specific matching against the
job's stored required_skills. Job-specific matching uses only
pipeline.skills.extracted_skills and the shared SemanticSkillMatcher. Confirmed
exact, taxonomy-normalized, semantic, or validated identical-ESCO-URI matches
count as present. Uncertain matches retain candidate, similarity, and evidence;
known related skills retain their relation evidence. Neither counts as present.
Requirements with candidates but no matcher evidence are `non_match`; when no
candidate skills exist they are `missing`. Only `confirmed_match` contributes
coverage, with essential and optional scores calculated separately and combined
using the shared gap-scoring weights. Semantic thresholds are provisional, and
extracted keyword matches are not verified candidate facts.

Requirement `canonical_uri` values are not trusted as arbitrary strings. A URI
match is used only when the requirement URI and a candidate mapping URI both
resolve through the repository's ESCO taxonomy, are equal, and the mapping's
skill name is present in `extracted_skills`. If either side cannot be resolved
or linked, matching falls back to skill names and taxonomy-based semantic
matching. URI lookup uses the local ESCO dataset; no URI-to-label mapping is
invented. The response carries both job_id and pipeline_run_id with the
job-specific result. No job-specific result is applied when the saved job has
no requirements or the pipeline run did not complete.

## Career Assistant

POST /assistant/messages requires bearer authentication and currently returns
503 because this repository has no configured chat model or retrieval service.
The frontend remains an explicitly labeled local demonstration and does not
send messages to that endpoint. Its sample responses are not live AI guidance
or personal candidate analysis.

## Planned or unavailable capabilities

The frontend's resume-extraction.v1 type describes planned structured fields,
evidence, confidence, and provenance. The backend does not currently emit that
contract. Its PDF text extraction, rule-based section grouping, and vocabulary
matches must remain distinct from that future structured extraction.

The frontend's richer profile sample values are demo data.

Non-exact name comparisons require the optional Sentence Transformers package
and its model weights. A confirmed canonical URI match can be resolved locally
without embedding inference. If name matching needs embeddings and they are
unavailable, the job match endpoint reports matching as unavailable rather
than returning fabricated matches.

## Verification boundary

Unit tests for job matching use a stub matcher to verify scoring, provenance,
empty and invalid input handling without downloading model weights. They do
not contact PostgreSQL, run migrations, or verify live model connectivity.
