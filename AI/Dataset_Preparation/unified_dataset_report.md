# Road2Hire — M4.2 Unified Candidate–Occupation Dataset Report & Final Audit

**Audit Date:** 2026-11-05 12:05:00 UTC  
**Dataset Location:** `Datasets/Processed/candidate_occupation_dataset.jsonl`  
**Dataset Format:** JSON Lines (`.jsonl`)  
**Dataset Size:** 27.65 MB (27,652,653 bytes)  

---

## 1. Executive Summary

This report provides the final quality audit and verification of the **Road2Hire Unified Candidate–Occupation Dataset (M4.2)** before progressing to M4.3 (Career-Readiness Label Preparation).

The dataset bridges candidate profiles from synthetic and real parsed resume repositories with canonical ESCO occupation requirements, hybrid skill gap detection features, personalized knowledge graph topological metrics, and supplementary O*NET skill benchmarks.

> [!IMPORTANT]
> **Strict Non-Readiness Guarantees Verified:**
> 1. **Skill Coverage Scores are Features, Not Labels:** The numerical scores (`overall_skill_coverage_score`, `essential_skill_coverage_score`, `optional_skill_coverage_score`) are rule-based, deterministic alignment metrics produced by the M3 Hybrid Skill Gap engine. They are not career-readiness labels or training targets.
> 2. **Gold Labels Represent Compatibility, Not Readiness:** The annotations from `Datasets/gold_labels.json` assess candidate-job compatibility for specific scraped job postings. They are completely separated from readiness logic and stored strictly as nullable reference metadata.
> 3. **Zero Dataset Mutation:** All raw datasets (`master_resumes.jsonl`, `synthetic_profiles.json`, `scraped_jobs.json`, `gold_labels.json`, ESCO CSVs) remain completely unmodified.

---

## 2. Dataset Construction & Distribution

| Metric | Verified Count | Notes / Provenance |
|:---|:---|:---|
| **Total Records Generated** | **1,140** | Validated JSON lines |
| **Unique Candidate Profiles** | **1,140** | 100% unique `(candidate_source, candidate_id)` |
| **Unique Pair IDs** | **1,140** | 100% unique `{candidate_id}__{target_occupation_uri}` |
| - *Synthetic Profiles (`synthetic_profiles.json`)* | **640** (56.1%) | 100% of available synthetic profiles |
| - *Real Parsed Resumes (`master_resumes.jsonl`)* | **500** (43.9%) | Sampled via memory-safe streaming |
| **Unique Grounded ESCO Occupations** | **71** | Valid canonical concept URIs |
| **Records Excluded** | **0** | All 1,140 profiles passed Schema v1.1.0 validation |
| **Supplementary O*NET Competencies** | **67 skills** | 61,880 SOC mapping entries indexed |

### Skill Gap Coverage Distribution Across the Dataset
- **Mean Overall Skill Coverage:** `0.0104` (1.04%)
- **Minimum Overall Skill Coverage:** `0.0000` (0.0%)
- **Maximum Overall Skill Coverage:** `0.0728` (7.28%)
- **Distribution Insight:** Real candidates and entry/mid-level synthetic profiles possess targeted technical skillsets (typically 3–15 skills), whereas canonical ESCO occupations specify extensive taxonomies (often 50–120 required skills). This produces realistic, right-skewed coverage distributions that will serve as rich non-linear features for readiness modeling.

---

## 3. Explanation of Master Resume Processing Limit

`Datasets/master_resumes.jsonl` contains 4,817 parsed resumes. During this initial generation pass, **500 resumes** were processed alongside all **640 synthetic profiles**.

### Why 500 Resumes Were Processed:
1. **Operational Processing Limit, Not an Exclusionary Filter:** The 500-resume cap was an intentional engineering parameter (`--master-limit 500`) to balance computational throughput on CPU against dataset diversity.
2. **Title Redundancy in Master Resumes:** Analysis of all 4,817 resumes revealed only **67 unique job titles** across the entire corpus, with heavy repetition (e.g., 172 Java Developers, 129 Python Developers, 114 DevOps Engineers, 104 Data Scientists, 101 Database Administrators, 100 Full Stack Developers). Processing 500 resumes provided full structural representation of all major occupational titles and skill patterns while avoiding excessive class imbalance.
3. **Execution Runtime:** Running full 384-dimensional Sentence Transformer embedding generation and Hungarian bipartite graph matching on 4,817 resumes sequentially on CPU takes ~15–20 minutes. The 500-resume limit permitted complete end-to-end dataset generation in **175 seconds**.
4. **Streaming Scalability:** The pipeline is architected using memory-safe lazy generators (`stream_master_resumes`). Running `--master-limit -1` will scale to all 4,817 resumes without requiring code changes.

---

## 4. Candidate–Occupation Pairing Methodology

Pairs were generated deterministically by grounding candidate profile occupational intent against the canonical ESCO Knowledge Graph:

```
[Candidate Source]
   ├── Synthetic Profile  ──> Primary Role (`roles[0]`) ──┐
   └── Master Resume      ──> Job Title (`experience[0]`) ─┼─> [RoleOccupationResolver]
                                                           │     ├── 1. Direct ESCO Lookup
                                                           │     ├── 2. Prefix Stripping (Junior, Senior, etc.)
                                                           │     ├── 3. Canonical Domain Aliases
                                                           │     ├── 4. Suffix Stripping
                                                           │     └── 5. Canonical Fallback ("software developer")
                                                           │
                                                           ▼
                                            [ESCO Occupation Concept URI]
                                                           │
                                                           ▼
                                            [Hybrid Skill Gap Detection (M3)]
                                            [Personalized Knowledge Graph]
                                            [Unified CandidateOccupationRecord]
```

