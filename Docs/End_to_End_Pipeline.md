# Road2Hire — End-to-End Career Readiness Pipeline

**Pipeline Version:** `3.0.0`  
**Central Orchestrator:** [`AI/Pipeline/pipeline.py`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Pipeline/pipeline.py)  
**CLI Interface:** [`AI/Pipeline/cli.py`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Pipeline/cli.py)  
**Schema Models:** [`AI/Pipeline/pipeline_schema.py`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Pipeline/pipeline_schema.py)  
**Automated Tests:** [`Tests/AI/test_end_to_end_pipeline.py`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Tests/AI/test_end_to_end_pipeline.py)  

---

## 1. Architectural Overview & Workflow

The Central Road2Hire Pipeline unifies Milestones **M1, M2, M3, and M4** into a single, cohesive resume intelligence and career readiness assessment system.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ROAD2HIRE CENTRAL PIPELINE WORKFLOW                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [Resume PDF Input]                                                         │
│         │                                                                   │
│         ▼                                                                   │
│  [Stage 1: Validation & Text Extraction (M1)]                               │
│  - PyMuPDF extraction, empty text check, page metadata                      │
│         │                                                                   │
│         ▼                                                                   │
│  [Stage 2: Section Detection (M1)]                                          │
│  - Heuristic pattern detection (Summary, Education, Experience, Skills...)  │
│         │                                                                   │
│         ▼                                                                   │
│  [Stage 3: Boundary-Aware Trie Skill Extraction (M2)]                       │
│  - 99,676 ESCO preferred + alt-label Trie matching in O(L) time             │
│         │                                                                   │
│         ▼                                                                   │
│  [Stage 4: ESCO Normalization & Semantic Embeddings (M2)]                   │
│  - Canonical ESCO concept mapping + all-MiniLM-L6-v2 embeddings             │
│         │                                                                   │
│         ▼                                                                   │
│  [Stage 5: Candidate Profile Assembly (Schema v1.1.0)]                      │
│  - Structured candidate JSON validated against schema                       │
│         │                                                                   │
│         ▼                                                                   │
│  [Stage 6: Knowledge Graph Occupation Matching (M2)]                        │
│  - Overlap scoring across ESCO occupation-skill relations                   │
│         │                                                                   │
│         ▼                                                                   │
│  [Stage 7: Target Occupation Resolution & Selection]                        │
│  - Interactive menu selection OR explicit command-line argument             │
│         │                                                                   │
│         ▼                                                                   │
│  [Stage 8: Hybrid 3-Tier Skill Gap Detection (M3)]                          │
│  - Tier 1: Exact URI/Label -> Tier 2: ESCO Graph -> Tier 3: Semantic       │
│  - Coverage metrics: Overall (0.75 Essential + 0.25 Optional), Missing sets │
│         │                                                                   │
│         ▼                                                                   │
│  [Stage 9: Personalized Knowledge Graph (M3)]                               │
│  - NetworkX candidate-occupation subgraph (Candidate, Roles, Skills, Gaps) │
│         │                                                                   │
│         ▼                                                                   │
│  [Stage 10: Supervised Career Readiness Prediction (M4)]                    │
│  - Logistic Regression pipeline evaluated on 9 profile features             │
│  - Class probabilities: Developing, Job Ready, Not Ready                    │
│         │                                                                   │
│         ▼                                                                   │
│  [Stage 11: SHAP Explainability (M4.5)]                                     │
│  - Exact LinearExplainer decision margin attributions (Efficiency Axiom)   │
│  - Top positive & negative factors, waterfall step breakdown                │
│         │                                                                   │
│         ▼                                                                   │
│  [Stage 12: Personalized Learning Roadmap]                                  │
│  - Prioritized 4-Phase milestones: Foundational -> Core -> Applied -> Adv.  │
│         │                                                                   │
│         ▼                                                                   │
│  [Stage 13: Unified Output Reporting]                                       │
│  - Timestamped output directory under Outputs/                              │
│  - Machine-readable JSON + Human-readable Markdown                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Command-Line Interface (CLI)

The pipeline can be invoked via Python module execution from the project root:

### A. Non-Interactive Execution (Explicit Target Role)
```bash
python -m AI.Pipeline.cli --resume "Tests/AI/sample_resume.pdf" --occupation "Data Engineer"
```

