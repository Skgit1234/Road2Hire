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
import { validateResumeFile } from "@/components/profile/resume-upload-service";
import { useCandidateProfile } from "@/components/profile/CandidateProfileProvider";
import { useAuth } from "@/components/auth/AuthProvider";
import { deleteResume, downloadResume, getResumeAnalysis, listResumes, uploadResume, type ResumeAnalysisResponse, type ResumeRecord } from "@/lib/api-client";

type UploadState = "empty" | "selected" | "uploading" | "success" | "error";
type ListState = "loading" | "ready" | "error";
type AnalysisState = "idle" | "loading" | "ready" | "error";
const formatSize = (size: number) => size < 1024 * 1024 ? `${Math.max(1, Math.round(size / 1024))} KB` : `${(size / (1024 * 1024)).toFixed(1)} MB`;

function ResumeProcessingStatus({ state, message }: { state: UploadState; message: string }) {
  const labels: Record<UploadState, string> = {
    empty: "No file selected", selected: "PDF selected · Ready to upload", uploading: "Uploading resume…",
    success: "Resume uploaded", error: "Resume upload failed",
  };
  return <div role={state === "error" ? "alert" : "status"} aria-live="polite" className={`rounded-xl border px-4 py-3 text-sm ${state === "error" ? "border-rose-200 bg-rose-50 text-rose-800" : state === "success" ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-slate-200 bg-slate-50 text-slate-700"}`}>
    <p className="font-semibold">{labels[state]}</p>{message && <p className="mt-1">{message}</p>}
  </div>;
}

