import type {
  AnalysisStatus,
  DataProvenance,
  ResumeProcessingStatus,
  RoadmapCompletion,
  RoadmapPhase,
  RoadmapRecommendationPhase,
  RoadmapStatus,
  SampleReadinessCategory,
  SampleSkill,
} from "../../app/data/sample-data";
import {
  isVerifiedExtractedField,
  validateResumeExtractionPayload,
  type ExtractionStatus,
  type ExtractionValidationIssue,
  type ExtractedSkill,
  type ResumeExtractionResultV1,
} from "./resume-extraction-contract.ts";

export type { DataProvenance } from "../../app/data/sample-data";

export type CandidateResumeStatus = ResumeProcessingStatus;

export type CandidateResumeMetadata = {
  fileName: string | null;
  fileSize: number | null;
  fileType: string | null;
  status: CandidateResumeStatus;
  sourceFingerprint: string | null;
  provenance: DataProvenance;
};

export type CandidateAnalysis = {
  status: AnalysisStatus;
  sourceFingerprint: string | null;
  version: number;
  provenance: DataProvenance;
};

export type CandidateRoadmap = {
  recommendations: readonly RoadmapRecommendationPhase[];
  completions: readonly RoadmapCompletion[];
  status: AnalysisStatus;
  sourceFingerprint: string | null;
  provenance: DataProvenance;
};

export type CandidateExtractionSummary = {
  status: ExtractionStatus | "stale";
  sourceFingerprint: string;
  extractionVersion: string;
  provenance: Extract<DataProvenance, { kind: "resume_extracted" }>;
  warnings: ResumeExtractionResultV1["warnings"];
  candidate: {
    name: string | null;
    email: string | null;
    phone: string | null;
    location: string | null;
    links: readonly string[];
  };
  skills: {
    explicit: readonly CandidateExtractedSkill[];
    inferred: readonly CandidateExtractedSkill[];
  };
};

export type CandidateExtractedSkill = {
  id: string;
  name: string;
  normalizedName: string | null;
  aliases: readonly string[];
  source: ExtractedSkill["source"];
  provenance: Extract<DataProvenance, { kind: "resume_extracted" }>;
};

export type CandidateProfile = {
  targetRole: string;
  targetRoleProvenance: DataProvenance;
  resume: CandidateResumeMetadata;
  extraction: CandidateExtractionSummary | null;
  skills: readonly SampleSkill[];
  readiness: {
    overall: number;
    interview: number;
    status: AnalysisStatus;
    provenance: DataProvenance;
    categories: readonly SampleReadinessCategory[];
  };
  roadmap: CandidateRoadmap;
  analysis: CandidateAnalysis;
};

export type SelectedResumeMetadata = Partial<Pick<CandidateResumeMetadata, "fileType" | "sourceFingerprint">> & {
  fileName: string;
  fileSize: number;
  status: Exclude<CandidateResumeStatus, "empty">;
};

export type InitialCandidateProfile = Omit<CandidateProfile, "resume" | "extraction"> &
  Partial<Pick<CandidateProfile, "extraction">>;

export type ExtractionProfileMappingResult =
  | { accepted: true; profile: CandidateProfile; issues: [] }
  | { accepted: false; profile: CandidateProfile; issues: ExtractionValidationIssue[] };

const sampleProvenance: Extract<DataProvenance, { kind: "sample" }> = {
  kind: "sample",
  label: "Road2Hire demo profile",
};

const emptyResumeMetadata: CandidateResumeMetadata = {
  fileName: null,
  fileSize: null,
  fileType: null,
  status: "empty",
  sourceFingerprint: null,
  provenance: sampleProvenance,
};

export function createInitialCandidateProfile(seed: InitialCandidateProfile): CandidateProfile {
  return {
    targetRole: seed.targetRole,
    targetRoleProvenance: seed.targetRoleProvenance,
    resume: { ...emptyResumeMetadata },
    extraction: seed.extraction ? cloneExtraction(seed.extraction) : null,
    skills: seed.skills.map((skill) => ({ ...skill })),
    readiness: {
      overall: seed.readiness.overall,
      interview: seed.readiness.interview,
      status: seed.readiness.status,
      provenance: seed.readiness.provenance,
      categories: seed.readiness.categories.map((category) => ({ ...category })),
    },
    roadmap: {
      recommendations: seed.roadmap.recommendations.map((phase) => ({
        ...phase,
        recommendations: phase.recommendations.map((recommendation) => ({ ...recommendation })),
      })),
      completions: seed.roadmap.completions.map((completion) => ({ ...completion })),
      status: seed.roadmap.status,
      sourceFingerprint: seed.roadmap.sourceFingerprint,
      provenance: seed.roadmap.provenance,
    },
    analysis: { ...seed.analysis },
  };
}

