
"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { sampleMetrics } from "../data/sample-data";
import { useCandidateProfile } from "@/components/profile/CandidateProfileProvider";

type UploadStatus = "empty" | "selected" | "processing" | "success" | "error";

const supportedExtensions = ["pdf", "doc", "docx"];
const maxFileSize = 10 * 1024 * 1024;

function formatFileSize(size: number) {
  return size < 1024 * 1024
    ? `${Math.max(1, Math.round(size / 1024))} KB`
    : `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function FileIcon({ className = "h-6 w-6" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      className={className}
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M7 3.75h6l4.25 4.5v11A1.75 1.75 0 0 1 15.5 21h-8A1.75 1.75 0 0 1 5.75 19.25v-13.75A1.75 1.75 0 0 1 7.5 3.75Z"
      />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M13 4v4.5h4.25M8.5 13h7M8.5 16.5h7"
      />
    </svg>
  );
}

function UploadIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      className="h-7 w-7"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 15.5V4m0 0L7.75 8.25M12 4l4.25 4.25M4.5 15v3.25A1.75 1.75 0 0 0 6.25 20h11.5a1.75 1.75 0 0 0 1.75-1.75V15"
      />
    </svg>
  );
}

const extractionReviewItems = [
  {
    title: "Explicit skills",
    detail:
      "Skills directly stated in the resume, kept separate from inferred skills.",
    number: "01",
  },
  {
    title: "Inferred skills",
    detail:
      "Potential skills suggested by titles or context, clearly identified as inferred.",
    number: "02",
  },
  {
    title: "Needs review",
    detail:
      "Ambiguous or rejected fields can be flagged instead of treated as confirmed facts.",
    number: "03",
  },
  {
    title: "Evidence and warnings",
    detail:
      "Relevant evidence and extraction warnings can explain why a field needs attention.",
    number: "04",
  },
];

export default function ResumePage() {
  const inputRef = useRef<HTMLInputElement>(null);
  const { profile, setResumeMetadata, resetResumeMetadata } =
    useCandidateProfile();

  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<UploadStatus>("empty");
  const [errorMessage, setErrorMessage] = useState("");
  const [isDragging, setIsDragging] = useState(false);

  const selectedFileName = file?.name ?? profile.resume.fileName;
  const selectedFileSize = file?.size ?? profile.resume.fileSize;

  const showingSamplePreview =
    status !== "error" &&
    ((status === "success" && file !== null) ||
      (status === "empty" && profile.resume.status === "sample-preview"));

  const showingSharedSelection =
    status === "empty" && profile.resume.status === "selected";

  const showingRetainedSelectionAfterError =
    status === "error" && profile.resume.status !== "empty";

  function selectFile(candidate?: File) {
    if (!candidate) return;

    const extension = candidate.name.split(".").pop()?.toLowerCase() ?? "";

    if (!supportedExtensions.includes(extension)) {
      setStatus("error");
      setErrorMessage(
        "This file type is not supported. Choose a PDF, DOC, or DOCX file.",
      );
      return;
    }

    if (candidate.size > maxFileSize) {
      setStatus("error");
      setErrorMessage(
        "This file is larger than 10 MB. Choose a smaller resume file.",
      );
      return;
    }

    setFile(candidate);

    setResumeMetadata({
      fileName: candidate.name,
      fileSize: candidate.size,
      fileType: candidate.type || extension,
      status: "selected",
    });

    setErrorMessage("");
    setStatus("selected");
  }

  function handleDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    selectFile(event.dataTransfer.files[0]);
  }

  function analyzeResume() {
    if (!file) return;

    const selectedFile = file;
    setStatus("processing");

    window.setTimeout(() => {
      setStatus("success");

      setResumeMetadata({
        fileName: selectedFile.name,
        fileSize: selectedFile.size,
        fileType:
          selectedFile.type ||
          (selectedFile.name.split(".").pop()?.toLowerCase() ?? null),
        status: "sample-preview",
      });
    }, 1400);
  }

  function resetUpload() {
    setFile(null);
    setStatus("empty");
    setErrorMessage("");
    resetResumeMetadata();

    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }

  return (
    <div className="min-h-screen bg-background px-4 pb-6 pt-16 sm:px-6 md:py-8 lg:px-8">
      <div className="mx-auto max-w-[1180px]">
        <header className="mb-7 border-b border-slate-200 pb-6">
          <p className="mb-1 text-sm font-semibold text-primary">
            Resume Analysis
          </p>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-slate-900">
                Upload your resume
              </h1>

              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
                Get a clearer picture of your skills, experience, and next
                career steps.
              </p>
            </div>

            <span className="inline-flex w-fit items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-500">
              <span
                className="h-2 w-2 rounded-full bg-emerald-500"
                aria-hidden="true"
              />
              Private and secure
            </span>
          </div>
        </header>

        <div className="grid gap-5 lg:grid-cols-[minmax(0,1.65fr)_minmax(260px,0.85fr)]">
          <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_6px_18px_rgba(15,23,42,0.04)] sm:p-6">
            <div className="mb-5 flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">
                  Resume file
                </h2>
                <p className="mt-1 text-sm text-slate-500">
                  Upload a recent version to begin.
                </p>
              </div>

              <span className="hidden rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700 sm:inline-flex">
                Prototype · Local demo
              </span>
            </div>

            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              className="hidden"
              aria-label="Choose resume file"
              onChange={(event) => selectFile(event.target.files?.[0])}
            />

            {showingSamplePreview ? (
              <div
                className="rounded-xl border border-emerald-200 bg-emerald-50/60 p-5 sm:p-6"
                role="status"
                aria-live="polite"
              >
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div className="flex items-start gap-3">
                    <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700">
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        className="h-5 w-5"
                        aria-hidden="true"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="m5 12.5 4.5 4.5L19 7.5"
                        />
                      </svg>
                    </span>

                    <div>
                      <p className="font-semibold text-emerald-900">
                        Sample preview ready
                      </p>
                      <p className="mt-1 text-sm text-emerald-800">
                        Illustrative results for{" "}
                        {profile.resume.fileName ??
                          file?.name ??
                          "your selected resume"}
                      </p>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={resetUpload}
                    className="text-left text-sm font-semibold text-indigo-700 hover:text-indigo-900 sm:text-right"
                  >
                    Upload another
                  </button>
                </div>

                <div className="mt-5 grid gap-3 sm:grid-cols-3">
                  {[
                    {
                      label: "Resume score",
                      value: String(sampleMetrics.resumeScore),
                      detail: "sample score out of 100",
                    },
                    {
                      label: "Skills found",
                      value: "18",
                      detail: "across 4 categories",
                    },
                    {
                      label: "Experience",
                      value: "3 yrs",
                      detail: "sample estimate",
                    },
                  ].map((item) => (
                    <div
                      key={item.label}
                      className="rounded-xl border border-emerald-100 bg-white p-4"
                    >
                      <p className="text-xs font-medium text-slate-500">
                        {item.label}
                      </p>
                      <p className="mt-2 text-2xl font-bold text-slate-900">
                        {item.value}
                      </p>
                      <p className="mt-1 text-xs text-slate-500">
                        {item.detail}
                      </p>
                    </div>
                  ))}
                </div>

                <p className="mt-4 text-xs leading-5 text-slate-500">
                  This preview uses illustrative sample values only. Your file
                  stayed in this browser; its contents were not uploaded or
                  analyzed.
                </p>

                <Link
                  href="/skill-gap"
                  className="mt-4 inline-flex min-h-10 items-center justify-center rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white transition hover:bg-primary-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300 focus-visible:ring-offset-2"
                >
                  Explore sample skill gaps{" "}
                  <span className="ml-2" aria-hidden="true">
                    →
                  </span>
                </Link>
              </div>
            ) : (
              <div
                onDragOver={(event) => {
                  event.preventDefault();
                  setIsDragging(true);
                }}
                onDragLeave={(event) => {
                  if (
                    !event.currentTarget.contains(
                      event.relatedTarget as Node | null,
                    )
                  ) {
                    setIsDragging(false);
                  }
                }}
                onDrop={handleDrop}
                className={`rounded-xl border-2 border-dashed px-4 py-9 text-center transition-colors sm:px-8 sm:py-12 ${
                  isDragging
                    ? "border-indigo-500 bg-indigo-50"
                    : status === "error"
                      ? "border-rose-300 bg-rose-50/50"
                      : "border-slate-300 bg-slate-50/70 hover:border-indigo-300 hover:bg-indigo-50/40"
                }`}
              >
                {status === "processing" ? (
                  <div
                    className="mx-auto max-w-sm"
                    role="status"
                    aria-live="polite"
                  >
                    <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-100 text-primary">
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        className="h-7 w-7 animate-spin"
                        aria-hidden="true"
                      >
                        <circle
                          cx="12"
                          cy="12"
                          r="9"
                          stroke="currentColor"
                          strokeOpacity=".2"
                          strokeWidth="3"
                        />
                        <path
                          d="M21 12a9 9 0 0 0-9-9"
                          stroke="currentColor"
                          strokeWidth="3"
                          strokeLinecap="round"
                        />
                      </svg>
                    </div>

                    <h3 className="text-lg font-semibold text-slate-900">
                      Preparing your sample preview
                    </h3>

                    <p className="mt-2 text-sm text-slate-500">
                      This prototype simulates the analysis flow. Your resume
                      contents are not being analyzed.
                    </p>

                    <div className="mx-auto mt-5 h-1.5 max-w-xs overflow-hidden rounded-full bg-indigo-100">
                      <div className="h-full w-2/3 animate-pulse rounded-full bg-indigo-600" />
                    </div>
                  </div>
                ) : (
                  (status === "selected" && file) ||
                  (status === "error" && file) ||
                  showingSharedSelection ||
                  showingRetainedSelectionAfterError
                ) ? (
                  <div className="mx-auto max-w-lg text-left">
                    {status === "error" && (
                      <p
                        role="alert"
                        aria-live="assertive"
                        className="mb-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700"
                      >
                        {errorMessage}{" "}
                        {(file || profile.resume.status !== "empty") &&
                          "Previous valid resume metadata is retained."}
                      </p>
                    )}

                    <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
                      <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-indigo-100 text-indigo-700">
                        <FileIcon />
                      </span>

                      <div className="min-w-0 flex-1">
                        <p className="truncate font-semibold text-slate-900">
                          {selectedFileName ?? "Resume file"}
                        </p>

                        <p className="mt-1 text-sm text-slate-500">
                          {selectedFileSize === null
                            ? "File selected earlier in this session"
                            : formatFileSize(selectedFileSize)}
                          {file
                            ? " · Ready for sample preview"
                            : " · Reselect the file to continue"}
                        </p>
                      </div>

                      <button
                        type="button"
                        onClick={resetUpload}
                        className="text-left text-sm font-medium text-slate-500 hover:text-slate-800"
                      >
                        Remove
                      </button>
                    </div>

                    <div className="mt-6 flex flex-col gap-3 sm:flex-row">
                      {file && (
                        <button
                          type="button"
                          onClick={analyzeResume}
                          className="inline-flex min-h-11 flex-1 items-center justify-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-primary-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300 focus-visible:ring-offset-2"
                        >
                          Preview sample results{" "}
                          <span aria-hidden="true">→</span>
                        </button>
                      )}

                      <button
                        type="button"
                        onClick={() => inputRef.current?.click()}
                        className="min-h-11 rounded-xl border border-slate-200 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                      >
                        {file ? "Choose another file" : "Choose resume again"}
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="mx-auto max-w-md">
                    <div
                      className={`mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl ${
                        status === "error"
                          ? "bg-rose-100 text-rose-700"
                          : "bg-indigo-100 text-indigo-700"
                      }`}
                    >
                      {status === "error" ? (
                        <span className="text-2xl font-semibold" aria-hidden="true">
                          !
                        </span>
                      ) : (
                        <UploadIcon />
                      )}
                    </div>

                    <h3 className="text-lg font-semibold text-slate-900">
                      {status === "error"
                        ? "We couldn't use that file"
                        : "Drop your resume here"}
                    </h3>

                    <p
                      role={status === "error" ? "alert" : undefined}
                      aria-live={status === "error" ? "assertive" : undefined}
                      className={`mt-2 text-sm leading-6 ${
                        status === "error"
                          ? "text-rose-700"
                          : "text-slate-500"
                      }`}
                    >
                      {status === "error"
                        ? errorMessage
                        : "Drag and drop your file, or choose it from your device."}
                    </p>

                    <button
                      type="button"
                      onClick={() => inputRef.current?.click()}
                      className="mt-5 inline-flex min-h-11 items-center justify-center rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-primary-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300 focus-visible:ring-offset-2"
                    >
                      Choose resume
                    </button>

                    <p className="mt-4 text-xs text-slate-400">
                      PDF, DOC, or DOCX · Maximum 10 MB
                    </p>
                  </div>
                )}
              </div>
            )}

            <p className="mt-4 text-xs leading-5 text-slate-400">
              Demo mode: file details stay in your browser; no upload or
              server-side analysis occurs.
            </p>
          </section>

          <aside className="space-y-5">
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_6px_18px_rgba(15,23,42,0.04)]">
              <h2 className="text-base font-semibold text-slate-900">
                What you’ll get
              </h2>

              <div className="mt-4 space-y-4">
                {[
                  {
                    number: "01",
                    title: "Skills snapshot",
                    detail: "See the strengths already in your resume.",
                  },
                  {
                    number: "02",
                    title: "Career alignment",
                    detail: "Understand where your experience fits.",
                  },
                  {
                    number: "03",
                    title: "Next-step guidance",
                    detail: "Get a focused path for continued growth.",
                  },
                ].map((step) => (
                  <div key={step.number} className="flex gap-3">
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-xs font-bold text-indigo-700">
                      {step.number}
                    </span>

                    <div>
                      <p className="text-sm font-semibold text-slate-800">
                        {step.title}
                      </p>
                      <p className="mt-1 text-xs leading-5 text-slate-500">
                        {step.detail}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_6px_18px_rgba(15,23,42,0.04)]">
              <div className="flex items-start gap-3">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-600">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.7"
                    className="h-5 w-5"
                    aria-hidden="true"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M12 3.75 5.5 6.5v5.1c0 4.1 2.8 7.3 6.5 8.65 3.7-1.35 6.5-4.55 6.5-8.65V6.5L12 3.75Z"
                    />
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="m9 12 2 2 4-4"
                    />
                  </svg>
                </span>

                <div>
                  <h2 className="text-sm font-semibold text-slate-900">
                    Your information stays yours
                  </h2>
                  <p className="mt-1 text-xs leading-5 text-slate-500">
                    This preview runs locally in your browser. Real analysis is
                    not connected yet.
                  </p>
                </div>
              </div>
            </section>
          </aside>
        </div>

        <section
          aria-labelledby="extraction-review-heading"
          className="mt-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_6px_18px_rgba(15,23,42,0.04)] sm:p-6"
        >
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-indigo-700">
                Upcoming capability
              </p>

              <h2
                id="extraction-review-heading"
                className="mt-1 text-lg font-semibold text-slate-900"
              >
                Resume extraction review
              </h2>

              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
                Once extraction is connected, you will be able to review the
                information identified in your resume before it informs your
                career profile.
              </p>
            </div>

            <span className="inline-flex w-fit shrink-0 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800">
              Not connected
            </span>
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {extractionReviewItems.map((item) => (
              <article
                key={item.title}
                className="rounded-xl border border-slate-200 bg-slate-50/70 p-4"
              >
                <span className="text-xs font-bold tracking-wider text-indigo-600">
                  {item.number}
                </span>

                <h3 className="mt-2 text-sm font-semibold text-slate-800">
                  {item.title}
                </h3>

                <p className="mt-2 text-xs leading-5 text-slate-500">
                  {item.detail}
                </p>
              </article>
            ))}
          </div>

          <p className="mt-4 rounded-lg bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-500">
            These are planned review capabilities, not results from your
            selected file. No resume content is currently extracted or
            verified.
          </p>
        </section>
      </div>
    </div>
  );
}
