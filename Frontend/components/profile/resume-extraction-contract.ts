import type {
  AnalysisStatus,
  DataProvenance,
  ResumeProcessingStatus,
} from "../../app/data/sample-data";

export type ExtractionContractVersion = "resume-extraction.v1";

export const extractionContractVersion: ExtractionContractVersion = "resume-extraction.v1";

export type FieldState = "present" | "missing" | "ambiguous" | "rejected";

export type EvidenceSection =
  | "contact"
  | "education"
  | "experience"
  | "projects"
  | "skills"
  | "certifications"
  | "languages";

export type ExtractionWarningSeverity = "info" | "warning" | "error";

export type ExtractionWarningCode =
  | "unsupported_file_type"
  | "file_too_large"
  | "unreadable_document"
  | "malformed_document"
  | "missing_required_field"
  | "ambiguous_field"
  | "low_confidence"
  | "duplicate_record"
  | "conflicting_dates"
  | "partial_section"
  | "insufficient_evidence"
  | "validation_rejected";

export type ExtractionWarning = {
  code: ExtractionWarningCode;
  severity: ExtractionWarningSeverity;
  message: string;
  fieldPath?: string;
};

export type EvidenceReference = {
  section: EvidenceSection;
  page?: number;
  label?: string;
  snippet?: string;
};

export type Confidence = number;

export type ExtractedField<T> = {
  state: FieldState;
  value?: T;
  confidence?: Confidence;
  evidence?: readonly EvidenceReference[];
  warnings?: readonly ExtractionWarning[];
  rejectionReason?: string;
};

export type DatePrecision = "year" | "month" | "day";

export type ExtractedDateValue = {
  value: string;
  precision: DatePrecision;
};

export type ExtractedDate = ExtractedField<ExtractedDateValue>;

export type ExtractedDateRange = {
  start: ExtractedDate;
  end: ExtractedDate;
  isCurrent?: boolean;
  warnings?: readonly ExtractionWarning[];
};

export type ResumeExtractedProvenance = Extract<DataProvenance, { kind: "resume_extracted" }>;

export type ExtractedCandidateContact = {
  name: ExtractedField<string>;
  email: ExtractedField<string>;
  phone: ExtractedField<string>;
  location: ExtractedField<string>;
  links: readonly ExtractedField<string>[];
};

export type ExtractedEducation = {
  id: string;
  institution: ExtractedField<string>;
  degree: ExtractedField<string>;
  fieldOfStudy: ExtractedField<string>;
  dates: ExtractedDateRange;
  location?: ExtractedField<string>;
  provenance: ResumeExtractedProvenance;
};

export type ExtractedExperience = {
  id: string;
  organization: ExtractedField<string>;
  title: ExtractedField<string>;
  dates: ExtractedDateRange;
  location?: ExtractedField<string>;
  highlights: readonly ExtractedField<string>[];
  provenance: ResumeExtractedProvenance;
};

export type ExtractedProject = {
  id: string;
  name: ExtractedField<string>;
  description: ExtractedField<string>;
  dates?: ExtractedDateRange;
  links: readonly ExtractedField<string>[];
  skills: readonly string[];
  provenance: ResumeExtractedProvenance;
};

export type SkillExtractionSource = "explicit" | "inferred_from_title" | "inferred_from_context";

export type ExtractedSkill = {
  id: string;
  name: ExtractedField<string>;
  normalizedName?: string;
  aliases: readonly string[];
  source: SkillExtractionSource;
  category?: ExtractedField<string>;
  provenance: ResumeExtractedProvenance;
};

export type ExtractedCertification = {
  id: string;
  name: ExtractedField<string>;
  issuer: ExtractedField<string>;
  issuedDate?: ExtractedDate;
  expirationDate?: ExtractedDate;
  credentialId?: ExtractedField<string>;
  provenance: ResumeExtractedProvenance;
};

export type ExtractedLanguage = {
  id: string;
  name: ExtractedField<string>;
  proficiency: ExtractedField<string>;
  provenance: ResumeExtractedProvenance;
};

export type ExtractionStatus =
  | "queued"
  | "processing"
  | "succeeded"
  | "partial"
  | "unsupported"
  | "malformed"
  | "failed";

