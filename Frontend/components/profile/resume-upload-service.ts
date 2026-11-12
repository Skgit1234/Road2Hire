import { validateResumeExtractionPayload, type ResumeExtractionResultV1 } from "./resume-extraction-contract.ts";

export const MAX_RESUME_BYTES = 5 * 1024 * 1024;
export const RESUME_EXTENSIONS = ["pdf"] as const;

export function validateResumeFile(file: Pick<File, "name" | "size"> & Partial<Pick<File, "type">>): string | null {
  const extension = file.name.split(".").pop()?.toLowerCase();
  if (!extension || !RESUME_EXTENSIONS.includes(extension as (typeof RESUME_EXTENSIONS)[number])) {
    return "This file type is not supported. Choose a PDF file.";
  }
  if (file.type && file.type !== "application/pdf") return "This file is not recognized as a PDF. Choose a valid PDF file.";
  if (file.size <= 0) return "This file is empty. Choose a resume with content.";
  if (file.size > MAX_RESUME_BYTES) return "This file is larger than 5 MiB. Choose a smaller resume file.";
  return null;
}

export function parseResumeExtractionResponse(payload: unknown): ResumeExtractionResultV1 {
  const result = validateResumeExtractionPayload(payload);
  if (!result.ok) throw new Error("The resume service returned data that does not match resume-extraction.v1.");
  return result.value;
}
