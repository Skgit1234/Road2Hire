"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/AuthProvider";
import { ApiError } from "@/lib/api-client";
import {
  getPipelineLearningRoadmap,
  updatePipelineTaskProgress,
} from "@/lib/pipeline-api";
import type {
  LearningTaskStatus,
  PipelineLearningRoadmapResponse,
  RoadmapItemResponse,
} from "@/lib/pipeline-types";

type PageState = "loading" | "ready" | "empty" | "validation" | "error";

type ProgressDraft = {
  status: LearningTaskStatus;
  progress: string;
};

const statusLabel: Record<LearningTaskStatus, string> = {
  not_started: "Not started",
  in_progress: "In progress",
  completed: "Completed",
};

const statusStyle: Record<LearningTaskStatus, string> = {
  not_started: "border-slate-200 bg-slate-100 text-slate-600",
  in_progress: "border-indigo-200 bg-indigo-50 text-indigo-700",
  completed: "border-emerald-200 bg-emerald-50 text-emerald-700",
};

function isValidationError(message: string) {
  return message.startsWith("The API returned an invalid ") ||
    message.startsWith("Provide both a task status and progress") ||
    message.startsWith("Task progress must be") ||
    message.startsWith("Task status and progress are inconsistent") ||
    message.startsWith("Invalid learning task status");
}

function getProgressDrafts(
  roadmap: PipelineLearningRoadmapResponse,
): Record<number, ProgressDraft> {
  return Object.fromEntries(
    roadmap.phases.flatMap((phase) =>
      phase.items.map((item) => [
        item.task_id,
        {
          status: item.status,
          progress: String(item.progress),
        },
      ]),
    ),
  );
}

function getResourceLabel(resource: Record<string, string>, index: number) {
  return resource.name ??
    resource.category ??
    resource.type ??
    resource.title ??
    `Resource category ${index + 1}`;
}