export type ExtractionProfileResumeStatus = Extract<
  ResumeProcessingStatus,
  "processing" | "unsupported" | "malformed" | "failed" | "ready"
>;

export type ExtractionProfileAnalysisStatus = Extract<
  AnalysisStatus,
  "ready" | "insufficient-data" | "stale"
>;

export type ResumeExtractionResultV1 = {
  contractVersion: ExtractionContractVersion;
  extractionVersion: string;
  sourceFingerprint: string;
  status: ExtractionStatus;
  profileResumeStatus: ExtractionProfileResumeStatus;
  profileAnalysisStatus: ExtractionProfileAnalysisStatus;
  provenance: ResumeExtractedProvenance;
  candidate: ExtractedCandidateContact;
  education: readonly ExtractedEducation[];
  experience: readonly ExtractedExperience[];
  projects: readonly ExtractedProject[];
  skills: readonly ExtractedSkill[];
  certifications: readonly ExtractedCertification[];
  languages: readonly ExtractedLanguage[];
  warnings: readonly ExtractionWarning[];
};

export type ExtractionValidationIssueCode =
  | "invalid_type"
  | "invalid_contract_version"
  | "invalid_status"
  | "invalid_field_state"
  | "invalid_confidence"
  | "invalid_evidence"
  | "invalid_warning"
  | "invalid_skill_source"
  | "invalid_date_precision"
  | "invalid_provenance";

export type ExtractionValidationIssue = {
  path: string;
  code: ExtractionValidationIssueCode;
  message: string;
};

export type ExtractionValidationResult =
  | { ok: true; value: ResumeExtractionResultV1; issues: [] }
  | { ok: false; issues: ExtractionValidationIssue[] };

const fieldStates = new Set<FieldState>(["present", "missing", "ambiguous", "rejected"]);
const evidenceSections = new Set<EvidenceSection>([
  "contact",
  "education",
  "experience",
  "projects",
  "skills",
  "certifications",
  "languages",
]);
const warningSeverities = new Set<ExtractionWarningSeverity>(["info", "warning", "error"]);
const warningCodes = new Set<ExtractionWarningCode>([
  "unsupported_file_type",
  "file_too_large",
  "unreadable_document",
  "malformed_document",
  "missing_required_field",
  "ambiguous_field",
  "low_confidence",
  "duplicate_record",
  "conflicting_dates",
  "partial_section",
  "insufficient_evidence",
  "validation_rejected",
]);
const extractionStatuses = new Set<ExtractionStatus>([
  "queued",
  "processing",
  "succeeded",
  "partial",
  "unsupported",
  "malformed",
  "failed",
]);
const profileResumeStatuses = new Set<ExtractionProfileResumeStatus>([
  "processing",
  "unsupported",
  "malformed",
  "failed",
  "ready",
]);
const profileAnalysisStatuses = new Set<ExtractionProfileAnalysisStatus>([
  "ready",
  "insufficient-data",
  "stale",
]);
const datePrecisions = new Set<DatePrecision>(["year", "month", "day"]);
const skillSources = new Set<SkillExtractionSource>([
  "explicit",
  "inferred_from_title",
  "inferred_from_context",
]);

export function createResumeExtractedProvenance(
  sourceFingerprint: string,
  extractionVersion: string,
): ResumeExtractedProvenance {
  return {
    kind: "resume_extracted",
    sourceFingerprint,
    extractionVersion,
  };
}

export function isValidConfidence(confidence: Confidence | undefined): boolean {
  return confidence === undefined || (Number.isFinite(confidence) && confidence >= 0 && confidence <= 1);
}

export function isVerifiedExtractedField<T>(
  field: ExtractedField<T>,
): field is ExtractedField<T> & { state: "present"; value: T } {
  return field.state === "present" && field.value !== undefined && isValidConfidence(field.confidence);
}

export function mapExtractionStatusToResumeStatus(
  status: ExtractionStatus,
): ExtractionProfileResumeStatus {
  switch (status) {
    case "queued":
    case "processing":
      return "processing";
    case "succeeded":
    case "partial":
      return "ready";
    case "unsupported":
      return "unsupported";
    case "malformed":
      return "malformed";
    case "failed":
      return "failed";
  }
}