### B. Interactive Execution (Prompt from Suggestions)
```bash
python -m AI.Pipeline.cli --resume "Tests/AI/sample_resume.pdf"
```
When `--occupation` is omitted in an interactive terminal session:
1. The pipeline processes the resume and displays the **Top 10 ranked occupation matches**.
2. A prompt asks the user to enter `1 - 10` or type a custom occupation title or URI.
3. The selected role is resolved to its canonical ESCO URI before running gap detection and roadmap generation.

### C. Available CLI Arguments
| Flag | Short | Default | Description |
|:---|:---:|:---:|:---|
| `--resume` | `-r` | *(Required)* | Path to candidate resume PDF file. |
| `--occupation` | `-o` | `None` | Target occupation title, concept URI, or search string. |
| `--output` | `-d` | `Outputs` | Base directory where report folders are saved. |
| `--top-n` | `-n` | `10` | Number of top occupation matches to display. |
| `--format` | `-f` | `both` | Output format: `both`, `json`, or `markdown`. |
| `--verbose` | - | `False` | Enable detailed diagnostic logging, model loading output, and tracebacks. |
| `--quiet` | `-q` | `False` | Run in quiet mode, suppressing progress banners and summary. |
| `--version` | `-V` | - | Display pipeline version and exit. |

### D. Clean & Professional Terminal Output
By default, the CLI runs in a clean, quiet-by-default execution mode designed for production and presentation clarity:
- **Noisy Log Suppression:** Third-party HTTP request logs (`httpx`, `httpcore`), internal model-loading logs (`sentence_transformers`, `transformers`), and harmless warnings (`huggingface_hub` unauthenticated notices) are suppressed.
- **Progress Bar Handling:** `tqdm` progress bars are disabled during normal runs.
- **Candidate Name Integrity:** Candidate name is extracted directly from `candidate_profile["candidate"]["name"]`. If missing or empty, it strictly displays `Not provided` (it is never inferred or guessed from the PDF filename).
- **Execution Summary:** Every successful run prints a clear terminal summary highlighting:
  - Pipeline title and version
  - Processing status (`Success` or specific stage warnings)
  - Candidate name and resume page count
  - Target occupation title and canonical ESCO URI
  - Extracted skills count and 3-tier coverage percentages (Overall, Essential, Optional)
  - Career readiness class and model probability
  - Learning roadmap milestone count, phase breakdown, and estimated weeks
  - Output report paths (`.json` and `.md`)
- **Diagnostic Mode (`--verbose`):** When diagnosing issues or inspecting model loading, `--verbose` activates full `INFO` diagnostic logging, enables progress indicators, and prints full exception tracebacks on failure.
- **Error Handling:** Stage validation and pipeline errors exit with code `1` and a concise, single-line error notice without cluttering stdout; unexpected errors exit with code `2`.

---

## 3. Python API Integration

The pipeline can also be called directly in Python:

```python
from AI.Pipeline import Road2HirePipeline

# Initialize the pipeline (reuses cached taxonomy, graph, and ML models)
pipeline = Road2HirePipeline()

# Run the complete workflow
result = pipeline.run(
    resume_path="Tests/AI/sample_resume.pdf",
    target_occupation="Data Engineer",
    interactive=False,
    output_format="both",
)

# Access individual stage outputs
print("Status:", result.status)
print("Target Role:", result.selected_occupation.occupation_label)
print("Overall Skill Coverage:", result.skill_gap_analysis["overall_skill_coverage_score"])
print("Readiness Class:", result.readiness_prediction.predicted_class)
print("Readiness Probabilities:", result.readiness_prediction.class_probabilities)
print("Is OOD:", result.readiness_prediction.is_ood)
print("SHAP Summary:", result.shap_explanation.human_readable_summary)
print("Roadmap Total Skills:", result.learning_roadmap.total_roadmap_skills)
print("Saved Reports:", result.report_paths)

# Direct JSON export
json_payload = result.to_json(indent=2)
```

For complete backend integration details, schema documentation, and API design guidelines, see [`Docs/AI_ML_Pipeline_Integration_Guide.md`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/Docs/AI_ML_Pipeline_Integration_Guide.md).

---

## 4. Output Structure & Artifacts

For each run, a unique, timestamped directory is created under `Outputs/`:
```text
Outputs/
└── readiness_<candidate_name>_<resume_file>_<YYYYMMDD_HHMMSS>/
    ├── career_readiness_report.json    # Full machine-readable payload
    └── career_readiness_report.md      # Comprehensive executive & technical report
```

