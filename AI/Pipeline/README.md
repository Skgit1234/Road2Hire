# Road2Hire — Central AI/ML Pipeline Package

**Pipeline Version:** `3.0.0`  
**Package:** `AI/Pipeline/`  
**Central Entry Point:** `Road2HirePipeline` in [`AI/Pipeline/pipeline.py`](AI/Pipeline/pipeline.py)  
**Schema Contract:** [`AI/Pipeline/pipeline_schema.py`](AI/Pipeline/pipeline_schema.py)  
**CLI Tool:** [`AI/Pipeline/cli.py`](AI/Pipeline/cli.py)  

---

## 1. Overview

The `AI/Pipeline/` package orchestrates the complete Road2Hire Career Readiness workflow, integrating all capabilities from Milestones M1 through M4.5 into a unified Python interface and CLI.

```
Resume PDF
  │
  ▼
[1. Text Extraction & Section Parsing] (M1 / M2)
  │
  ▼
[2. Trie Skill Extraction & ESCO Normalization] (M2)
  │
  ▼
[3. Knowledge Graph Occupation Ranking] (M2)
  │
  ▼
[4. Target Occupation Resolution]
  │
  ▼
[5. Hybrid 3-Tier Skill Gap Detection] (M3)
  │
  ▼
[6. Personalized Knowledge Graph Generation] (M3)
  │
  ▼
[7. Career Readiness Prediction & OOD Detection] (M4)
  │
  ▼
[8. SHAP Explainability] (M4.5)
  │
  ▼
[9. Personalized Learning Roadmap Generation]
  │
  ▼
[10. Markdown & JSON Report Serialization]
```

---

## 2. Core Modules

| Module | Description | Primary Classes / Functions |
|:---|:---|:---|
| [`pipeline.py`](AI/Pipeline/pipeline.py) | Central orchestrator connecting all AI modules | `Road2HirePipeline`, `ResumeValidationError` |
| [`pipeline_schema.py`](AI/Pipeline/pipeline_schema.py) | Stable dataclasses and JSON serialization contracts | `UnifiedPipelineResult`, `SelectedOccupation`, `ReadinessPredictionData`, `SHAPExplanationData`, `LearningRoadmap` |
| [`target_occupation_selector.py`](AI/Pipeline/target_occupation_selector.py) | Resolves target occupations from query or ranked matches | `TargetOccupationSelector`, `OccupationSelectionError` |
| [`roadmap_generator.py`](AI/Pipeline/roadmap_generator.py) | Generates prioritized 4-phase learning milestones | `RoadmapGenerator`, `RoadmapPhase`, `RoadmapItem` |
| [`report_generator.py`](AI/Pipeline/report_generator.py) | Renders comprehensive Markdown and JSON reports | `ReportGenerator` |
| [`cli.py`](AI/Pipeline/cli.py) | Clean command-line interface with logging suppression | `main()`, `print_summary()` |

---

## 3. Programmatic Usage (Python Backend)

Road2Hire provides two primary Python integration entry points:
1. `process_resume(...)`: High-level convenience function for backend services and background workers.
2. `Road2HirePipeline.run(...)`: Direct object-oriented pipeline interface.

Both entry points utilize the thread-safe `get_pipeline()` and `get_road2hire_model()` singletons to share heavy in-memory models (ESCO taxonomy, knowledge graph, SentenceTransformer embeddings, M4 readiness classifier, SHAP explainer) across inference requests.

### A. High-Level Python API (`process_resume`)

```python
from pathlib import Path
from AI.Pipeline import process_resume, UnifiedPipelineResult

# 1. Processing with explicit target occupation
result: UnifiedPipelineResult = process_resume(
    resume_path="path/to/resume.pdf",
    target_occupation="data engineer",
    output_format="none",  # 'none' suppresses file I/O for API speed
)

# 2. Processing with automatic top-occupation resolution
result_auto = process_resume(
    resume_path="path/to/resume.pdf",
    target_occupation=None,
    auto_select_top_occupation=True,
    output_format="none",
)

# Access typed attributes
print(f"Status:       {result.status}")
print(f"Candidate:    {result.candidate_profile['candidate']['name']}")
print(f"Target Role:  {result.selected_occupation.occupation_label}")
print(f"Readiness:    {result.readiness_prediction.predicted_class}")
print(f"Is OOD:       {result.readiness_prediction.is_ood}")

# Serialize to Draft-07 canonical JSON for HTTP responses
canonical_payload: dict = result.to_canonical_dict()
json_string: str = result.to_json(indent=2)
```

### B. Object-Oriented Pipeline API (`Road2HirePipeline`)

```python
from AI.Pipeline import Road2HirePipeline, get_pipeline

# Obtain shared singleton (thread-safe)
pipeline: Road2HirePipeline = get_pipeline(base_output_dir="Outputs")

# Run pipeline execution
result = pipeline.run(
    resume_path="path/to/resume.pdf",
    target_occupation="data engineer",
    interactive=False,
    output_format="both",
    auto_select_top_occupation=False,
)
```

### C. Exception Handling

```python
from AI.Pipeline import ResumeValidationError, OccupationSelectionError, PipelineError

try:
    result = process_resume(
        resume_path="candidate.pdf",
        target_occupation=None,
        auto_select_top_occupation=False,
    )
except ResumeValidationError as exc:
    # 400 Bad Request: missing file, non-PDF, 0-byte corrupt document
    print(f"Resume validation failed: {exc}")
except OccupationSelectionError as exc:
    # 422 Unprocessable Entity: occupation missing or unresolvable.
    # .suggested_occupations contains ranked recommendations to prompt the user
    print(f"Occupation error: {exc}")
    for occ in exc.suggested_occupations[:5]:
        print(f" - {occ['occupation_label']} (Score: {occ['score']})")
except PipelineError as exc:
    # 500 Internal Server Error: general orchestration failure
    print(f"Pipeline error: {exc}")
```

---

## 4. CLI Usage

```bash
# Explicit target occupation
python -m AI.Pipeline.cli Tests/AI/sample_resume.pdf --occupation "data engineer"

# Interactive selection mode
python -m AI.Pipeline.cli Tests/AI/sample_resume.pdf --interactive

# Specify custom output directory and format
python -m AI.Pipeline.cli Tests/AI/sample_resume.pdf --occupation "software developer" --output-dir "MyReports" --format markdown
```
