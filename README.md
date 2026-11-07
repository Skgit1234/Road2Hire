# Road2Hire — AI-Powered Career Readiness Engine

Road2Hire is an intelligent career readiness platform designed to evaluate candidate resumes, map competencies against standardized occupational taxonomies (ESCO v1.1.1 and US O*NET), detect skill gaps, predict career readiness tiers, provide explainable AI insights via SHAP, and generate personalized learning roadmaps.

---

## AI/ML Module Status

- **Status:** **Completed, Stabilized & Verified (Phase 7 Handover Ready)**
- **Test Suite:** 369 passed / 369 tests (100% pass rate)
- **JSON Schema:** Validated against Draft-07 schemas (`pipeline_output.schema.json` & `pipeline_error.schema.json`)
- **Backend Interface:** Reentrant thread-safe Python interface (`process_resume`, `get_pipeline`)
- **Database Specifications:** Hybrid Relational + JSONB architecture and field mapping specifications provided in `Docs/`

---

## Core Capabilities

- **Resume Intelligence (M2):** Automated PDF text extraction, contact metadata parsing, work history chronologies, and education normalization.
- **Taxonomy & Knowledge Graph (M1):** European Skills, Competences, Qualifications and Occupations (ESCO v1.1.1) and US O*NET occupational graph crosswalks.
- **Skill Extraction (M2):** Hybrid dictionary exact token matching and semantic embedding similarity (`all-MiniLM-L6-v2`).
- **Hybrid Skill Gap Detection (M3):** Three-tier categorization (Missing, Matched, Partially Matched) with weighted coverage scoring ($0.75 \times \text{Essential} + 0.25 \times \text{Optional}$).
- **Career Readiness Classifier (M4):** L2-regularized multinomial logistic regression predicting career readiness tiers (`Developing`, `Job Ready`, `Not Ready`).
- **Out-of-Distribution (OOD) Detection (M4):** Empirical bounding box checks detecting feature drift and extrapolation.
- **Explainable AI / SHAP (M4.5):** Local Shapley feature attributions quantifying positive and negative drivers of model predictions.
- **Personalized Learning Roadmap:** Structured 4-phase pedagogical curriculum mapped to curated learning resources.
- **Unified Reporting:** Simultaneous generation of canonical JSON data payloads and executive Markdown reports.

---

## Project Structure

```text
Road2Hire/
├── AI/                                  # Core AI/ML Engine
│   ├── Knowledge_Graph/                 # M1: ESCO/O*NET Knowledge Graph logic
│   ├── Resume_Extraction/               # M2: Resume PDF parsing & text extraction
│   ├── Candidate_Profile/               # M2: Profile schema & normalization
│   ├── Skill_Extraction/                # M2: Hybrid dictionary & MiniLM embeddings
│   ├── Skill_Gap_Detection/             # M3: 3-tier gap detection & candidate graph
│   ├── Readiness_Model/                 # M4: L2 Logistic Regression & OOD detector
│   ├── Explainability/                  # M4.5: Local SHAP LinearExplainer
│   ├── Pipeline/                        # Orchestrator, CLI, schemas & public interface
│   │   ├── pipeline.py                  # Road2HirePipeline central orchestrator
│   │   ├── pipeline_schema.py           # Dataclasses & canonical JSON serialization
│   │   ├── target_occupation_selector.py# Automatic & explicit occupation resolution
│   │   ├── roadmap_generator.py         # 4-phase curriculum builder
│   │   ├── report_generator.py          # Markdown executive summary generator
│   │   ├── cli.py                       # Standalone CLI entry point
│   │   └── schemas/                     # Draft-07 JSON Schema contracts
│   └── road2hire_model.py               # Singleton accessors & pre-warming caches
├── Datasets/                            # Taxonomy, training data & learning resources
│   ├── ESCO_ONET/                       # ESCO v1.1.1 & O*NET mappings
│   ├── Learning_Resources/              # Curated course catalogs
│   ├── Readiness_Dataset/               # Model training data (N=71)
│   └── Skill_Taxonomy/                  # Processed skill taxonomy catalogs
├── Docs/                                # Architecture & Handover Documentation
│   ├── AI_ML_Pipeline_Integration_Guide.md     # Developer integration guide
│   ├── AI_ML_Output_Contract.md                # Canonical JSON contract details
│   ├── AI_ML_Database_Storage_Specification.md # Hybrid persistence schema & ERD
│   ├── AI_ML_Database_Field_Mapping.md         # PostgreSQL column mapping table
│   ├── AI_ML_Limitations_and_Future_Work.md    # 12 scientific & engineering limitations
│   └── AI_ML_Final_Handover.md                 # Complete backend handover document
└── Tests/AI/                            # Complete automated test suite
```

