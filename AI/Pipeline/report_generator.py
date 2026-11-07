"""Report Generator for Unified Career Readiness Pipeline (Road2Hire).

Generates comprehensive human-readable Markdown and machine-readable JSON
reports saved to unique timestamped directories under Outputs/.
"""

from __future__ import annotations

from datetime import datetime
import json
import logging
from pathlib import Path
import re
from typing import Any

from AI.Pipeline.pipeline_schema import UnifiedPipelineResult

logger = logging.getLogger(__name__)

DEFAULT_OUTPUTS_DIR = Path("Outputs")


class ReportGenerator:
    """Formats and writes structured JSON and Markdown career readiness reports."""

    def __init__(self, base_output_dir: Path | str = DEFAULT_OUTPUTS_DIR) -> None:
        self.base_output_dir = Path(base_output_dir)

    def save_reports(
        self,
        result: UnifiedPipelineResult,
        output_dir: Path | str | None = None,
        output_format: str = "both",
    ) -> dict[str, str]:
        """Save JSON and/or Markdown report artifacts.

        Parameters
        ----------
        result:
            The complete UnifiedPipelineResult instance.
        output_dir:
            Custom directory path or None for default timestamped run folder.
        output_format:
            'both', 'json', or 'markdown'.

        Returns
        -------
        dict mapping format name ('json', 'markdown') to saved file path.
        """
        target_dir = self._prepare_run_dir(result, output_dir)
        paths: dict[str, str] = {}

        if output_format in ("json", "both"):
            json_file = target_dir / "career_readiness_report.json"
            json_data = result.to_dict()
            json_file.write_text(json.dumps(json_data, indent=2, default=str), encoding="utf-8")
            paths["json"] = str(json_file)
            logger.info("Saved JSON report to: %s", json_file)

        if output_format in ("markdown", "both"):
            md_file = target_dir / "career_readiness_report.md"
            md_content = self.render_markdown(result)
            md_file.write_text(md_content, encoding="utf-8")
            paths["markdown"] = str(md_file)
            logger.info("Saved Markdown report to: %s", md_file)

        result.report_paths = paths
        return paths

    def _prepare_run_dir(
        self,
        result: UnifiedPipelineResult,
        custom_dir: Path | str | None = None,
    ) -> Path:
        """Create a dedicated, unique directory for the pipeline run."""
        if custom_dir is not None:
            run_dir = Path(custom_dir)
        else:
            cand_name = "unnamed_candidate"
            try:
                candidate_info = (
                    result.candidate_profile.get("candidate", {})
                    if isinstance(result.candidate_profile, dict)
                    else {}
                )
                raw_name = candidate_info.get("name") if isinstance(candidate_info, dict) else None
                if raw_name and isinstance(raw_name, str) and raw_name.strip():
                    cand_name = re.sub(r"[^a-zA-Z0-9_\-]+", "_", raw_name.strip())
            except Exception:
                pass

            src_stem = Path(result.source_file).stem if result.source_file else "resume"
            src_clean = re.sub(r"[^a-zA-Z0-9_\-]+", "_", src_stem)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            folder_name = f"readiness_{cand_name}_{src_clean}_{ts}"
            run_dir = self.base_output_dir / folder_name

        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def render_markdown(self, res: UnifiedPipelineResult) -> str:
        """Render a formatted, comprehensive Markdown report."""
        sel_occ = res.selected_occupation
        gap = res.skill_gap_analysis
        readiness = res.readiness_prediction
        shap_exp = res.shap_explanation
        roadmap = res.learning_roadmap
        cand = (
            res.candidate_profile.get("candidate", {})
            if isinstance(res.candidate_profile, dict)
            else {}
        )
        raw_name = cand.get("name") if isinstance(cand, dict) else None
        cand_name = (
            raw_name.strip()
            if raw_name and isinstance(raw_name, str) and raw_name.strip()
            else "Not provided"
        )

        lines: list[str] = [
            f"# Road2Hire — Career Readiness & Skill Gap Intelligence Report",
            "",
            f"**Candidate:** `{cand_name}`  ",
            f"**Target Occupation:** **{sel_occ.occupation_label}**  ",
            f"**ESCO Concept URI:** [`{sel_occ.occupation_uri}`]({sel_occ.occupation_uri})  ",
            f"**Report Generated:** {res.timestamp}  ",
            f"**Pipeline Version:** `{res.pipeline_version}`  ",
            "",
            "---",
            "",
            "## 1. Executive Summary",
            "",
            f"- **Resume Processing:** Successfully extracted **{res.page_count} page(s)** with **{len(res.extracted_skills)} technical skills** verified.",
            f"- **Target Occupation:** **{sel_occ.occupation_label}** (Initial Match Overlap Score: `{sel_occ.match_score}`)",
            f"- **Overall Skill Coverage:** **`{gap.get('overall_skill_coverage_score', 0.0)*100:.1f}%`** "
            f"(Essential: `{gap.get('essential_skill_coverage_score', 0.0)*100:.1f}%`, "
            f"Optional: `{gap.get('optional_skill_coverage_score', 0.0)*100:.1f}%`)",
        ]

        if readiness:
            prob_str = ", ".join(f"{k}: {v*100:.1f}%" for k, v in readiness.class_probabilities.items())
            lines.append(
                f"- **Supervised Career Readiness:** **`{readiness.predicted_class}`** ({prob_str})"
            )

        if roadmap:
            lines.append(
                f"- **Personalized Learning Roadmap:** **{roadmap.total_roadmap_skills} recommended skill milestones** "
                f"structured across 4 phases ({roadmap.total_estimated_weeks})."
            )

        lines.extend([
            "",
            "---",
            "",
            "## 2. Extracted Resume Skills & ESCO Normalization",
            "",
            f"A total of **{len(res.extracted_skills)} skills** were extracted using boundary-aware Trie matching and normalized to canonical ESCO concepts:",
            "",
            "| Skill Name | Canonical ESCO Preferred Label | Mapping Type | Sections Found |",
            "|:---|:---|:---:|:---|",
        ])

        for s in res.esco_mappings:
            s_name = s.get("skill", "")
            esco_name = s.get("ESCO_Skill_Name") or "*(Unmapped)*"
            m_type = s.get("ESCO_Mapping_Type", "unmapped")
            secs = ", ".join(s.get("source_sections", []))
            lines.append(f"| **{s_name}** | {esco_name} | `{m_type}` | {secs} |")

        lines.extend([
            "",
            "---",
            "",
            "## 3. Hybrid Skill Gap Analysis",
            "",
            f"### Target Occupation: **{sel_occ.occupation_label}**",
            "",
            "| Metric | Score | Formula / Notes |",
            "|:---|:---:|:---|",
            f"| **Overall Skill Coverage** | **`{gap.get('overall_skill_coverage_score', 0.0)*100:.2f}%`** | $0.75 \\times \\text{{Essential}} + 0.25 \\times \\text{{Optional}}$ |",
            f"| **Essential Skill Coverage** | **`{gap.get('essential_skill_coverage_score', 0.0)*100:.2f}%`** | Matched essential credits / total essential requirements |",
            f"| **Optional Skill Coverage** | **`{gap.get('optional_skill_coverage_score', 0.0)*100:.2f}%`** | Matched optional credits / total optional requirements |",
            "",
            "#### Matched & Partially Matched Skills",
            "",
            "| Skill | Match Tier | Match Type | Similarity Credit |",
            "|:---|:---:|:---|:---:|",
        ])

        for m in gap.get("matched_skills", []):
            sk = m.get("occupation_skill") or m.get("candidate_skill")
            tier = m.get("match_tier", 1)
            m_type = m.get("match_type", "exact_uri")
            credit = m.get("credit", 1.0)
            lines.append(f"| **{sk}** | Tier {tier} | `{m_type}` | `{credit:.2f}` |")

        for m in gap.get("partially_matched_skills", []):
            sk = m.get("occupation_skill") or m.get("candidate_skill")
            tier = m.get("match_tier", 3)
            m_type = m.get("match_type", "semantic_similarity")
            credit = m.get("credit", 0.5)
            lines.append(f"| **{sk}** (Partial) | Tier {tier} | `{m_type}` | `{credit:.2f}` |")

        if not gap.get("matched_skills") and not gap.get("partially_matched_skills"):
            lines.append("| *(No direct or partial matches)* | - | - | - |")

        lines.extend([
            "",
            f"#### Missing Essential Skills ({len(gap.get('missing_essential_skills', []))} total)",
            "",
            "| Missing Essential Skill | Type | ESCO URI |",
            "|:---|:---:|:---|",
        ])

        for m in gap.get("missing_essential_skills", []):
            label = m.get("skill_label", "")
            s_type = m.get("skill_type", "skill/competence")
            uri = m.get("skill_uri", "")
            lines.append(f"| **{label}** | `{s_type}` | [`{uri.split('/')[-1]}`]({uri}) |")

        lines.extend([
            "",
            "---",
            "",
            "## 4. Supervised Career Readiness Classification (M4)",
            "",
        ])

        if readiness:
            lines.extend([
                f"**Predicted Readiness Class:** **`{readiness.predicted_class}`**  ",
                f"**Model Architecture:** `{readiness.model_type}` (`{readiness.model_version}`)  ",
                "",
                "| Readiness Class | Model Probability | Status |",
                "|:---|:---:|:---|",
            ])
            for cls_name, prob in readiness.class_probabilities.items():
                is_pred = " **(Predicted)**" if cls_name == readiness.predicted_class else ""
                lines.append(f"| **{cls_name}** | **`{prob*100:.2f}%`** | {is_pred} |")

            if getattr(readiness, "is_ood", False) and readiness.ood_warnings:
                lines.extend([
                    "",
                    "> [!WARNING]",
                    "> **Out-of-Distribution (OOD) Warning:**  ",
                    "> The candidate's evidence profile contains feature values outside observed training bounds:",
                ])
                for w in readiness.ood_warnings:
                    lines.append(f"> - {w}")
                lines.append("> Probability estimates reflect regularized model extrapolations and must not be taken as certified competence.")

            lines.extend([
                "",
                "> [!NOTE]",
                "> Career readiness evaluates whether the candidate demonstrates foundational competencies, "
                "> tenure, and practical project depth expected of industry candidates. "
                "> It is distinct from skill coverage or candidate-job requisition matching. "
                "> Probabilities are heuristic model estimates, not certified real-world guarantees.",
                "",
            ])
        else:
            lines.append("*(Readiness classification skipped or unavailable)*\n")

        lines.extend([
            "---",
            "",
            "## 5. SHAP Explainability & Feature Attributions (M4.5)",
            "",
        ])

        if shap_exp:
            lines.extend([
                f"**Target Class Explained:** `{shap_exp.target_class_explained}`  ",
                f"**Model Intercept (Base Value):** `{shap_exp.base_value:.4f}` log-odds  ",
                "",
                f"**Summary:** {shap_exp.human_readable_summary}",
                "",
                "### Primary Positive Driving Factors",
                "",
                "| Feature | Feature Value | Contribution (+Log-Odds) | Description |",
                "|:---|:---:|:---:|:---|",
            ])
            for f in shap_exp.top_positive_factors:
                lines.append(
                    f"| **{f.get('display_name', f.get('feature'))}** | `{f.get('feature_value')}` | "
                    f"**`+{f.get('contribution', 0.0):.4f}`** | {f.get('description', '')} |"
                )

            lines.extend([
                "",
                "### Primary Negative Restraining Factors",
                "",
                "| Feature | Feature Value | Contribution (-Log-Odds) | Description |",
                "|:---|:---:|:---:|:---|",
            ])
            for f in shap_exp.top_negative_factors:
                lines.append(
                    f"| **{f.get('display_name', f.get('feature'))}** | `{f.get('feature_value')}` | "
                    f"**`{f.get('contribution', 0.0):.4f}`** | {f.get('description', '')} |"
                )
        else:
            lines.append("*(SHAP explainability skipped or unavailable)*\n")

        lines.extend([
            "",
            "---",
            "",
            "## 6. Personalized Knowledge Graph Topology (M3)",
            "",
        ])

        pg_sum = res.personalized_graph_summary
        if pg_sum:
            lines.extend([
                f"- **Total Graph Nodes:** `{pg_sum.get('total_nodes', 0)}`",
                f"- **Total Graph Edges:** `{pg_sum.get('total_edges', 0)}`",
                f"- **Node Breakdown:** {', '.join(f'{k}: {v}' for k, v in pg_sum.get('node_counts_by_kind', {}).items())}",
                f"- **Edge Breakdown:** {', '.join(f'{k}: {v}' for k, v in pg_sum.get('edge_counts_by_relation', {}).items())}",
            ])
        else:
            lines.append("*(Personalized knowledge graph not generated)*")

        lines.extend([
            "",
            "---",
            "",
            "## 7. Personalized Learning Roadmap",
            "",
            f"Tailored to close identified skill gaps for **{sel_occ.occupation_label}**:",
            "",
        ])

        if roadmap:
            for p in roadmap.phases:
                lines.extend([
                    f"### {p.phase_name} ({p.estimated_weeks})",
                    "",
                    f"*{p.description}*",
                    "",
                ])
                for idx, it in enumerate(p.items, start=1):
                    lines.extend([
                        f"#### {p.phase_number}.{idx} {it.skill_name} (`{it.priority}` Priority)",
                        "",
                        f"- **Rationale:** {it.importance_rationale}",
                        f"- **Learning Outcome:** {it.learning_outcome}",
                        f"- **Estimated Duration:** {it.estimated_duration_weeks}",
                        f"- **Suggested Activities:**",
                    ])
                    for act in it.suggested_activities:
                        lines.append(f"  - {act}")
                    lines.append(f"- **Practical Project:** {it.practical_project}")
                    lines.append(f"- **Completion Criteria:** {it.completion_criteria}")
                    lines.append(f"- **Recommended Search Resources:**")
                    for rc in it.resource_categories:
                        lines.append(f"  - *{rc['category']}:* `{rc['recommended_search']}`")
                    lines.append("")

        lines.extend([
            "---",
            "",
            "## 8. Methodological Governance & Limitations",
            "",
            "1. **Exploratory Model Scope:** The M4 Career Readiness prediction model is trained on an annotated pilot dataset ($N=71$) with class imbalance. Predictions are experimental.",
            "2. **Attribution, Not Proof:** SHAP attributions reflect statistical model log-odds margins relative to background training resumes, not certified guarantees of real-world qualification.",
            "3. **Skill Coverage Distinctness:** Skill coverage metrics reflect direct taxonomy string and semantic overlap against official ESCO occupation definitions; they do not represent hiring probability.",
            "4. **No Commercial Guarantee:** Completing recommended roadmap milestones builds domain capability but does not guarantee employment or job placement.",
            "",
        ])

        return "\n".join(lines)