export function validateResumeExtractionPayload(payload: unknown): ExtractionValidationResult {
  const issues: ExtractionValidationIssue[] = [];
  if (!isRecord(payload)) {
    return { ok: false, issues: [issue("$", "invalid_type", "Extraction payload must be an object.")] };
  }

  requireExact(payload.contractVersion, extractionContractVersion, "$.contractVersion", "invalid_contract_version", issues);
  requireString(payload.extractionVersion, "$.extractionVersion", issues);
  requireString(payload.sourceFingerprint, "$.sourceFingerprint", issues);
  requireSet(payload.status, extractionStatuses, "$.status", "invalid_status", issues);
  requireSet(payload.profileResumeStatus, profileResumeStatuses, "$.profileResumeStatus", "invalid_status", issues);
  requireSet(payload.profileAnalysisStatus, profileAnalysisStatuses, "$.profileAnalysisStatus", "invalid_status", issues);
  validateProvenance(payload.provenance, payload.sourceFingerprint, payload.extractionVersion, "$.provenance", issues);
  validateCandidate(payload.candidate, "$.candidate", issues);
  validateCollection(payload.education, "$.education", issues, validateEducation);
  validateCollection(payload.experience, "$.experience", issues, validateExperience);
  validateCollection(payload.projects, "$.projects", issues, validateProject);
  validateCollection(payload.skills, "$.skills", issues, validateSkill);
  validateCollection(payload.certifications, "$.certifications", issues, validateCertification);
  validateCollection(payload.languages, "$.languages", issues, validateLanguage);
  validateWarnings(payload.warnings, "$.warnings", issues);

  return issues.length === 0
    ? { ok: true, value: payload as ResumeExtractionResultV1, issues: [] }
    : { ok: false, issues };
}

function validateCandidate(value: unknown, path: string, issues: ExtractionValidationIssue[]) {
  if (!isRecord(value)) {
    issues.push(issue(path, "invalid_type", "Candidate section must be an object."));
    return;
  }
  validateField(value.name, `${path}.name`, issues);
  validateField(value.email, `${path}.email`, issues);
  validateField(value.phone, `${path}.phone`, issues);
  validateField(value.location, `${path}.location`, issues);
  validateCollection(value.links, `${path}.links`, issues, validateField);
}

function validateEducation(value: unknown, path: string, issues: ExtractionValidationIssue[]) {
  if (!validateRecordWithIdAndProvenance(value, path, issues)) return;
  validateField(value.institution, `${path}.institution`, issues);
  validateField(value.degree, `${path}.degree`, issues);
  validateField(value.fieldOfStudy, `${path}.fieldOfStudy`, issues);
  validateDateRange(value.dates, `${path}.dates`, issues);
  if (value.location !== undefined) validateField(value.location, `${path}.location`, issues);
}

function validateExperience(value: unknown, path: string, issues: ExtractionValidationIssue[]) {
  if (!validateRecordWithIdAndProvenance(value, path, issues)) return;
  validateField(value.organization, `${path}.organization`, issues);
  validateField(value.title, `${path}.title`, issues);
  validateDateRange(value.dates, `${path}.dates`, issues);
  if (value.location !== undefined) validateField(value.location, `${path}.location`, issues);
  validateCollection(value.highlights, `${path}.highlights`, issues, validateField);
}

function validateProject(value: unknown, path: string, issues: ExtractionValidationIssue[]) {
  if (!validateRecordWithIdAndProvenance(value, path, issues)) return;
  validateField(value.name, `${path}.name`, issues);
  validateField(value.description, `${path}.description`, issues);
  if (value.dates !== undefined) validateDateRange(value.dates, `${path}.dates`, issues);
  validateCollection(value.links, `${path}.links`, issues, validateField);
  validateStringCollection(value.skills, `${path}.skills`, issues);
}

function validateSkill(value: unknown, path: string, issues: ExtractionValidationIssue[]) {
  if (!validateRecordWithIdAndProvenance(value, path, issues)) return;
  validateField(value.name, `${path}.name`, issues);
  validateOptionalString(value.normalizedName, `${path}.normalizedName`, issues);
  validateStringCollection(value.aliases, `${path}.aliases`, issues);
  requireSet(value.source, skillSources, `${path}.source`, "invalid_skill_source", issues);
  if (value.category !== undefined) validateField(value.category, `${path}.category`, issues);
}

