# Road2Hire — M4.3 Career Readiness Annotation Pilot Dataset Report

**Generated:** 2026-11-05 UTC  
**Dataset File:** `C:\Users\Sarvesh S. Kundale\Road2Hire\Datasets\Processed\readiness_annotation_pilot.jsonl`  
**Format:** JSON Lines (`.jsonl`)  
**Sample Size:** **100 records** (100% `master_resumes`)  
**Schema Contract:** [`AI/Dataset_Preparation/readiness_label_schema.json`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Dataset_Preparation/readiness_label_schema.json)  

---

## 1. Executive Summary

This dataset contains **100 draft annotation records** sampled exclusively from real parsed resumes (`master_resumes.jsonl`) in the unified dataset (`candidate_occupation_dataset.jsonl`). It serves as the primary dataset for the initial multi-annotator human career readiness labeling pilot.

All records satisfy strict multi-modal evidence criteria: every selected candidate possesses verified skills, active professional work experience, documented project descriptions with technologies, and accredited academic degrees.

> [!IMPORTANT]
> **Zero Label Pre-Population (Strict Human Ground Truth):**
> - `readiness_label` is initialized to `null`.
> - `confidence` is initialized to `null`.
> - All evidence evaluation subfields are initialized to `null`.
> - `reviewer_status` is marked as `"Draft"`.
> - Existing rule-based skill coverage scores and gold compatibility labels were **completely excluded** to prevent data contamination and confirmation bias.

---

## 2. Sample Composition & Occupation Distribution

| Target ESCO Occupation | Target Concept URI | Selected Records | Share |
|:---|:---|:---:|:---:|
| **Software Developer** | `http://data.europa.eu/esco/occupation/f2b15a0e-e65a-438a-affb-29b9d50b77d1` | **55** | 55.0% |
| **Cloud DevOps Engineer** | `http://data.europa.eu/esco/occupation/2512.4` | **25** | 25.0% |
| **Data Scientist** | `http://data.europa.eu/esco/occupation/258e46f9-0075-4a2e-adae-1ff0477e0f30` | **7** | 7.0% |
| **ICT System Administrator** | `http://data.europa.eu/esco/occupation/a6baae73-cfdf-474d-b6eb-3b7cce14bb06` | **6** | 6.0% |
| **Operations Manager** | `http://data.europa.eu/esco/occupation/1349.1` | **5** | 5.0% |
| **Project Manager** | `http://data.europa.eu/esco/occupation/1219.1` | **2** | 2.0% |
| **Total** | | **100** | **100.0%** |

---

## 3. Selection & Exclusion Methodology

### Inclusion Criteria:
1. **Source Exclusivity:** 100% of candidates originate from real parsed resumes (`master_resumes`). Zero synthetic profiles were included due to their lack of qualitative project execution narrative.
2. **Multi-Modal Evidence Guarantee:**
   - **Normalized Skills:** $\ge 1$ verified technical skills (mean: 11.4 skills).
   - **Professional Experience:** $\ge 1$ professional work history records (mean: 1.8 positions).
   - **Technical Projects:** $\ge 1$ detailed project descriptions with technologies (mean: 1.6 projects).
   - **Accredited Education:** $\ge 1$ formal academic degrees (Computer Science, Software Engineering, IT, STEM).
3. **Occupation Variety:** Covers 6 distinct technical and management occupational families.

### Exclusion Log (During Sampling from Master Resumes):
- **Missing Project Evidence:** 99 resumes lacked a distinct project block and were excluded from this pilot.
- **Missing Skills Block:** 15 resumes lacked extracted skill dictionaries and were excluded.
- **Ungrounded / Non-Technical Roles:** Resumes mapped to non-technical or low-relevance roles (e.g. legal/lawyer) were excluded.
- **Quota Exceeded:** Once the software developer quota (55) was reached, subsequent developer candidates were safely bypassed to maintain occupational diversity.

---

## 4. Annotation Record Structure

Each record adheres strictly to [`readiness_label_schema.json`](file:///c:/Users/Sarvesh%20S.%20Kundale/Road2Hire/AI/Dataset_Preparation/readiness_label_schema.json):

```json
{
  "annotation_id": "mr_1__software_developer__pilot_ann",
  "pair_id": "mr_1__http://data.europa.eu/esco/occupation/f2b15a0e-e65a-438a-affb-29b9d50b77d1",
  "candidate_id": "mr_1",
  "candidate_source": "master_resumes",
  "target_occupation_uri": "http://data.europa.eu/esco/occupation/f2b15a0e-e65a-438a-affb-29b9d50b77d1",
  "target_occupation_title": "software developer",
  "readiness_label": null,
  "confidence": null,
  "evidence": {
    "essential_skill_proficiency": null,
    "work_experience_relevance": null,
    "practical_application_evidence": null,
    "education_relevance": null,
    "certifications_observed": [],
    "key_evidence_summary": null,
    "candidate_profile_summary": {
      "skills": ["Python", "Tensorflow", "Numpy", "MySQL"],
      "experience_summary": ["Python Developer (full-time)"],
      "projects_summary": ["Machine Learning Classifier: Python & Scikit-Learn"],
      "education_summary": ["B.Sc. in Computer Science"]
    }
  },
  "reviewer_status": "Draft",
  "annotator_id": "",
  "annotation_timestamp": "",
  "annotation_notes": ""
}
```

---

## 5. Next Steps for Annotation Execution

1. Distribute `readiness_annotation_pilot.jsonl` to two independent technical annotators.
2. Annotators review `candidate_profile_summary` and assign:
   - `readiness_label`: `"Not Ready"`, `"Developing"`, or `"Job Ready"`.
   - `confidence`: `"High"`, `"Medium"`, or `"Low"`.
   - Evidence subfield ratings and a 1–2 sentence `key_evidence_summary`.
3. Compute inter-annotator agreement (Cohen's $\kappa$). Target: $\kappa \ge 0.75$.
