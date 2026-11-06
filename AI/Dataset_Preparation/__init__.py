"""Dataset Preparation package for Road2Hire M4.2 (Unified Candidate-Occupation Dataset).

Provides:
- Source dataset schemas (MasterResumeRecord, ScrapedJobRecord, SyntheticProfileRecord, GoldLabelRecord, etc.)
- Unified candidate-occupation schema (CandidateOccupationRecord, SkillGapSummaryFeatures, GraphTopologicalFeatures)
- Dataset inventory scanner and lazy streaming access (get_dataset_inventory, stream_master_resumes, etc.)
- Candidate profile adapters (adapt_master_resume_to_candidate_profile)
- Target occupation adapters (adapt_esco_occupation, adapt_scraped_job)
"""

from AI.Dataset_Preparation.candidate_adapter import (
    adapt_master_resume_to_candidate_profile,
    adapt_synthetic_profile_to_candidate_profile,
)
from AI.Dataset_Preparation.build_unified_dataset import (
    RoleOccupationResolver,
    UnifiedDatasetBuilder,
    load_onet_supplementary_data,
)
from AI.Dataset_Preparation.external_candidate_adapter import (
    adapt_external_cv_to_candidate_profile,
)
from AI.Dataset_Preparation.external_compatibility_benchmark import (
    BenchmarkMetrics,
    ExternalCompatibilityBenchmark,
    compute_correlation_metrics,
)
from AI.Dataset_Preparation.external_dataset_loader import (
    load_external_cvs_records,
    load_external_jobs_records,
    load_external_matches_records,
    safe_parse_json_list,
    stream_external_cvs,
    stream_external_jobs,
    stream_external_matches,
)
from AI.Dataset_Preparation.external_dataset_validator import (
    ExternalDatasetValidator,
    ValidationReport,
)
from AI.Dataset_Preparation.external_occupation_adapter import (
    adapt_external_job_to_occupation,
)
from AI.Dataset_Preparation.dataset_inventory import (
    get_dataset_inventory,
    get_datasets_dir,
    get_gold_label_index,
    load_gold_labels,
    load_scraped_jobs,
    load_synthetic_profiles,
    stream_master_resumes,
)
from AI.Dataset_Preparation.gold_label_audit import (
    audit_gold_labels,
    classify_record_status,
    parse_pair_id,
)
from AI.Dataset_Preparation.occupation_adapter import (
    adapt_esco_occupation,
    adapt_scraped_job,
)
from AI.Dataset_Preparation.source_schemas import (
    ESCOSkillMappingRecord,
    GoldLabelRecord,
    MasterResumeRecord,
    ONETSkillMappingRecord,
    ScrapedJobRecord,
    SyntheticProfileRecord,
)
from AI.Dataset_Preparation.unified_schema import (
    CandidateOccupationRecord,
    GraphTopologicalFeatures,
    GroundTruthAlignment,
    OccupationRequirementSummary,
    SkillGapSummaryFeatures,
)

__all__ = [
    # Schemas
    "MasterResumeRecord",
    "ScrapedJobRecord",
    "SyntheticProfileRecord",
    "GoldLabelRecord",
    "ESCOSkillMappingRecord",
    "ONETSkillMappingRecord",
    "CandidateOccupationRecord",
    "SkillGapSummaryFeatures",
    "GraphTopologicalFeatures",
    "GroundTruthAlignment",
    "OccupationRequirementSummary",
    # Inventory & Loaders
    "get_datasets_dir",
    "get_dataset_inventory",
    "stream_master_resumes",
    "load_scraped_jobs",
    "load_synthetic_profiles",
    "load_gold_labels",
    "get_gold_label_index",
    # Audit
    "audit_gold_labels",
    "classify_record_status",
    "parse_pair_id",
    # Adapters & Builders
    "adapt_master_resume_to_candidate_profile",
    "adapt_synthetic_profile_to_candidate_profile",
    "adapt_esco_occupation",
    "adapt_scraped_job",
    "UnifiedDatasetBuilder",
    "RoleOccupationResolver",
    "load_onet_supplementary_data",
    # External Dataset Integration
    "stream_external_cvs",
    "stream_external_jobs",
    "stream_external_matches",
    "load_external_cvs_records",
    "load_external_jobs_records",
    "load_external_matches_records",
    "safe_parse_json_list",
    "adapt_external_cv_to_candidate_profile",
    "adapt_external_job_to_occupation",
    "ExternalDatasetValidator",
    "ValidationReport",
    "ExternalCompatibilityBenchmark",
    "compute_correlation_metrics",
    "BenchmarkMetrics",
]

