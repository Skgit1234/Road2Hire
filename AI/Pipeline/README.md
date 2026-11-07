# Road2Hire — Central AI/ML Pipeline Package

**Pipeline Version:** `3.0.0`  
**Package:** `AI/Pipeline/`  
**Central Entry Point:** `Road2HirePipeline` in [`AI/Pipeline/pipeline.py`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Pipeline/pipeline.py)  
**Schema Contract:** [`AI/Pipeline/pipeline_schema.py`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Pipeline/pipeline_schema.py)  
**CLI Tool:** [`AI/Pipeline/cli.py`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Pipeline/cli.py)  

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
| [`pipeline.py`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Pipeline/pipeline.py) | Central orchestrator connecting all AI modules | `Road2HirePipeline`, `ResumeValidationError` |
| [`pipeline_schema.py`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Pipeline/pipeline_schema.py) | Stable dataclasses and JSON serialization contracts | `UnifiedPipelineResult`, `SelectedOccupation`, `ReadinessPredictionData`, `SHAPExplanationData`, `LearningRoadmap` |
| [`target_occupation_selector.py`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Pipeline/target_occupation_selector.py) | Resolves target occupations from query or ranked matches | `TargetOccupationSelector`, `OccupationSelectionError` |
| [`roadmap_generator.py`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Pipeline/roadmap_generator.py) | Generates prioritized 4-phase learning milestones | `RoadmapGenerator`, `RoadmapPhase`, `RoadmapItem` |
| [`report_generator.py`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Pipeline/report_generator.py) | Renders comprehensive Markdown and JSON reports | `ReportGenerator` |
| [`cli.py`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Pipeline/cli.py) | Clean command-line interface with logging suppression | `main()`, `print_summary()` |

---

## 3. Programmatic Usage (Python Backend)

```python
from pathlib import Path
from AI.Pipeline import Road2HirePipeline, UnifiedPipelineResult

# Initialize pipeline with cached model singletons
pipeline = Road2HirePipeline(base_output_dir="Outputs")

# Run analysis
result: UnifiedPipelineResult = pipeline.run(
    resume_path=Path("path/to/resume.pdf"),
    target_occupation="data engineer",
    interactive=False,
    output_format="both",
)

# Access typed output
print(f"Status:       {result.status}")
print(f"Candidate:    {result.candidate_profile['candidate']['name']}")
print(f"Target Role:  {result.selected_occupation.occupation_label}")
print(f"Readiness:    {result.readiness_prediction.predicted_class}")
print(f"Is OOD:       {result.readiness_prediction.is_ood}")

# Serialize to JSON
json_output = result.to_json(indent=2)
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