### JSON Report Schema
```json
{
  "pipeline_version": "3.0.0",
  "timestamp": "2026-11-06T22:18:00.443776",
  "source_file": "Tests/AI/sample_resume.pdf",
  "page_count": 1,
  "extraction_status": "success",
  "candidate_profile": { ... },
  "extracted_skills": [ ... ],
  "esco_mappings": [ ... ],
  "occupation_matches": [ ... ],
  "selected_occupation": {
    "occupation_uri": "http://data.europa.eu/esco/occupation/2079755f-d809-49e6-8037-4de6180e54c0",
    "occupation_label": "data engineer",
    "match_score": 3,
    "essential_matched": 2,
    "optional_matched": 1
  },
  "skill_gap_analysis": {
    "overall_skill_coverage_score": 0.1152,
    "essential_skill_coverage_score": 0.087,
    "optional_skill_coverage_score": 0.20,
    "matched_skills": [ ... ],
    "partially_matched_skills": [ ... ],
    "missing_essential_skills": [ ... ],
    "missing_optional_skills": [ ... ]
  },
  "personalized_graph_summary": {
    "total_nodes": 43,
    "total_edges": 64
  },
  "readiness_prediction": {
    "predicted_class": "Job Ready",
    "class_probabilities": {
      "Developing": 0.0522,
      "Job Ready": 0.9198,
      "Not Ready": 0.0280
    },
    "model_version": "0.1.0-exploratory",
    "model_type": "LogisticRegression"
  },
  "shap_explanation": {
    "target_class_explained": "Job Ready",
    "base_value": 0.4497,
    "top_positive_factors": [ ... ],
    "top_negative_factors": [ ... ],
    "human_readable_summary": "..."
  },
  "learning_roadmap": {
    "target_occupation_title": "data engineer",
    "total_roadmap_skills": 14,
    "total_estimated_weeks": "12 – 22 Weeks",
    "phases": [ ... ]
  },
  "execution_timings_seconds": { ... },
  "warnings": [],
  "errors": []
}
```

---

## 5. 4-Phase Learning Roadmap Structure

The learning roadmap groups prioritized skill gaps into 4 distinct phases:

| Phase | Focus Area | Inputs | Target Duration |
|:---:|:---|:---|:---:|
| **Phase 1** | **Foundational Competencies & Core Knowledge** | Missing essential knowledge concepts (`skill_type == 'knowledge'`) and prerequisites | 2 – 4 Weeks |
| **Phase 2** | **Core Technical Implementation Skills** | Remaining missing essential competencies (`skill_type == 'skill/competence'`) | 4 – 8 Weeks |
| **Phase 3** | **Applied Systems & Portfolio Project Execution** | Partially matched skills to deepen from theoretical to hands-on production level | 4 – 6 Weeks |
| **Phase 4** | **Advanced Specialization & Optional Capabilities** | Missing optional skills and enterprise cloud tooling | 2 – 4 Weeks |

Every roadmap item provides:
- **Skill Name & Canonical ESCO URI**
- **Priority Tier:** `Critical`, `High`, `Medium`, or `Low`
- **Importance Rationale:** Why the role demands this skill
- **Learning Outcome:** Concrete capability to acquire
- **Suggested Learning Activities:** Hands-on study and architecture diagrams
- **Practical Project Scenario:** Specific portfolio project scenario to build
- **Completion Criteria:** Verifiable standard of mastery
- **Recommended Search Terms:** Topic search queries without fake URLs or fabricated provider names

---

## 6. Methodological Governance & Disclaimers

1. **Supervised Model Limitations:** The M4 Career Readiness prediction model is trained on an annotated pilot dataset ($N=71$) with class imbalance. Predictions are experimental and descriptive of candidate resume profile signals; they do not certify real-world competence.
2. **Attribution, Not Proof:** SHAP attributions reflect statistical model log-odds margins relative to background training resumes, not certified guarantees of real-world qualification.
3. **Skill Coverage Distinctness:** Skill coverage metrics reflect direct taxonomy string and semantic overlap against official ESCO occupation definitions; they do not represent hiring probability.
4. **No Commercial Guarantee:** Completing recommended roadmap milestones builds domain capability but does not guarantee employment or job placement.
5. **Candidate Privacy:** Resume parsing does not expose PII in terminal logs. Generated reports are stored locally in the git-ignored `Outputs/` folder.

