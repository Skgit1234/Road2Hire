"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useAuth } from "@/components/auth/AuthProvider";
import {
  createJob,
  listJobs,
  listResumes,
  matchResumeToJob,
  type JobCreateRequest,
  type JobMatchingResponse,
  type JobRecord,
  type ResumeRecord,
} from "@/lib/api-client";

type LoadState = "loading" | "ready" | "error";
type SkillDraft = { skill_name: string; importance: "essential" | "optional" };

function formatScore(score: number | null) {
  return score === null ? "Not applicable" : `${Math.round(score * 100)}%`;
}

function MatchResult({ result }: { result: JobMatchingResponse }) {
  const matching = result.job_specific_matching;
  return (
    <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6" aria-labelledby="job-match-result-heading" aria-live="polite">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-primary">Analysis result</p>
          <h2 id="job-match-result-heading" className="mt-1 text-xl font-bold text-slate-900">{result.job.title}</h2>
          <p className="mt-1 text-sm text-slate-500">Pipeline run #{result.run.id}</p>
        </div>
        <span className={`rounded-full px-3 py-1 text-sm font-semibold ${result.run.status === "completed" ? "bg-emerald-50 text-emerald-800" : result.run.status === "failed" ? "bg-rose-50 text-rose-800" : "bg-amber-50 text-amber-800"}`}>
          Pipeline {result.run.status}
        </span>
      </div>

      <p className="mt-4 rounded-xl bg-slate-50 p-4 text-sm leading-6 text-slate-700">{result.matching_basis}</p>

      {result.run.status === "failed" && (
        <div role="alert" className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          <p className="font-semibold">The pipeline could not complete this matching run.</p>
          {result.run.error_message && <p className="mt-1">{result.run.error_message}</p>}
        </div>
      )}

      {matching && matching.status === "no_requirements" && (
        <p role="status" className="mt-4 rounded-xl border border-slate-200 p-4 text-sm text-slate-600">This job has no saved skill requirements to compare.</p>
      )}

      {matching?.status === "completed" && (
        <>
          <div className="mt-5 grid gap-3 sm:grid-cols-3" aria-label="Job-specific coverage scores">
            {([ ["Overall coverage", matching.scores.overall], ["Essential coverage", matching.scores.essential], ["Optional coverage", matching.scores.optional] ] as const).map(([label, score]) => (
              <div key={label} className="rounded-xl border border-slate-200 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
                <p className="mt-2 text-2xl font-bold text-slate-900">{formatScore(score)}</p>
              </div>
            ))}
          </div>

          <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950">
            <p>Candidate skills come from resume extraction and are unverified. Matching thresholds are provisional. Only confirmed matches count toward coverage; uncertain and related evidence is shown separately.</p>
          </div>

          {matching.requirements.length === 0 ? (
            <p role="status" className="mt-5 text-sm text-slate-600">There are no requirements to display.</p>
          ) : (
            <div className="mt-5 space-y-3">
              <h3 className="text-lg font-semibold text-slate-900">Requirement evidence</h3>
              {matching.requirements.map((requirement, index) => (
                <article key={`${index}-${requirement.name}`} className="rounded-xl border border-slate-200 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h4 className="font-semibold text-slate-900">{requirement.name}</h4>
                    <div className="flex flex-wrap gap-2">
                      <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium capitalize text-slate-700">{requirement.importance}</span>
                      <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${requirement.match_status === "confirmed_match" ? "bg-emerald-100 text-emerald-800" : requirement.match_status === "related_skill" || requirement.match_status === "uncertain_match" ? "bg-amber-100 text-amber-900" : "bg-slate-100 text-slate-700"}`}>
                        {requirement.match_status.replaceAll("_", " ")}
                      </span>
                    </div>
                  </div>
                  <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
                    <div><dt className="font-medium text-slate-500">Candidate skill</dt><dd className="mt-0.5 text-slate-800">{requirement.candidate_skill ?? "No candidate evidence"}</dd></div>
                    <div><dt className="font-medium text-slate-500">Similarity</dt><dd className="mt-0.5 text-slate-800">{requirement.similarity_score === null ? "Not available" : `${(requirement.similarity_score * 100).toFixed(1)}%`}</dd></div>
                  </dl>
                  {requirement.evidence && <p className="mt-3 text-sm leading-6 text-slate-600"><span className="font-medium text-slate-700">Evidence: </span>{requirement.evidence}</p>}
                  {requirement.related_evidence.length > 0 && (
                    <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3">
                      <h5 className="text-sm font-semibold text-amber-950">Related skills (not confirmed matches)</h5>
                      <ul className="mt-2 space-y-2 text-sm text-amber-950">
                        {requirement.related_evidence.map((evidence, relatedIndex) => (
                          <li key={`${evidence.candidate_skill}-${relatedIndex}`}>
                            <span className="font-medium">{evidence.candidate_skill}</span> · {(evidence.similarity_score * 100).toFixed(1)}% similarity · {evidence.relation}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </article>
              ))}
            </div>
          )}
        </>
      )}

      {!matching && result.run.status !== "failed" && (
        <p role="status" className="mt-4 text-sm text-slate-600">Job-specific requirement matching was not applied for this pipeline run.</p>
      )}
    </section>
  );
}

export default function JobsPage() {
  const { session, isRestoring } = useAuth();
  const matchLock = useRef(false);
  const [jobs, setJobs] = useState<JobRecord[]>([]);
  const [resumes, setResumes] = useState<ResumeRecord[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [loadError, setLoadError] = useState("");
  const [jobId, setJobId] = useState("");
  const [resumeId, setResumeId] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [occupation, setOccupation] = useState("");
  const [skills, setSkills] = useState<SkillDraft[]>([{ skill_name: "", importance: "essential" }]);
  const [createError, setCreateError] = useState("");
  const [createMessage, setCreateMessage] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [matchError, setMatchError] = useState("");
  const [isMatching, setIsMatching] = useState(false);
  const [matchResult, setMatchResult] = useState<JobMatchingResponse | null>(null);

  useEffect(() => {
    if (isRestoring) return;
    if (!session) return;
    let active = true;
    void Promise.resolve()
      .then(() => {
        if (!active) return undefined;
        setLoadState("loading");
        setLoadError("");
        return Promise.all([listJobs(session.accessToken), listResumes(session.accessToken)]);
      })
      .then((loaded) => {
        if (!loaded) return;
        const [savedJobs, savedResumes] = loaded;
        if (!active) return;
        setJobs(savedJobs);
        setResumes(savedResumes);
        setJobId((current) => current || (savedJobs[0] ? String(savedJobs[0].id) : ""));
        setResumeId((current) => current || (savedResumes[0] ? String(savedResumes[0].id) : ""));
        setLoadState("ready");
      })
      .catch((error: unknown) => {
        if (!active) return;
        setLoadError(error instanceof Error ? error.message : "Could not load jobs and resumes.");
        setLoadState("error");
      });
    return () => { active = false; };
  }, [session, isRestoring]);

  async function submitJob(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session || isCreating) return;
    setIsCreating(true);
    setCreateError("");
    setCreateMessage("");
    try {
      const requiredSkills = skills.filter((skill) => skill.skill_name.trim()).map((skill) => ({
        skill_name: skill.skill_name.trim(),
        importance: skill.importance,
      }));
      const details: JobCreateRequest = {
        title: title.trim(),
        description: description.trim(),
        target_occupation: occupation.trim(),
        required_skills: requiredSkills,
      };
      const created = await createJob(details, session.accessToken);
      setJobs((current) => [created, ...current]);
      setJobId(String(created.id));
      setTitle("");
      setDescription("");
      setOccupation("");
      setSkills([{ skill_name: "", importance: "essential" }]);
      setCreateMessage(`Saved ${created.title}.`);
    } catch (error) {
      setCreateError(error instanceof Error ? error.message : "Could not save this job.");
    } finally {
      setIsCreating(false);
    }
  }

  async function submitMatch() {
    if (!session || !jobId || !resumeId || matchLock.current) return;
    matchLock.current = true;
    setIsMatching(true);
    setMatchError("");
    setMatchResult(null);
    try {
      setMatchResult(await matchResumeToJob(Number(jobId), Number(resumeId), session.accessToken));
    } catch (error) {
      setMatchError(error instanceof Error ? error.message : "Could not match this resume to the selected job.");
    } finally {
      matchLock.current = false;
      setIsMatching(false);
    }
  }

  return (
    <main className="min-h-screen bg-background px-4 pb-8 pt-16 sm:px-6 md:py-8 lg:px-8">
      <div className="mx-auto max-w-5xl">
        <header className="mb-6 border-b border-slate-200 pb-6">
          <p className="text-sm font-semibold text-primary">Job-specific comparison</p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-900">Jobs</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">Save a job and compare its requirements with skills extracted by the Road2Hire pipeline.</p>
        </header>

        {isRestoring ? (
          <section role="status" className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-600">Restoring your session…</section>
        ) : !session ? (
          <section role="status" className="rounded-2xl border border-amber-200 bg-white p-6 text-sm text-amber-900">Sign in to save jobs and run matching. <Link className="font-semibold underline" href="/login">Go to sign in</Link></section>
        ) : loadState === "loading" ? (
          <section role="status" className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-600">Loading your saved jobs and resumes…</section>
        ) : loadState === "error" ? (
          <section role="alert" className="rounded-2xl border border-rose-200 bg-white p-6 text-sm text-rose-800"><h2 className="font-semibold">Jobs could not be loaded</h2><p className="mt-2">{loadError}</p></section>
        ) : (
          <>
            <section className="grid gap-6 lg:grid-cols-2">
              <form onSubmit={submitJob} className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
                <div><h2 className="text-xl font-bold text-slate-900">Save a job</h2><p className="mt-1 text-sm text-slate-500">Add the role and the skills to compare.</p></div>
                <label className="block text-sm font-medium text-slate-700">Job title<input required maxLength={255} value={title} onChange={(event) => setTitle(event.target.value)} className="mt-1 min-h-11 w-full rounded-lg border border-slate-300 px-3" /></label>
                <label className="block text-sm font-medium text-slate-700">Description<textarea required value={description} onChange={(event) => setDescription(event.target.value)} rows={3} className="mt-1 w-full rounded-lg border border-slate-300 p-3" /></label>
                <label className="block text-sm font-medium text-slate-700">Target occupation<input required maxLength={512} value={occupation} onChange={(event) => setOccupation(event.target.value)} className="mt-1 min-h-11 w-full rounded-lg border border-slate-300 px-3" /></label>
                <fieldset className="space-y-3">
                  <legend className="text-sm font-semibold text-slate-800">Required skills</legend>
                  {skills.map((skill, index) => (
                    <div key={index} className="grid gap-2 sm:grid-cols-[1fr_10rem_auto]">
                      <label className="sr-only" htmlFor={`job-skill-${index}`}>Skill {index + 1}</label>
                      <input id={`job-skill-${index}`} value={skill.skill_name} onChange={(event) => setSkills((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, skill_name: event.target.value } : item))} placeholder="e.g. Python" className="min-h-11 rounded-lg border border-slate-300 px-3 text-sm" />
                      <label className="sr-only" htmlFor={`job-importance-${index}`}>Importance for skill {index + 1}</label>
                      <select id={`job-importance-${index}`} value={skill.importance} onChange={(event) => setSkills((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, importance: event.target.value as SkillDraft["importance"] } : item))} className="min-h-11 rounded-lg border border-slate-300 px-3 text-sm"><option value="essential">Essential</option><option value="optional">Optional</option></select>
                      <button type="button" onClick={() => setSkills((current) => current.length === 1 ? current : current.filter((_, itemIndex) => itemIndex !== index))} aria-label={`Remove skill ${index + 1}`} disabled={skills.length === 1} className="min-h-11 rounded-lg border border-slate-300 px-3 text-sm text-slate-600 disabled:opacity-40">Remove</button>
                    </div>
                  ))}
                  <button type="button" onClick={() => setSkills((current) => [...current, { skill_name: "", importance: "essential" }])} className="text-sm font-semibold text-indigo-700 underline">Add a skill</button>
                </fieldset>
                {createError && <p role="alert" className="text-sm text-rose-800">{createError}</p>}
                {createMessage && <p role="status" className="text-sm text-emerald-800">{createMessage}</p>}
                <button type="submit" disabled={isCreating} className="min-h-11 w-full rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white disabled:cursor-wait disabled:opacity-60">{isCreating ? "Saving job…" : "Save job"}</button>
              </form>

              <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6" aria-labelledby="run-job-match-heading">
                <div><h2 id="run-job-match-heading" className="text-xl font-bold text-slate-900">Match a resume to a job</h2><p className="mt-1 text-sm text-slate-500">Matching runs only when you choose the button below.</p></div>
                {jobs.length === 0 ? (
                  <p role="status" className="rounded-xl bg-slate-50 p-4 text-sm text-slate-600">You have no saved jobs yet. Add a job to start matching.</p>
                ) : (
                  <label className="block text-sm font-medium text-slate-700">Saved job<select value={jobId} onChange={(event) => { setJobId(event.target.value); setMatchResult(null); }} className="mt-1 min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3"><option value="">Choose a job</option>{jobs.map((job) => <option key={job.id} value={job.id}>{job.title}</option>)}</select></label>
                )}
                {resumes.length === 0 ? (
                  <p role="status" className="rounded-xl bg-slate-50 p-4 text-sm text-slate-600">Upload a resume before matching. <Link className="font-semibold underline" href="/resume">Go to Resume</Link></p>
                ) : (
                  <label className="block text-sm font-medium text-slate-700">Saved resume<select value={resumeId} onChange={(event) => { setResumeId(event.target.value); setMatchResult(null); }} className="mt-1 min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3"><option value="">Choose a resume</option>{resumes.map((resume) => <option key={resume.id} value={resume.id}>{resume.original_name}</option>)}</select></label>
                )}
                {jobs.length > 0 && resumes.length > 0 && <button type="button" onClick={() => void submitMatch()} disabled={!jobId || !resumeId || isMatching} className="min-h-11 w-full rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white disabled:cursor-wait disabled:opacity-60">{isMatching ? "Matching resume…" : "Run job matching"}</button>}
                {isMatching && <p role="status" className="text-sm text-slate-600">Running the pipeline and comparing extracted skills…</p>}
                {matchError && <p role="alert" className="text-sm text-rose-800">{matchError}</p>}
              </section>
            </section>

            {jobs.length > 0 && <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm" aria-labelledby="saved-jobs-heading"><h2 id="saved-jobs-heading" className="text-lg font-semibold text-slate-900">Saved jobs</h2><ul className="mt-3 divide-y divide-slate-100">{jobs.map((job) => <li key={job.id} className="py-3"><p className="font-medium text-slate-800">{job.title}</p><p className="mt-1 text-sm text-slate-500">{job.target_occupation} · {job.required_skills.length} required skills</p></li>)}</ul></section>}
            {matchResult && <MatchResult result={matchResult} />}
          </>
        )}
      </div>
    </main>
  );
}
