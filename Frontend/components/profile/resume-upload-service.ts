import { validateResumeExtractionPayload, type ResumeExtractionResultV1 } from "./resume-extraction-contract.ts";

export const MAX_RESUME_BYTES = 10 * 1024 * 1024;
export const RESUME_EXTENSIONS = ["pdf", "doc", "docx"] as const;

export function validateResumeFile(file: Pick<File, "name" | "size">): string | null {
  const extension = file.name.split(".").pop()?.toLowerCase();
  if (!extension || !RESUME_EXTENSIONS.includes(extension as (typeof RESUME_EXTENSIONS)[number])) {
    return "This file type is not supported. Choose a PDF, DOC, or DOCX file.";
  }
  if (file.size <= 0) return "This file is empty. Choose a resume with content.";
  if (file.size > MAX_RESUME_BYTES) return "This file is larger than 10 MB. Choose a smaller resume file.";
  return null;
}

/** Deliberately unconfigured until the backend defines an upload route and request format. */
export async function uploadResume(file: File): Promise<ResumeExtractionResultV1> {
  void file;
  throw new Error("Resume upload is not connected yet. The backend does not currently provide a resume upload endpoint.");
}

export function parseResumeExtractionResponse(payload: unknown): ResumeExtractionResultV1 {
  const result = validateResumeExtractionPayload(payload);
  if (!result.ok) throw new Error("The resume service returned data that does not match resume-extraction.v1.");
  return result.value;
}