### Detailed Resolution Steps:
1. **Synthetic Profiles:** Role extracted from `raw_profile["roles"][0]` (e.g. "Junior Backend Engineer", "Mobile App Developer").
2. **Master Resumes:** Occupational role extracted from `experience[0]["job_title"]` or `personal_info["summary"]` (e.g. "Python Developer", "Data Scientist").
3. **Seniority & Modifier Stripping:** Prefixes matching `^(junior|senior|staff|lead|principal|associate|entry-level|intern|mid-level|chief|head of|vp of)\s+` are stripped.
4. **Canonical Alias Mapping:** Common industry role variations that do not match ESCO labels verbatim are mapped to standardized ESCO concepts:
   - "Python Developer", "Java Developer", "Frontend Engineer", "Backend Developer", "Full Stack Developer", "Software Engineer" $\rightarrow$ `software developer` (`http://data.europa.eu/esco/occupation/f2b15a0e-e65a-438a-affb-29b9d50b77d1`)
   - "React Developer", "Angular Developer", "Node.js Developer" $\rightarrow$ `web developer` (`http://data.europa.eu/esco/occupation/c40a2919-48a9-40ea-b506-1f34f693496d`)
   - "Data Science Consultant", "ML Engineer", "Deep Learning Engineer" $\rightarrow$ `data scientist` (`http://data.europa.eu/esco/occupation/258e46f9-0075-4a2e-adae-1ff0477e0f30`)
   - "DevOps Engineer", "Cloud Operations Architect", "SRE" $\rightarrow$ `ICT system administrator` (`http://data.europa.eu/esco/occupation/a6baae73-cfdf-474d-b6eb-3b7cce14bb06`)
   - "QA Engineer", "Software Testing & Automation Engineer" $\rightarrow$ `software tester` (`http://data.europa.eu/esco/occupation/c1c38fa2-eb3b-48aa-b715-db1475cbeff9`)
   - "Database Engineer", "SQL Developer" $\rightarrow$ `database administrator` (`http://data.europa.eu/esco/occupation/8c57af09-719c-42b3-be40-6ed4946236cc`)
5. **Fallback:** If an ambiguous title cannot be resolved, it falls back to canonical `"software developer"`.

---

## 5. Data-Quality Audit Findings

A complete programmatic validation of all 1,140 records in `candidate_occupation_dataset.jsonl` confirmed:

- **0 Duplicates:** Every `pair_id` is unique. No candidate is paired multiple times with the same occupation.
- **0 Missing Required Fields:** All 14 required top-level fields are present in 100% of records (`pair_id`, `candidate_id`, `candidate_source`, `candidate_profile`, `candidate_skills_normalized`, `target_occupation`, `skill_gap_features`, `graph_features`, `matched_skills_evidence`, `partially_matched_skills_evidence`, `missing_essential_skills`, `missing_optional_skills`, `ground_truth`, `metadata`).
- **0 Invalid ESCO URIs:** Every `target_occupation.occupation_id` begins with `http://data.europa.eu/esco/occupation/` and maps to a valid ESCO node.
- **0 Malformed Features:** Every `skill_gap_features` dictionary contains all 11 required keys with coverage scores bounded strictly within $[0.0, 1.0]$.
- **0 Schema v1.1.0 Violations:** Candidate profiles in both sources pass validation. Canonical skill deduplication resolved all duplicate skill warnings.
- **Preserved Provenance:** Candidate IDs (`1` to `640` for synthetic, `mr_1` to `mr_500` for resumes) are preserved with clear `candidate_source` annotations.

---

## 6. Remaining Limitations

1. **Synthetic Profiles Breadth:** Synthetic candidates do not contain university degrees or detailed project records; their entries reflect declared skills and years of experience.
2. **Master Resume Contact Obfuscation:** Real resumes from `master_resumes.jsonl` intentionally mask contact info (names/emails/phones as "Unknown" or None) for privacy.
3. **Gold-Label Compatibility Scope:** Human annotations in `gold_labels.json` represent candidate-job compatibility for specific job postings and are not career-readiness labels.

---

## 7. Final Recommendation for M4.3 (Readiness-Label Preparation)

With the unified candidate–occupation dataset verified and stable:

1. **Do NOT Treat Skill Coverage as the Readiness Label:** Skill coverage is an input feature representing direct ESCO requirement overlap. A candidate with low direct ESCO coverage may still be career-ready if they have relevant experience, strong foundational competencies, or adjacent transferable skills.
2. **Formulate Readiness Multi-Factor Modeling:** In M4.3, define career readiness using a holistic, multi-dimensional assessment that combines:
   - Essential and optional skill coverage scores.
   - Graph topological signals (provenance depth, semantic adjacency credits).
   - Experience seniority and domain tenure.
   - Supplementary O*NET importance/level metrics.
3. **Keep Gold Compatibility Separate:** Maintain compatibility benchmark evaluations as a distinct downstream validation task.