function validateCertification(value: unknown, path: string, issues: ExtractionValidationIssue[]) {
  if (!validateRecordWithIdAndProvenance(value, path, issues)) return;
  validateField(value.name, `${path}.name`, issues);
  validateField(value.issuer, `${path}.issuer`, issues);
  if (value.issuedDate !== undefined) validateDate(value.issuedDate, `${path}.issuedDate`, issues);
  if (value.expirationDate !== undefined) validateDate(value.expirationDate, `${path}.expirationDate`, issues);
  if (value.credentialId !== undefined) validateField(value.credentialId, `${path}.credentialId`, issues);
}

function validateLanguage(value: unknown, path: string, issues: ExtractionValidationIssue[]) {
  if (!validateRecordWithIdAndProvenance(value, path, issues)) return;
  validateField(value.name, `${path}.name`, issues);
  validateField(value.proficiency, `${path}.proficiency`, issues);
}

function validateRecordWithIdAndProvenance(
  value: unknown,
  path: string,
  issues: ExtractionValidationIssue[],
): value is Record<string, unknown> {
  if (!isRecord(value)) {
    issues.push(issue(path, "invalid_type", "Section item must be an object."));
    return false;
  }
  requireString(value.id, `${path}.id`, issues);
  validateProvenance(value.provenance, undefined, undefined, `${path}.provenance`, issues);
  return true;
}

function validateField(value: unknown, path: string, issues: ExtractionValidationIssue[]) {
  if (!isRecord(value)) {
    issues.push(issue(path, "invalid_type", "Extracted field must be an object."));
    return;
  }

  requireSet(value.state, fieldStates, `${path}.state`, "invalid_field_state", issues);
  if (value.confidence !== undefined && !isValidConfidence(value.confidence as Confidence)) {
    issues.push(issue(`${path}.confidence`, "invalid_confidence", "Confidence must be a finite number from 0 to 1."));
  }
  if (value.evidence !== undefined) validateCollection(value.evidence, `${path}.evidence`, issues, validateEvidence);
  if (value.warnings !== undefined) validateWarnings(value.warnings, `${path}.warnings`, issues);

  if (value.state === "present" && value.value === undefined) {
    issues.push(issue(`${path}.value`, "invalid_field_state", "Present fields must include a value."));
  }
  if (value.state === "missing" && value.value !== undefined) {
    issues.push(issue(`${path}.value`, "invalid_field_state", "Missing fields must not include a value."));
  }
  if (value.state === "rejected" && typeof value.rejectionReason !== "string") {
    issues.push(issue(`${path}.rejectionReason`, "invalid_field_state", "Rejected fields must include a rejection reason."));
  }
}

function validateDate(value: unknown, path: string, issues: ExtractionValidationIssue[]) {
  validateField(value, path, issues);
  if (!isRecord(value) || value.state !== "present") return;
  if (!isRecord(value.value)) {
    issues.push(issue(`${path}.value`, "invalid_type", "Present date value must be an object."));
    return;
  }
  requireString(value.value.value, `${path}.value.value`, issues);
  requireSet(value.value.precision, datePrecisions, `${path}.value.precision`, "invalid_date_precision", issues);
}

function validateDateRange(value: unknown, path: string, issues: ExtractionValidationIssue[]) {
  if (!isRecord(value)) {
    issues.push(issue(path, "invalid_type", "Date range must be an object."));
    return;
  }
  validateDate(value.start, `${path}.start`, issues);
  validateDate(value.end, `${path}.end`, issues);
  if (value.isCurrent !== undefined && typeof value.isCurrent !== "boolean") {
    issues.push(issue(`${path}.isCurrent`, "invalid_type", "Current-role marker must be a boolean."));
  }
  if (value.isCurrent === true && isRecord(value.end) && value.end.state === "present") {
    issues.push(issue(`${path}.end`, "invalid_field_state", "Current roles must not include a present end date."));
  }
  if (value.warnings !== undefined) validateWarnings(value.warnings, `${path}.warnings`, issues);
}