export default function ResumePage() {
  const inputRef = useRef<HTMLInputElement>(null);
  const uploadLock = useRef(false);
  const analysisRequest = useRef(0);
  const { profile, setResumeMetadata, resetResumeMetadata } = useCandidateProfile();
  const { session } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [state, setState] = useState<UploadState>("empty");
  const [message, setMessage] = useState("");
  const [dragging, setDragging] = useState(false);
  const [resumes, setResumes] = useState<ResumeRecord[]>([]);
  const [listState, setListState] = useState<ListState>("loading");
  const [listMessage, setListMessage] = useState("");
  const [analysisState, setAnalysisState] = useState<AnalysisState>("idle");
  const [analysis, setAnalysis] = useState<ResumeAnalysisResponse | null>(null);
  const [analysisError, setAnalysisError] = useState("");
  const [selectedAnalysisResume, setSelectedAnalysisResume] = useState<ResumeRecord | null>(null);
  const [resumeAction, setResumeAction] = useState<{ id: number; action: "download" | "delete" } | null>(null);
  const [resumeActionMessage, setResumeActionMessage] = useState("");
  const [resumeActionError, setResumeActionError] = useState("");
  const resumeActionLock = useRef(false);
  const previewUrl = useRef<string | null>(null);
  const [previewLink, setPreviewLink] = useState<string | null>(null);

  useEffect(() => () => { if (previewUrl.current) URL.revokeObjectURL(previewUrl.current); }, []);

  async function refreshResumes(token: string) {
    setListState("loading");
    setListMessage("");
    try {
      const records = await listResumes(token);
      setResumes(records);
      setListState("ready");
    } catch (error) {
      setListState("error");
      setListMessage(error instanceof Error ? error.message : "Could not load your resumes.");
    }
  }

  async function analyzeResume(resume: ResumeRecord) {
    if (!session) return;
    const requestId = ++analysisRequest.current;
    setSelectedAnalysisResume(resume);
    setAnalysis(null);
    setAnalysisError("");
    setAnalysisState("loading");
    try {
      const result = await getResumeAnalysis(resume.id, session.accessToken);
      if (requestId === analysisRequest.current) {
        setAnalysis(result);
        setAnalysisState("ready");
      }
    } catch (error) {
      if (requestId === analysisRequest.current) {
        setAnalysisError(error instanceof Error ? error.message : "Could not retrieve resume analysis.");
        setAnalysisState("error");
      }
    }
  }

  useEffect(() => {
    if (!session) return;
    let active = true;
    void Promise.resolve().then(() => {
      if (!active) return undefined;
      setListState("loading");
      return listResumes(session.accessToken);
    }).then((records) => {
      if (active && records) { setResumes(records); setListState("ready"); setListMessage(""); }
    }).catch((error: unknown) => {
      if (active) {
        setListState("error");
        setListMessage(error instanceof Error ? error.message : "Could not load your resumes.");
      }
    });
    return () => { active = false; };
  }, [session]);

  async function downloadSavedResume(resume: ResumeRecord) {
    if (!session || resumeActionLock.current) return;

    resumeActionLock.current = true;
    setResumeAction({ id: resume.id, action: "download" });
    setResumeActionMessage("");
    setResumeActionError("");

    try {
      const blob = await downloadResume(resume.id, session.accessToken);
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = resume.original_name;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
      setResumeActionMessage(`Download started for ${resume.original_name}.`);
    } catch (error) {
      setResumeActionError(error instanceof Error ? error.message : "Could not download this resume.");
    } finally {
      resumeActionLock.current = false;
      setResumeAction(null);
    }
  }

  async function deleteSavedResume(resume: ResumeRecord) {
    if (!session || resumeActionLock.current) return;

    const confirmed = window.confirm(
      `Delete "${resume.original_name}" from your saved resumes? This cannot be undone.`,
    );
    if (!confirmed) return;

    resumeActionLock.current = true;
    setResumeAction({ id: resume.id, action: "delete" });
    setResumeActionMessage("");
    setResumeActionError("");

    try {
      const result = await deleteResume(resume.id, session.accessToken);
      setResumes((current) => current.filter((item) => item.id !== resume.id));

      if (selectedAnalysisResume?.id === resume.id) {
        analysisRequest.current += 1;
        setSelectedAnalysisResume(null);
        setAnalysis(null);
        setAnalysisError("");
        setAnalysisState("idle");
      }

      setResumeActionMessage(result.message);
      await refreshResumes(session.accessToken);
    } catch (error) {
      setResumeActionError(error instanceof Error ? error.message : "Could not delete this resume.");
      // Reconcile the list: the backend can delete metadata before file removal fails.
      await refreshResumes(session.accessToken);
    } finally {
      resumeActionLock.current = false;
      setResumeAction(null);
    }
  }
  function clearLocalFile() {
    if (previewUrl.current) URL.revokeObjectURL(previewUrl.current);
    previewUrl.current = null;
    setPreviewLink(null);
    setFile(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  function chooseFile(candidate?: File) {
    if (!candidate || uploadLock.current) return;
    const issue = validateResumeFile(candidate);
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
      fileType: candidate.type || "application/pdf",
      status: "selected",
    });
    setState("selected");
    setMessage("");
  }

  async function submit() {
    if (!file || !session || uploadLock.current) return;
    uploadLock.current = true;
    setState("uploading");
    setMessage("Sending the selected PDF to the backend.");
    try {
      const response = await uploadResume(file, session.profile.id, session.accessToken);
      setState("success");
      setMessage(response.message || "The resume was uploaded successfully.");
      await refreshResumes(session.accessToken);
    } catch (error) {
      setState("error");
      setMessage(error instanceof Error ? error.message : "A network or server error prevented the resume upload.");
    } finally {
      uploadLock.current = false;
    }
  }

  function removeFile() {
    clearLocalFile();
    resetResumeMetadata();
    setState("empty");
    setMessage("");
  }

  const rememberedResume = !file && profile.resume.status !== "empty";

  return <main className="min-h-screen bg-background px-4 pb-8 pt-16 sm:px-6 md:py-8 lg:px-8">
    <div className="mx-auto max-w-[1180px]">
      <header className="mb-7 border-b border-slate-200 pb-6">
        <p className="mb-1 text-sm font-semibold text-primary">Resume intelligence</p>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between"><div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">Resume and candidate profile</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">Upload a PDF resume and review files saved to your account. Profile details appear only after a connected service returns verified extraction data.</p>
        </div><Link href="/" className="text-sm font-semibold text-indigo-700 hover:text-indigo-900">Back to dashboard</Link></div>
      </header>

      <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(280px,0.8fr)]" aria-label="Resume upload">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <h2 className="text-lg font-semibold text-slate-900">Upload a resume</h2>
          <p className="mt-1 text-sm text-slate-500">PDF only · Maximum 5 MiB</p>
          <input ref={inputRef} type="file" className="sr-only" accept=".pdf,application/pdf" aria-label="Choose resume file" onChange={(event) => chooseFile(event.target.files?.[0])} />
          <div onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragging(false); }} onDrop={(event) => { event.preventDefault(); setDragging(false); chooseFile(event.dataTransfer.files[0]); }} className={`mt-5 rounded-xl border-2 border-dashed p-6 text-center sm:p-9 ${dragging ? "border-indigo-500 bg-indigo-50" : "border-slate-300 bg-slate-50/70"}`}>
            <p className="font-semibold text-slate-800">Drop your resume here</p><p className="mt-1 text-sm text-slate-500">or choose a PDF from your device</p>
            <button type="button" onClick={() => inputRef.current?.click()} className="mt-4 min-h-11 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400">Choose PDF</button>
          </div>
          {file && <div className="mt-4 flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 p-4">
            <div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold text-slate-800">{file.name}</p><p className="mt-1 text-xs text-slate-500">{formatSize(file.size)} · PDF</p></div>
            {previewLink && <a href={previewLink} target="_blank" rel="noreferrer" className="text-sm font-medium text-indigo-700 underline">Open PDF preview</a>}
            <button type="button" onClick={removeFile} disabled={state === "uploading"} className="text-sm font-medium text-slate-600 underline disabled:opacity-50">Remove</button>
          </div>}
          <div className="mt-4"><ResumeProcessingStatus state={state} message={message || (rememberedResume ? "File details are remembered for this session. Choose the PDF again to preview or upload it." : "")} /></div>
          {rememberedResume && <div className="mt-3 flex items-center justify-between gap-3 rounded-xl border border-slate-200 p-4">
            <div className="min-w-0"><p className="truncate text-sm font-semibold text-slate-800">{profile.resume.fileName}</p><p className="mt-1 text-xs text-slate-500">{profile.resume.fileSize === null ? "Selected earlier in this session" : formatSize(profile.resume.fileSize)} · File must be reselected after navigation</p></div>
            <button type="button" onClick={removeFile} className="text-sm font-medium text-slate-600 underline">Remove</button>
          </div>}
          {!session && <p className="mt-3 text-sm text-amber-800" role="status">Sign in before uploading or viewing saved resumes. <Link className="font-semibold underline" href="/login">Go to sign in</Link></p>}
          <button type="button" onClick={submit} disabled={!file || !session || state === "uploading" || state === "success"} className="mt-4 min-h-11 w-full rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-white hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300 focus-visible:ring-offset-2">
            {state === "uploading" ? "Uploading…" : "Upload PDF"}
          </button>
          <p className="mt-3 text-xs leading-5 text-slate-500">A successful upload saves the PDF to your account. Resume analysis is not part of this step.</p>
        </div>
        <aside className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <h2 className="font-semibold text-slate-900">Saved resumes</h2>
          {resumeActionMessage && <p className="mt-2 text-sm text-emerald-800" role="status">{resumeActionMessage}</p>}
          {resumeActionError && <p className="mt-2 text-sm text-rose-800" role="alert">{resumeActionError}</p>}
          {!session ? <p className="mt-2 text-sm leading-6 text-slate-600">Sign in to load resumes associated with your account.</p> : listState === "loading" ? <p className="mt-2 text-sm text-slate-600" role="status">Loading your resumes…</p> : listState === "error" ? <div className="mt-2" role="alert"><p className="text-sm text-rose-800">{listMessage}</p><button type="button" onClick={() => void refreshResumes(session.accessToken)} className="mt-3 text-sm font-semibold text-indigo-700 underline">Retry</button></div> : resumes.length === 0 ? <p className="mt-2 text-sm text-slate-600" role="status">No resumes have been uploaded yet.</p> : <ul className="mt-3 divide-y divide-slate-100">
            {resumes.map((resume) => {
              const downloading = resumeAction?.id === resume.id && resumeAction.action === "download";
              const deleting = resumeAction?.id === resume.id && resumeAction.action === "delete";
              const actionBusy = resumeAction !== null;
              return <li key={resume.id} className="py-3">
                <p className="break-words text-sm font-medium text-slate-800">{resume.original_name}</p>
                <p className="mt-1 text-xs text-slate-500">Uploaded {new Date(resume.uploaded_at).toLocaleString()}</p>
                <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2">
                  <button type="button" onClick={() => void analyzeResume(resume)}
                    disabled={analysisState === "loading" || actionBusy}
                    className="text-sm font-semibold text-indigo-700 underline disabled:opacity-50">
                    {analysisState === "loading" && selectedAnalysisResume?.id === resume.id ? "Analyzing…" : "Analyze"}
                  </button>
                  <button type="button" onClick={() => void downloadSavedResume(resume)}
                    disabled={actionBusy}
                    className="text-sm font-semibold text-slate-700 underline disabled:opacity-50">
                    {downloading ? "Downloading…" : "Download"}
                  </button>
                  <button type="button" onClick={() => void deleteSavedResume(resume)}
                    disabled={actionBusy}
                    className="text-sm font-semibold text-rose-700 underline disabled:opacity-50">
                    {deleting ? "Deleting…" : "Delete"}
                  </button>
                </div>
              </li>;
            })}
          </ul>}
        </aside>
      </section>

      <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6" aria-labelledby="resume-analysis-heading">
        <div className="mb-4"><p className="text-sm font-semibold text-primary">Backend analysis</p><h2 id="resume-analysis-heading" className="mt-1 text-2xl font-bold text-slate-900">Resume analysis results</h2><p className="mt-1 text-sm text-slate-500">Choose Analyze on a saved resume to request its current backend analysis.</p></div>
        {!session ? <p className="text-sm text-slate-600" role="status">Sign in to request resume analysis.</p> : analysisState === "idle" ? <p className="text-sm text-slate-600" role="status">Analysis has not been requested in this view.</p> : analysisState === "loading" ? <p className="text-sm text-slate-600" role="status">Analyzing {selectedAnalysisResume?.original_name ?? "resume"}…</p> : analysisState === "error" ? <p className="text-sm text-rose-800" role="alert">{analysisError}</p> : analysis && <div aria-live="polite">
          <p className="text-sm font-semibold text-slate-800">Analysis completed for {analysis.original_name}</p>
          <p className="mt-1 text-xs text-slate-500">{analysis.page_count} pages · Pipeline {analysis.pipeline_version} · Skill extraction: {analysis.skill_extraction_method}</p>
          {Object.keys(analysis.sections).length === 0 && analysis.extracted_skills.length === 0 ? <p className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">Analysis completed, but no text sections or skills were detected.</p> : <div className="mt-4 grid gap-5 md:grid-cols-2">
            <section aria-label="Detected resume sections"><h3 className="font-semibold text-slate-800">Detected sections</h3>{Object.keys(analysis.sections).length === 0 ? <p className="mt-2 text-sm text-slate-500">No sections were detected.</p> : <ul className="mt-2 space-y-3">{Object.entries(analysis.sections).map(([name, text]) => <li key={name} className="rounded-xl bg-slate-50 p-3"><h4 className="text-sm font-medium capitalize text-slate-800">{name.replaceAll("_", " ")}</h4><p className="mt-1 whitespace-pre-wrap break-words text-sm text-slate-600">{text}</p></li>)}</ul>}</section>
            <section aria-label="Keyword matched skills"><h3 className="font-semibold text-slate-800">Keyword-matched skills</h3>{analysis.extracted_skills.length === 0 ? <p className="mt-2 text-sm text-slate-500">No skills matched the backend vocabulary.</p> : <ul className="mt-2 space-y-2">{analysis.extracted_skills.map((skill) => <li key={skill.skill} className="rounded-xl bg-indigo-50 p-3"><p className="font-medium text-indigo-900">{skill.skill}</p><p className="mt-1 text-xs text-indigo-800">Found in {skill.source_sections.join(", ") || "no recorded section"} · {skill.occurrences.length} match{skill.occurrences.length === 1 ? "" : "es"}</p></li>)}</ul>}<p className="mt-3 text-xs text-slate-500">These are backend keyword matches, not verified resume-extraction.v1 skills.</p></section>
          </div>}
        </div>}
      </section>

      <section className="mt-8" aria-labelledby="candidate-profile-heading"><div className="mb-4"><p className="text-sm font-semibold text-primary">Candidate profile</p><h2 id="candidate-profile-heading" className="mt-1 text-2xl font-bold text-slate-900">Structured extracted information</h2><p className="mt-1 text-sm text-slate-500">The backend analysis currently returns raw section text and keyword matches, not the structured resume-extraction.v1 contract. Profile fields remain unavailable from this response.</p></div>
        <p className="mb-4 rounded-xl border border-dashed border-slate-300 bg-white p-5 text-sm text-slate-500">Your candidate profile will appear here when resume processing is connected.</p>
        <div className="grid gap-4 md:grid-cols-2"><ProfileSkills data={null} /><EducationSection data={null} /><ExperienceSection data={null} /><ProjectsSection data={null} /><CertificationsSection data={null} /></div>
      </section>
    </div>
  </main>;
}