---

## Quickstart & Installation

### 1. Prerequisites & Virtual Environment

Python 3.10+ is recommended. Activate your virtual environment and install dependencies:

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Install required dependencies
pip install -r requirements.txt
```

### 2. Run the Automated Test Suite

Verify the complete AI/ML pipeline across all 369 unit, integration, and contract tests:

```bash
pytest Tests/AI -v
```

---

## Usage Guide

### A. Programmatic Python API (Backend Integration)

The `AI.Pipeline` package provides a high-level function `process_resume()` designed for direct FastAPI and worker integration:

```python
from AI.Pipeline import process_resume

# Run analysis with an explicit target occupation
result = process_resume(
    resume_path="Tests/AI/sample_resume.pdf",
    target_occupation="data engineer",
    output_format="none",  # Suppress disk I/O in API services
)

if result.status == "success":
    # Access typed dataclass attributes
    print(f"Candidate: {result.candidate_profile['candidate']['name']}")
    print(f"Target:    {result.selected_occupation.occupation_label}")
    print(f"Readiness: {result.readiness_prediction.predicted_class}")
    print(f"Is OOD:    {result.readiness_prediction.is_ood}")

    # Serialize to Draft-07 canonical JSON dictionary for HTTP responses
    json_payload = result.to_canonical_dict()
else:
    print(f"Pipeline error: {result.error}")
```

### B. Command-Line Interface (CLI)

Run resume evaluations directly from your terminal:

```bash
# Explicit target occupation
python -m AI.Pipeline.cli Tests/AI/sample_resume.pdf --occupation "data engineer"

# Interactive occupation selection prompt
python -m AI.Pipeline.cli Tests/AI/sample_resume.pdf --interactive

# Custom output format and directory
python -m AI.Pipeline.cli Tests/AI/sample_resume.pdf --occupation "software developer" --output-dir "Outputs" --format both
```

---

## Scientific Disclaimers & Governance

1. **Uncalibrated Model Scores:** Career readiness Softmax probabilities represent uncalibrated heuristic model scores on an annotated dataset ($N=71$). They are **not** real-world hiring probabilities or employment guarantees.
2. **Explainability Bounds:** SHAP attributions represent local linear model feature credit relative to training base rates; they do not establish real-world causal mechanisms.
3. **Advisory Tool:** Road2Hire is designed as an assistive decision-support tool. It must never be used as an autonomous gatekeeper for employment or academic admissions.

For in-depth analysis of scientific limitations, consult [`Docs/AI_ML_Limitations_and_Future_Work.md`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Docs/AI_ML_Limitations_and_Future_Work.md).

---

## Documentation Index

- [AI/ML Final Handover Document](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Docs/AI_ML_Final_Handover.md)
- [AI/ML Pipeline Integration Guide](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Docs/AI_ML_Pipeline_Integration_Guide.md)
- [AI/ML Output Contract & Schema Specification](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Docs/AI_ML_Output_Contract.md)
- [AI/ML Database Storage Specification](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Docs/AI_ML_Database_Storage_Specification.md)
- [AI/ML Database Field Mapping Guide](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Docs/AI_ML_Database_Field_Mapping.md)
- [AI/ML Limitations & Future Work](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Docs/AI_ML_Limitations_and_Future_Work.md)
- [Pipeline Package Documentation](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Pipeline/README.md)
