"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import {
  CertificationsSection,
  EducationSection,
  ExperienceSection,
  ProfileSkills,
  ProjectsSection,
} from "@/components/profile/ResumeProfileSections";
import { uploadResume, validateResumeFile } from "@/components/profile/resume-upload-service";
import type { ResumeExtractionResultV1 } from "@/components/profile/resume-extraction-contract";
import { useCandidateProfile } from "@/components/profile/CandidateProfileProvider";

type UploadState = "empty" | "selected" | "uploading" | "processing" | "success" | "error";
const formatSize = (size: number) => size < 1024 * 1024 ? `${Math.max(1, Math.round(size / 1024))} KB` : `${(size / (1024 * 1024)).toFixed(1)} MB`;

function ResumeProcessingStatus({ state, message }: { state: UploadState; message: string }) {
  const labels: Record<UploadState, string> = {
    empty: "No resume uploaded", selected: "Resume selected · Ready to upload", uploading: "Uploading resume…",
    processing: "Resume analysis in progress…", success: "Resume analysis complete", error: "Resume upload or analysis failed",
  };
  return <div role={state === "error" ? "alert" : "status"} aria-live="polite" className={`rounded-xl border px-4 py-3 text-sm ${state === "error" ? "border-rose-200 bg-rose-50 text-rose-800" : state === "success" ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-slate-200 bg-slate-50 text-slate-700"}`}>
    <p className="font-semibold">{labels[state]}</p>{message && <p className="mt-1">{message}</p>}
  </div>;
}