function validateEvidence(value: unknown, path: string, issues: ExtractionValidationIssue[]) {
  if (!isRecord(value)) {
    issues.push(issue(path, "invalid_evidence", "Evidence must be an object."));
    return;
  }
  requireSet(value.section, evidenceSections, `${path}.section`, "invalid_evidence", issues);
  const page = value.page;
  if (page !== undefined && (typeof page !== "number" || !Number.isInteger(page) || page < 1)) {
    issues.push(issue(`${path}.page`, "invalid_evidence", "Evidence page must be a positive integer."));
  }
  validateOptionalString(value.label, `${path}.label`, issues);
  validateOptionalString(value.snippet, `${path}.snippet`, issues);
}

function validateWarnings(value: unknown, path: string, issues: ExtractionValidationIssue[]) {
  validateCollection(value, path, issues, (warning, warningPath, collectionIssues) => {
    if (!isRecord(warning)) {
      collectionIssues.push(issue(warningPath, "invalid_warning", "Warning must be an object."));
      return;
    }
    requireSet(warning.code, warningCodes, `${warningPath}.code`, "invalid_warning", collectionIssues);
    requireSet(warning.severity, warningSeverities, `${warningPath}.severity`, "invalid_warning", collectionIssues);
    requireString(warning.message, `${warningPath}.message`, collectionIssues);
    validateOptionalString(warning.fieldPath, `${warningPath}.fieldPath`, collectionIssues);
  });
}

function validateCollection(
  value: unknown,
  path: string,
  issues: ExtractionValidationIssue[],
  validateItem: (item: unknown, path: string, issues: ExtractionValidationIssue[]) => void,
) {
  if (!Array.isArray(value)) {
    issues.push(issue(path, "invalid_type", "Expected an array."));
    return;
  }
  value.forEach((item, index) => validateItem(item, `${path}[${index}]`, issues));
}

function validateStringCollection(value: unknown, path: string, issues: ExtractionValidationIssue[]) {
  if (!Array.isArray(value)) {
    issues.push(issue(path, "invalid_type", "Expected an array."));
    return;
  }
  value.forEach((item, index) => requireString(item, `${path}[${index}]`, issues));
}

function validateProvenance(
  value: unknown,
  sourceFingerprint: unknown,
  extractionVersionValue: unknown,
  path: string,
  issues: ExtractionValidationIssue[],
) {
  if (!isRecord(value)) {
    issues.push(issue(path, "invalid_provenance", "Provenance must be an object."));
    return;
  }
  requireExact(value.kind, "resume_extracted", `${path}.kind`, "invalid_provenance", issues);
  requireString(value.sourceFingerprint, `${path}.sourceFingerprint`, issues);
  requireString(value.extractionVersion, `${path}.extractionVersion`, issues);
  if (sourceFingerprint !== undefined && value.sourceFingerprint !== sourceFingerprint) {
    issues.push(issue(`${path}.sourceFingerprint`, "invalid_provenance", "Provenance fingerprint must match payload fingerprint."));
  }
  if (extractionVersionValue !== undefined && value.extractionVersion !== extractionVersionValue) {
    issues.push(issue(`${path}.extractionVersion`, "invalid_provenance", "Provenance extraction version must match payload version."));
  }
}

function requireString(value: unknown, path: string, issues: ExtractionValidationIssue[]) {
  if (typeof value !== "string" || value.length === 0) {
    issues.push(issue(path, "invalid_type", "Expected a non-empty string."));
  }
}

function validateOptionalString(value: unknown, path: string, issues: ExtractionValidationIssue[]) {
  if (value !== undefined && typeof value !== "string") {
    issues.push(issue(path, "invalid_type", "Expected a string when present."));
  }
}

function requireSet<T extends string>(
  value: unknown,
  allowed: ReadonlySet<T>,
  path: string,
  code: ExtractionValidationIssueCode,
  issues: ExtractionValidationIssue[],
) {
  if (typeof value !== "string" || !allowed.has(value as T)) {
    issues.push(issue(path, code, `Expected one of: ${Array.from(allowed).join(", ")}.`));
  }
}

function requireExact(
  value: unknown,
  expected: string,
  path: string,
  code: ExtractionValidationIssueCode,
  issues: ExtractionValidationIssue[],
) {
  if (value !== expected) {
    issues.push(issue(path, code, `Expected ${expected}.`));
  }
}

function issue(
  path: string,
  code: ExtractionValidationIssueCode,
  message: string,
): ExtractionValidationIssue {
  return { path, code, message };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