export default function LearningRoadmapPage() {
  const { session, isRestoring } = useAuth();
  const [state, setState] = useState<PageState>("loading");
  const [roadmap, setRoadmap] =
    useState<PipelineLearningRoadmapResponse | null>(null);
  const [error, setError] = useState("");
  const [validationError, setValidationError] = useState("");
  const [progressDrafts, setProgressDrafts] =
    useState<Record<number, ProgressDraft>>({});
  const [updatingTaskId, setUpdatingTaskId] = useState<number | null>(null);

  useEffect(() => {
    if (!session) return;

    let active = true;

    void Promise.resolve()
      .then(() => {
        if (!active) return undefined;

        setState("loading");
        setRoadmap(null);
        setError("");
        setValidationError("");

        return getPipelineLearningRoadmap(session.accessToken);
      })
      .then((response) => {
        if (!active || !response) return;

        setRoadmap(response);
        setProgressDrafts(getProgressDrafts(response));
        setState("ready");
      })
      .catch((requestError: unknown) => {
        if (!active) return;

        if (requestError instanceof ApiError && requestError.status === 404) {
          setState("empty");
          return;
        }

        const message = requestError instanceof Error
          ? requestError.message
          : "Could not load your learning roadmap.";

        if (isValidationError(message)) {
          setValidationError(message);
          setState("validation");
        } else {
          setError(message);
          setState("error");
        }
      });

    return () => {
      active = false;
    };
  }, [session]);

  async function saveProgress(item: RoadmapItemResponse) {
    setValidationError("");
    setError("");

    const draft = progressDrafts[item.task_id] ?? {
      status: item.status,
      progress: String(item.progress),
    };

    const rawProgress = draft.progress;
    const progress = Number(rawProgress);

    if (
      !rawProgress.trim() ||
      !Number.isInteger(progress) ||
      progress < 0 ||
      progress > 100
    ) {
      setValidationError(
        "Enter a whole-number progress value from 0 to 100.",
      );
      return;
    }

    if (!session || !roadmap || updatingTaskId !== null) return;

    setUpdatingTaskId(item.task_id);

    try {
      await updatePipelineTaskProgress(
        session.accessToken,
        item.task_id,
        {
          status: draft.status,
          progress,
        },
      );

      const refreshed = await getPipelineLearningRoadmap(
        session.accessToken,
        roadmap.pipeline_run_id,
      );

      setRoadmap(refreshed);
      setProgressDrafts(getProgressDrafts(refreshed));
    } catch (requestError) {
      const message = requestError instanceof Error
        ? requestError.message
        : "Could not update task progress.";

      if (isValidationError(message)) {
        setValidationError(message);
      } else {
        setError(message);
      }
    } finally {
      setUpdatingTaskId(null);
    }
  }

  const phases = roadmap?.phases ?? [];
  const items = phases.flatMap((phase) => phase.items);
  const completedCount = items.filter(
    (item) => item.status === "completed",
  ).length;
  const totalProgress = items.length
    ? Math.round(
        items.reduce((sum, item) => sum + item.progress, 0) /
          items.length,
      )
    : 0;

  return (
    <div className="min-h-screen bg-background px-4 pb-8 pt-16 sm:px-6 md:py-8 lg:px-8">
      <div className="mx-auto max-w-[1280px]">
        <header className="mb-6 flex flex-col gap-4 border-b border-slate-200 pb-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="mb-1 text-sm font-semibold text-primary">
              Personalized learning
            </p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-900">
              Learning roadmap
            </h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
              A phased learning plan generated from your unified skill-gap analysis.
            </p>
          </div>
          <span className="inline-flex w-fit items-center gap-2 rounded-full border border-indigo-100 bg-white px-3 py-1.5 text-xs font-medium text-slate-500">
            <span
              className={`h-2 w-2 rounded-full ${
                state === "ready" ? "bg-emerald-500" : "bg-indigo-500"
              }`}
            />
            {state === "ready" ? "Pipeline roadmap" : "Account roadmap"}
          </span>
        </header>

        {isRestoring ? (
          <section
            className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-600"
            role="status"
          >
            Restoring your session…
          </section>
        ) : !session ? (
          <section
            className="rounded-2xl border border-amber-200 bg-white p-6 text-sm text-amber-900"
            role="status"
          >
            Sign in to view and update your learning roadmap.{" "}
            <Link className="font-semibold underline" href="/login">
              Go to sign in
            </Link>
          </section>
        ) : state === "loading" ? (
          <section
            className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-600"
            role="status"
            aria-live="polite"
          >
            Loading your learning roadmap...
          </section>
        ) : state === "empty" ? (
          <section
            className="rounded-2xl border border-slate-200 bg-white p-6 sm:p-8"
            aria-labelledby="no-roadmap-heading"
          >
            <h2
              id="no-roadmap-heading"
              className="text-xl font-semibold text-slate-900"
            >
              No completed analysis found
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
              Complete a skill-gap analysis first. Your personalized learning
              roadmap will be available after the pipeline finishes successfully.
            </p>
            <Link
              href="/skill-gap"
              className="mt-5 inline-flex min-h-11 items-center justify-center rounded-xl bg-primary px-4 py-3 text-sm font-semibold text-white hover:bg-primary-dark"
            >
              Go to skill-gap analysis
            </Link>
          </section>
        ) : state === "error" || state === "validation" ? (
          <section
            className="rounded-2xl border border-rose-200 bg-white p-6 text-sm text-rose-800"
            role="alert"
          >
            <h2 className="font-semibold">
              {state === "validation"
                ? "Roadmap response could not be validated"
                : "Learning roadmap could not be loaded"}
            </h2>
            <p className="mt-2">
              {state === "validation" ? validationError : error}
            </p>
          </section>
        ) : roadmap ? (
          <>
            <section
              className="mb-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
              aria-labelledby="roadmap-progress-heading"
            >
              <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-500">
                    Average task progress
                  </p>
                  <h2
                    id="roadmap-progress-heading"
                    className="mt-1 text-4xl font-bold tracking-tight text-slate-900"
                  >
                    {totalProgress}
                    <span className="text-2xl text-slate-400">%</span>
                  </h2>
                  <p className="mt-2 text-sm text-slate-500">
                    {completedCount} of {items.length} learning items completed
                  </p>
                  {roadmap.target_occupation_title && (
                    <p className="mt-1 text-sm font-medium text-slate-700">
                      Target occupation: {roadmap.target_occupation_title}
                    </p>
                  )}
                  {roadmap.total_estimated_weeks && (
                    <p className="mt-1 text-sm text-slate-500">
                      Estimated duration: {roadmap.total_estimated_weeks}
                    </p>
                  )}
                </div>
                <div className="w-full sm:max-w-md">
                  <div className="mb-2 flex justify-between text-xs font-medium text-slate-500">
                    <span>Average across learning items</span>
                    <span>{totalProgress}%</span>
                  </div>
                  <div
                    className="h-3 overflow-hidden rounded-full bg-slate-100"
                    role="progressbar"
                    aria-label="Average roadmap task progress"
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={totalProgress}
                    aria-valuetext={`${totalProgress}% average progress`}
                  >
                    <div
                      className="h-full rounded-full bg-primary transition-[width]"
                      style={{ width: `${totalProgress}%` }}
                    />
                  </div>
                </div>
              </div>
            </section>

            {validationError && (
              <p
                className="mb-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"
                role="alert"
              >
                {validationError}
              </p>
            )}
            {error && (
              <p
                className="mb-4 rounded-xl border border-rose-200 bg-white p-3 text-sm text-rose-800"
                role="alert"
              >
                {error}
              </p>
            )}

            <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1.55fr)_minmax(280px,0.8fr)]">
              <section
                className="min-w-0"
                aria-labelledby="learning-path-heading"
              >
                <div className="mb-4">
                  <h2
                    id="learning-path-heading"
                    className="text-lg font-semibold text-slate-900"
                  >
                    Your learning path
                  </h2>
                  <p className="mt-1 text-sm text-slate-500">
                    {roadmap.total_roadmap_skills ?? items.length} learning
                    items across {phases.length} phases.
                  </p>
                </div>

                {phases.length === 0 ? (
                  <p className="rounded-xl border border-dashed border-slate-300 bg-white px-4 py-8 text-center text-sm text-slate-600">
                    The backend returned no learning phases for this analysis.
                  </p>
                ) : (
                  <ol className="space-y-5">
                    {phases.map((phase) => (
                      <li
                        key={phase.phase_number}
                        className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5"
                      >
                        <div className="mb-4 border-b border-slate-100 pb-4">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <h3 className="font-semibold text-slate-900">
                              Phase {phase.phase_number}: {phase.phase_name}
                            </h3>
                            <span className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700">
                              {phase.estimated_weeks}
                            </span>
                          </div>
                          <p className="mt-2 text-sm leading-6 text-slate-600">
                            {phase.description}
                          </p>
                          <p className="mt-2 text-xs text-slate-500">
                            {phase.items.length} learning items
                          </p>
                        </div>

                        {phase.items.length === 0 ? (
                          <p className="text-sm text-slate-500">
                            No learning items are available in this phase.
                          </p>
                        ) : (
                          <ol className="space-y-4">
                            {phase.items.map((item) => {
                              const draft = progressDrafts[item.task_id] ?? {
                                status: item.status,
                                progress: String(item.progress),
                              };

                              return (
                                <li
                                  key={item.logical_item_key}
                                  className="rounded-xl border border-slate-200 p-4"
                                >
                                  <div className="flex flex-wrap items-start justify-between gap-3">
                                    <div className="min-w-0">
                                      <h4 className="font-semibold text-slate-900">
                                        {item.skill_name}
                                      </h4>
                                      <p className="mt-1 text-xs text-slate-500">
                                        Task ID {item.task_id}
                                        {item.priority
                                          ? ` · Priority: ${item.priority}`
                                          : ""}
                                      </p>
                                    </div>
                                    <span
                                      className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${statusStyle[item.status]}`}
                                    >
                                      {statusLabel[item.status]}
                                    </span>
                                  </div>

                                  {item.importance_rationale && (
                                    <p className="mt-3 text-sm leading-6 text-slate-600">
                                      {item.importance_rationale}
                                    </p>
                                  )}

                                  {item.learning_outcome && (
                                    <p className="mt-3 text-sm leading-6 text-slate-700">
                                      <span className="font-semibold">
                                        Learning outcome:{" "}
                                      </span>
                                      {item.learning_outcome}
                                    </p>
                                  )}

                                  <div className="mt-4 flex items-center gap-3">
                                    <div className="min-w-0 flex-1">
                                      <div
                                        className="h-2 overflow-hidden rounded-full bg-slate-100"
                                        role="progressbar"
                                        aria-label={`${item.skill_name} task progress`}
                                        aria-valuemin={0}
                                        aria-valuemax={100}
                                        aria-valuenow={item.progress}
                                        aria-valuetext={`${item.progress}% complete`}
                                      >
                                        <div
                                          className={`h-full rounded-full ${
                                            item.status === "completed"
                                              ? "bg-emerald-500"
                                              : "bg-indigo-600"
                                          }`}
                                          style={{
                                            width: `${item.progress}%`,
                                          }}
                                        />
                                      </div>
                                    </div>
                                    <span className="w-10 text-right text-xs tabular-nums text-slate-600">
                                      {item.progress}%
                                    </span>
                                  </div>

                                  <div className="mt-4 flex flex-wrap items-end gap-3">
                                    <label className="text-xs font-medium text-slate-600">
                                      Status
                                      <select
                                        aria-label={`Status for ${item.skill_name}`}
                                        value={draft.status}
                                        onChange={(event) =>
                                          setProgressDrafts((current) => ({
                                            ...current,
                                            [item.task_id]: {
                                              ...draft,
                                              status: event.target.value as LearningTaskStatus,
                                            },
                                          }))
                                        }
                                        className="mt-1 block h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm"
                                      >
                                        <option value="not_started">
                                          Not started
                                        </option>
                                        <option value="in_progress">
                                          In progress
                                        </option>
                                        <option value="completed">
                                          Completed
                                        </option>
                                      </select>
                                    </label>

                                    <label className="text-xs font-medium text-slate-600">
                                      Progress (%)
                                      <input
                                        aria-label={`Progress for ${item.skill_name}`}
                                        type="number"
                                        min={0}
                                        max={100}
                                        step={1}
                                        value={draft.progress}
                                        onChange={(event) =>
                                          setProgressDrafts((current) => ({
                                            ...current,
                                            [item.task_id]: {
                                              ...draft,
                                              progress: event.target.value,
                                            },
                                          }))
                                        }
                                        className="mt-1 block h-10 w-28 rounded-lg border border-slate-300 px-3 text-sm"
                                      />
                                    </label>

                                    <button
                                      type="button"
                                      disabled={updatingTaskId !== null}
                                      onClick={() => void saveProgress(item)}
                                      className="min-h-10 rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-white hover:bg-primary-dark disabled:cursor-wait disabled:opacity-60"
                                    >
                                      {updatingTaskId === item.task_id
                                        ? "Saving..."
                                        : "Save progress"}
                                    </button>
                                  </div>

                                  {item.prerequisites.length > 0 && (
                                    <div className="mt-4">
                                      <h5 className="text-xs font-semibold text-slate-700">
                                        Prerequisites
                                      </h5>
                                      <ul className="mt-2 flex flex-wrap gap-2">
                                        {item.prerequisites.map(
                                          (prerequisite) => (
                                            <li
                                              key={prerequisite}
                                              className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600"
                                            >
                                              {prerequisite}
                                            </li>
                                          ),
                                        )}
                                      </ul>
                                    </div>
                                  )}

                                  {item.suggested_activities.length > 0 && (
                                    <div className="mt-4">
                                      <h5 className="text-xs font-semibold text-slate-700">
                                        Suggested activities
                                      </h5>
                                      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-600">
                                        {item.suggested_activities.map(
                                          (activity) => (
                                            <li key={activity}>{activity}</li>
                                          ),
                                        )}
                                      </ul>
                                    </div>
                                  )}

                                  {item.practical_project && (
                                    <div className="mt-4 rounded-lg bg-indigo-50 p-3">
                                      <h5 className="text-xs font-semibold text-indigo-900">
                                        Practical project
                                      </h5>
                                      <p className="mt-1 text-sm leading-6 text-indigo-800">
                                        {item.practical_project}
                                      </p>
                                    </div>
                                  )}

                                  {item.completion_criteria && (
                                    <p className="mt-4 text-sm leading-6 text-slate-600">
                                      <span className="font-semibold text-slate-700">
                                        Completion criteria:{" "}
                                      </span>
                                      {item.completion_criteria}
                                    </p>
                                  )}

                                  {item.estimated_duration_weeks && (
                                    <p className="mt-3 text-xs text-slate-500">
                                      Estimated duration:{" "}
                                      {item.estimated_duration_weeks}
                                    </p>
                                  )}

                                  {item.resource_categories.length > 0 && (
                                    <div className="mt-4 border-t border-slate-100 pt-4">
                                      <h5 className="text-sm font-semibold text-slate-800">
                                        Resource categories
                                      </h5>
                                      <ul className="mt-2 space-y-2">
                                        {item.resource_categories.map(
                                          (resource, index) => (
                                            <li
                                              key={`${item.logical_item_key}-resource-${index}`}
                                              className="rounded-lg bg-slate-50 p-3 text-sm"
                                            >
                                              <p className="font-medium text-slate-800">
                                                {getResourceLabel(resource, index)}
                                              </p>
                                              <dl className="mt-2 space-y-1">
                                                {Object.entries(resource)
                                                  .filter(
                                                    ([key, value]) =>
                                                      key !== "name" &&
                                                      key !== "category" &&
                                                      key !== "type" &&
                                                      key !== "title" &&
                                                      Boolean(value),
                                                  )
                                                  .map(([key, value]) => (
                                                    <div
                                                      key={key}
                                                      className="flex flex-wrap gap-1 text-xs text-slate-600"
                                                    >
                                                      <dt className="font-medium">
                                                        {key.replaceAll("_", " ")}:
                                                      </dt>
                                                      <dd>{value}</dd>
                                                    </div>
                                                  ))}
                                              </dl>
                                            </li>
                                          ),
                                        )}
                                      </ul>
                                    </div>
                                  )}
                                </li>
                              );
                            })}
                          </ol>
                        )}
                      </li>
                    ))}
                  </ol>
                )}
              </section>

              <aside className="space-y-5">
                <section
                  className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
                  aria-labelledby="roadmap-summary-heading"
                >
                  <h2
                    id="roadmap-summary-heading"
                    className="text-base font-semibold text-slate-900"
                  >
                    Roadmap summary
                  </h2>
                  <dl className="mt-4 space-y-3 text-sm">
                    <div className="flex justify-between gap-3">
                      <dt className="text-slate-500">Pipeline run</dt>
                      <dd className="font-medium text-slate-800">
                        #{roadmap.pipeline_run_id}
                      </dd>
                    </div>
                    <div className="flex justify-between gap-3">
                      <dt className="text-slate-500">Learning phases</dt>
                      <dd className="font-medium text-slate-800">
                        {phases.length}
                      </dd>
                    </div>
                    <div className="flex justify-between gap-3">
                      <dt className="text-slate-500">Learning items</dt>
                      <dd className="font-medium text-slate-800">
                        {items.length}
                      </dd>
                    </div>
                    <div className="flex justify-between gap-3">
                      <dt className="text-slate-500">Completed</dt>
                      <dd className="font-medium text-slate-800">
                        {completedCount}
                      </dd>
                    </div>
                  </dl>
                </section>

                <section
                  className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
                  aria-labelledby="status-key-heading"
                >
                  <h2
                    id="status-key-heading"
                    className="text-base font-semibold text-slate-900"
                  >
                    Task status
                  </h2>
                  <ul className="mt-4 space-y-3 text-sm">
                    {(Object.keys(statusLabel) as LearningTaskStatus[]).map(
                      (status) => (
                        <li
                          key={status}
                          className="flex items-center justify-between gap-3"
                        >
                          <span className="text-slate-600">
                            {statusLabel[status]}
                          </span>
                          <span
                            className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${statusStyle[status]}`}
                          >
                            {status}
                          </span>
                        </li>
                      ),
                    )}
                  </ul>
                </section>

                {roadmap.disclaimers.length > 0 && (
                  <section
                    className="rounded-2xl border border-amber-200 bg-amber-50 p-5"
                    aria-labelledby="roadmap-notes-heading"
                  >
                    <h2
                      id="roadmap-notes-heading"
                      className="text-base font-semibold text-amber-900"
                    >
                      Roadmap notes
                    </h2>
                    <ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-6 text-amber-900">
                      {roadmap.disclaimers.map((disclaimer, index) => (
                        <li key={`${index}-${disclaimer}`}>{disclaimer}</li>
                      ))}
                    </ul>
                  </section>
                )}

                <Link
                  href="/career-readiness"
                  className="inline-flex min-h-11 w-full items-center justify-center rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                >
                  View career readiness
                </Link>
                <Link
                  href="/skill-gap"
                  className="inline-flex min-h-11 w-full items-center justify-center rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                >
                  View skill-gap analysis
                </Link>
              </aside>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}