export function updateResumeMetadata(
  profile: CandidateProfile,
  metadata: SelectedResumeMetadata,
): CandidateProfile {
  const sourceFingerprint = metadata.sourceFingerprint ?? createDemoResumeFingerprint(metadata);
  const resume = {
    fileName: metadata.fileName,
    fileSize: metadata.fileSize,
    fileType: metadata.fileType ?? null,
    status: metadata.status,
    sourceFingerprint,
    provenance: {
      kind: "user_provided" as const,
      updatedAt: sourceFingerprint,
    },
  };

  if (
    profile.resume.fileName === resume.fileName &&
    profile.resume.fileSize === resume.fileSize &&
    profile.resume.fileType === resume.fileType &&
    profile.resume.status === resume.status &&
    profile.resume.sourceFingerprint === resume.sourceFingerprint
  ) {
    return profile;
  }

  return invalidateDependentAnalysis({ ...profile, resume }, sourceFingerprint);
}

export function resetResumeMetadata(profile: CandidateProfile): CandidateProfile {
  if (
    profile.resume.status === "empty" &&
    profile.resume.fileName === null &&
    profile.resume.fileSize === null &&
    profile.resume.fileType === null &&
    profile.resume.sourceFingerprint === null
  ) {
    return profile;
  }
  return invalidateDependentAnalysis({ ...profile, resume: { ...emptyResumeMetadata } }, null);
}

export function completeRoadmapItem(profile: CandidateProfile, title: string): CandidateProfile {
  const target = getRoadmapPhases(profile.roadmap).flatMap((phase) => phase.items).find((item) => item.title === title);
  if (!target || (target.status === "Completed" && target.progress === 100)) return profile;

  const completions = profile.roadmap.completions.map((completion) =>
    completion.recommendationId === target.id
      ? { ...completion, status: "Completed" as RoadmapStatus, progress: 100 }
      : completion,
  );

  return { ...profile, roadmap: { ...profile.roadmap, completions } };
}

export function calculateRoadmapProgress(roadmap: CandidateRoadmap | readonly RoadmapPhase[]): number {
  const phases = "recommendations" in roadmap ? getRoadmapPhases(roadmap) : roadmap;
  const items = phases.flatMap((phase) => phase.items);
  if (items.length === 0) return 0;
  return Math.round(items.reduce((total, item) => total + item.progress, 0) / items.length);
}

export function getRoadmapPhases(roadmap: CandidateRoadmap): RoadmapPhase[] {
  return roadmap.recommendations.map((phase) => ({
    phase: phase.phase,
    name: phase.name,
    timeframe: phase.timeframe,
    items: phase.recommendations.map((recommendation) => {
      const completion = roadmap.completions.find((item) => item.recommendationId === recommendation.id);
      return {
        ...recommendation,
        status: completion?.status ?? "Upcoming",
        progress: completion?.progress ?? 0,
      };
    }),
  }));
}

export function replaceRoadmapRecommendations(
  profile: CandidateProfile,
  recommendations: readonly RoadmapRecommendationPhase[],
): CandidateProfile {
  const nextIds = new Set(recommendations.flatMap((phase) => phase.recommendations.map((item) => item.id)));
  const completions = profile.roadmap.completions.filter((completion) => nextIds.has(completion.recommendationId));
  const roadmap = {
    ...profile.roadmap,
    recommendations: recommendations.map((phase) => ({
      ...phase,
      recommendations: phase.recommendations.map((recommendation) => ({ ...recommendation })),
    })),
    completions,
  };

  return { ...profile, roadmap };
}

export function applyExtractionPayloadToCandidateProfile(
  profile: CandidateProfile,
  payload: unknown,
): ExtractionProfileMappingResult {
  const validation = validateResumeExtractionPayload(payload);
  if (!validation.ok) {
    return { accepted: false, profile, issues: validation.issues };
  }

  return applyValidatedExtractionToCandidateProfile(profile, validation.value);
}