export default function ResumePage() {
  const inputRef = useRef<HTMLInputElement>(null);
  const { profile, setResumeMetadata, resetResumeMetadata } = useCandidateProfile();
  const [file, setFile] = useState<File | null>(null);
  const [state, setState] = useState<UploadState>("empty");
  const [message, setMessage] = useState("");
  const [dragging, setDragging] = useState(false);
  const [result, setResult] = useState<ResumeExtractionResultV1 | null>(null);
  const previewUrl = useRef<string | null>(null);
  const [previewLink, setPreviewLink] = useState<string | null>(null);

  useEffect(() => () => { if (previewUrl.current) URL.revokeObjectURL(previewUrl.current); }, []);

  function clearLocalFile() {
    if (previewUrl.current) URL.revokeObjectURL(previewUrl.current);
    previewUrl.current = null;
    setPreviewLink(null);
    setFile(null);
    setResult(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  function chooseFile(candidate?: File) {
    if (!candidate) return;
    const issue = validateResumeFile(candidate);
    setResult(null);
    if (issue) {
      clearLocalFile();
      resetResumeMetadata();
      setState("error");
      setMessage(issue);
      return;
    }
    if (previewUrl.current) URL.revokeObjectURL(previewUrl.current);
    const nextPreviewUrl = URL.createObjectURL(candidate);
    previewUrl.current = nextPreviewUrl;
    setPreviewLink(nextPreviewUrl);
    setFile(candidate);
    setResumeMetadata({
      fileName: candidate.name,
      fileSize: candidate.size,
      fileType: candidate.type || candidate.name.split(".").pop()?.toLowerCase() || null,
      status: "selected",
    });
    setState("selected");
    setMessage("");
  }

  async function submit() {
    if (!file || state === "uploading" || state === "processing") return;
    setState("uploading"); setMessage("Sending the selected file to the resume service.");
    try {
      const extraction = await uploadResume(file);
      if (extraction.status === "queued" || extraction.status === "processing") {
        setResult(extraction); setState("processing"); setMessage("The service accepted the file and is still processing it.");
      } else if (extraction.status === "failed" || extraction.status === "unsupported" || extraction.status === "malformed") {
        setResult(extraction); setState("error"); setMessage(extraction.warnings[0]?.message ?? "The resume could not be processed.");
      } else {
        setResult(extraction); setState("success"); setMessage(extraction.status === "partial" ? "Partial profile information was extracted; review the available fields below." : "Your extracted profile is ready below.");
      }
    } catch (error) {
      setState("error"); setMessage(error instanceof Error ? error.message : "A network or server error prevented resume processing.");
    }
  }

  function removeFile() {
    clearLocalFile();
    resetResumeMetadata();
    setState("empty");
    setMessage("");
  }

  const rememberedResume = !file && profile.resume.status !== "empty";
  const status = state === "empty" && rememberedResume ? "selected" : state;

  return <main className="min-h-screen bg-background px-4 pb-8 pt-16 sm:px-6 md:py-8 lg:px-8">
    <div className="mx-auto max-w-[1180px]">
      <header className="mb-7 border-b border-slate-200 pb-6">
        <p className="mb-1 text-sm font-semibold text-primary">Resume intelligence</p>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between"><div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">Resume and candidate profile</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">Select a resume to prepare it for analysis. Profile details appear only after a connected service returns verified extraction data.</p>
        </div><Link href="/" className="text-sm font-semibold text-indigo-700 hover:text-indigo-900">Back to dashboard</Link></div>
      </header>

      <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(280px,0.8fr)]" aria-label="Resume upload">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <h2 className="text-lg font-semibold text-slate-900">Upload a resume</h2>
          <p className="mt-1 text-sm text-slate-500">PDF, DOC, or DOCX · Maximum 10 MB</p>
          <input ref={inputRef} type="file" className="sr-only" accept=".pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document" aria-label="Choose resume file" onChange={(event) => chooseFile(event.target.files?.[0])} />
          <div onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragging(false); }} onDrop={(event) => { event.preventDefault(); setDragging(false); chooseFile(event.dataTransfer.files[0]); }} className={`mt-5 rounded-xl border-2 border-dashed p-6 text-center sm:p-9 ${dragging ? "border-indigo-500 bg-indigo-50" : "border-slate-300 bg-slate-50/70"}`}>
            <p className="font-semibold text-slate-800">Drop your resume here</p><p className="mt-1 text-sm text-slate-500">or choose a file from your device</p>
            <button type="button" onClick={() => inputRef.current?.click()} className="mt-4 min-h-11 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400">Choose resume</button>
          </div>
          {file && <div className="mt-4 flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 p-4">
            <div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold text-slate-800">{file.name}</p><p className="mt-1 text-xs text-slate-500">{formatSize(file.size)} · {file.type || "File type detected from extension"}</p></div>
            {file.type === "application/pdf" && previewLink && <a href={previewLink} target="_blank" rel="noreferrer" className="text-sm font-medium text-indigo-700 underline">Open PDF preview</a>}
            <button type="button" onClick={removeFile} disabled={state === "uploading" || state === "processing"} className="text-sm font-medium text-slate-600 underline disabled:opacity-50">Remove</button>
          </div>}
          <div className="mt-4"><ResumeProcessingStatus state={status} message={message || (rememberedResume ? "File details are remembered for this session. Choose the file again to preview or upload it." : "")} /></div>
          {rememberedResume && <div className="mt-3 flex items-center justify-between gap-3 rounded-xl border border-slate-200 p-4">
            <div className="min-w-0"><p className="truncate text-sm font-semibold text-slate-800">{profile.resume.fileName}</p><p className="mt-1 text-xs text-slate-500">{profile.resume.fileSize === null ? "Selected earlier in this session" : formatSize(profile.resume.fileSize)} · File must be reselected after navigation</p></div>
            <button type="button" onClick={removeFile} className="text-sm font-medium text-slate-600 underline">Remove</button>
          </div>}
          <button type="button" onClick={submit} disabled={!file || state === "uploading" || state === "processing" || state === "success"} className="mt-4 min-h-11 w-full rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-white hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300 focus-visible:ring-offset-2">
            {state === "uploading" ? "Uploading…" : state === "processing" ? "Processing…" : "Upload and analyze"}
          </button>
      <p className="mt-3 text-xs leading-5 text-slate-500">Resume upload is not connected yet. No file leaves this browser until the backend upload contract is implemented.</p>
        </div>
        <aside className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <h2 className="font-semibold text-slate-900">Processing summary</h2><p className="mt-2 text-sm leading-6 text-slate-600">The current backend includes local PDF text and skill extraction modules, but no resume upload endpoint or structured profile response route. This page validates and previews a selected file locally.</p>
          {file && previewLink && <a href={previewLink} download={file.name} className="mt-4 inline-flex text-sm font-semibold text-indigo-700 underline">Download selected file</a>}
          {result && <p className="mt-4 text-xs text-slate-500">Extraction status: {result.status} · Contract: {result.contractVersion}</p>}
        </aside>
      </section>

      <section className="mt-8" aria-labelledby="candidate-profile-heading"><div className="mb-4"><p className="text-sm font-semibold text-primary">Candidate profile</p><h2 id="candidate-profile-heading" className="mt-1 text-2xl font-bold text-slate-900">Extracted information</h2><p className="mt-1 text-sm text-slate-500">Values below are sourced from the verified extraction response; unavailable fields remain empty.</p></div>
        {!result && <p className="mb-4 rounded-xl border border-dashed border-slate-300 bg-white p-5 text-sm text-slate-500">Your candidate profile will appear here when resume processing is connected.</p>}
        <div className="grid gap-4 md:grid-cols-2"><ProfileSkills data={result} /><EducationSection data={result} /><ExperienceSection data={result} /><ProjectsSection data={result} /><CertificationsSection data={result} /></div>
      </section>
    </div>
  </main>;
}