export function applyValidatedExtractionToCandidateProfile(
  profile: CandidateProfile,
  extraction: ResumeExtractionResultV1,
): ExtractionProfileMappingResult {
  if (
    profile.resume.sourceFingerprint !== null &&
    profile.resume.sourceFingerprint !== extraction.sourceFingerprint
  ) {
    return {
      accepted: false,
      profile,
      issues: [{
        path: "$.sourceFingerprint",
        code: "invalid_provenance",
        message: "Extraction fingerprint does not match the selected resume.",
      }],
    };
  }

  const nextResume = {
    ...profile.resume,
    status: extraction.profileResumeStatus,
    sourceFingerprint: extraction.sourceFingerprint,
    provenance: extraction.provenance,
  };
  const nextProfile = {
    ...profile,
    resume: nextResume,
    extraction: mapExtractionSummary(extraction),
    analysis: {
      ...profile.analysis,
      status: extraction.profileAnalysisStatus,
      sourceFingerprint: extraction.sourceFingerprint,
      version: profile.analysis.version + 1,
      provenance: extraction.provenance,
    },
  };

  return { accepted: true, profile: nextProfile, issues: [] };
}

function createDemoResumeFingerprint(metadata: Pick<SelectedResumeMetadata, "fileName" | "fileSize" | "fileType">) {
  return `demo:${metadata.fileName}:${metadata.fileSize}:${metadata.fileType ?? "unknown"}`;
}

function invalidateDependentAnalysis(profile: CandidateProfile, sourceFingerprint: string | null): CandidateProfile {
  return {
    ...profile,
    extraction: invalidateExtraction(profile.extraction, sourceFingerprint),
    analysis: {
      ...profile.analysis,
      status: "sample",
      sourceFingerprint,
      provenance: sampleProvenance,
    },
  };
}

function invalidateExtraction(
  extraction: CandidateExtractionSummary | null,
  sourceFingerprint: string | null,
): CandidateExtractionSummary | null {
  if (!extraction || extraction.sourceFingerprint === sourceFingerprint) return extraction;
  return {
    ...extraction,
    status: "stale",
    candidate: {
      name: null,
      email: null,
      phone: null,
      location: null,
      links: [],
    },
    skills: {
      explicit: [],
      inferred: [],
    },
  };
}

function mapExtractionSummary(extraction: ResumeExtractionResultV1): CandidateExtractionSummary {
  const skills = extraction.skills.reduce<{
    explicit: CandidateExtractedSkill[];
    inferred: CandidateExtractedSkill[];
  }>(
    (groups, skill) => {
      const mapped = mapExtractedSkill(skill);
      if (!mapped) return groups;
      if (skill.source === "explicit") groups.explicit.push(mapped);
      else groups.inferred.push(mapped);
      return groups;
    },
    { explicit: [], inferred: [] },
  );

  return {
    status: extraction.status,
    sourceFingerprint: extraction.sourceFingerprint,
    extractionVersion: extraction.extractionVersion,
    provenance: extraction.provenance,
    warnings: extraction.warnings,
    candidate: {
      name: presentStringOrNull(extraction.candidate.name),
      email: presentStringOrNull(extraction.candidate.email),
      phone: presentStringOrNull(extraction.candidate.phone),
      location: presentStringOrNull(extraction.candidate.location),
      links: extraction.candidate.links.flatMap((link) => {
        const value = presentStringOrNull(link);
        return value ? [value] : [];
      }),
    },
    skills,
  };
}

function mapExtractedSkill(skill: ExtractedSkill): CandidateExtractedSkill | null {
  const name = presentStringOrNull(skill.name);
  if (!name) return null;

  return {
    id: skill.id,
    name,
    normalizedName: skill.normalizedName ?? null,
    aliases: skill.aliases,
    source: skill.source,
    provenance: skill.provenance,
  };
}

function presentStringOrNull(field: ResumeExtractionResultV1["candidate"]["name"]): string | null {
  return isVerifiedExtractedField(field) && typeof field.value === "string" ? field.value : null;
}

function cloneExtraction(extraction: CandidateExtractionSummary): CandidateExtractionSummary {
  return {
    ...extraction,
    warnings: extraction.warnings.map((warning) => ({ ...warning })),
    candidate: {
      ...extraction.candidate,
      links: [...extraction.candidate.links],
    },
    skills: {
      explicit: extraction.skills.explicit.map((skill) => ({ ...skill, aliases: [...skill.aliases] })),
      inferred: extraction.skills.inferred.map((skill) => ({ ...skill, aliases: [...skill.aliases] })),
    },
  };
}
