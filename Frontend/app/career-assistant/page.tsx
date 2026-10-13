
"use client";

import { useState, type FormEvent } from "react";
import { useCandidateProfile, type CandidateProfile } from "@/components/profile/CandidateProfileProvider";
import { getRoadmapPhases } from "@/components/profile/candidate-profile-state";

type ChatMessage = {
  id: number;
  role: "assistant" | "user";
  text: string;
  isDemo?: boolean;
};

const suggestions = [
  "How can I improve my resume?",
  "Which skill gap should I focus on first?",
  "Give me a technical interview practice plan",
  "Help me structure a learning plan",
];

function getDemoResponse(message: string, profile: CandidateProfile) {
  const lower = message.toLowerCase();
  if (lower.includes("resume")) {
    return `For a ${profile.targetRole} application, consider leading with a focused summary and describing project impact. This is general demo guidance; the selected resume contents have not been parsed or analyzed.`;
  }
  if (lower.includes("skill") || lower.includes("gap")) {
    const sampleGap = profile.skills
      .filter((skill) => skill.current < skill.target)
      .sort((left, right) => (right.target - right.current) - (left.target - left.current))[0];
    return sampleGap
      ? `The shared sample profile suggests practicing ${sampleGap.name} next (${sampleGap.current}/100 current, ${sampleGap.target}/100 target). These are demo values, not results extracted from your resume.`
      : "Choose one skill and set a small weekly practice goal. This is a demonstration suggestion, not a live skill assessment.";
  }
  if (lower.includes("interview") || lower.includes("practice")) {
    return `The sample profile's interview readiness is ${profile.readiness.interview}/100. For practice, try one technical problem, explain your decisions aloud, then review what to improve. This is a demonstration plan, not an assessment.`;
  }
  if (lower.includes("learn") || lower.includes("plan")) {
    const nextItem = getRoadmapPhases(profile.roadmap).flatMap((phase) => phase.items).find((item) => item.status === "In progress" || item.status === "Upcoming");
    return `For your ${profile.targetRole} goal, work through one topic, apply it in a small project, and explain what you built.${nextItem ? ` The sample roadmap's next item is ${nextItem.title}.` : ""} This is illustrative guidance, not a generated AI plan.`;
  }
  return `Start by choosing one area related to your ${profile.targetRole} goal and setting a small weekly practice target. This is a demonstration response, not live AI guidance.`;
}

function AssistantMark({ small = false }: { small?: boolean }) {
  return (
    <span className={`flex shrink-0 items-center justify-center rounded-xl bg-indigo-100 font-bold text-indigo-700 ${small ? "h-8 w-8 text-xs" : "h-10 w-10 text-sm"}`} aria-hidden="true">
      R
    </span>
  );
}

export default function CareerAssistantPage() {
  const { profile } = useCandidateProfile();
  const [messages, setMessages] = useState<ChatMessage[]>(() => [
    {
      id: 1,
      role: "assistant",
      text: `Welcome. I can help you think through your resume, skill gaps, interviews, or learning plan for your ${profile.targetRole} goal. This prototype uses shared sample profile data only.`,
    },
  ]);
  const [draft, setDraft] = useState("");
  const [announcement, setAnnouncement] = useState("");
  const [nextId, setNextId] = useState(2);

  function sendMessage(value: string) {
    const text = value.trim();
    if (!text) {
      setAnnouncement("Enter a question before sending.");
      return;
    }

    setMessages((current) => [
      ...current,
      { id: nextId, role: "user", text },
      { id: nextId + 1, role: "assistant", text: getDemoResponse(text, profile), isDemo: true },
    ]);
    setNextId((current) => current + 2);
    setDraft("");
    setAnnouncement("Message sent. A demonstration response was added.");
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    sendMessage(draft);
  }

  return (
    <div className="min-h-screen bg-background px-4 pb-8 pt-16 sm:px-6 md:py-8 lg:px-8">
      <div className="mx-auto max-w-[1100px]">
        <header className="mb-6 flex flex-col gap-4 border-b border-slate-200 pb-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="mb-1 text-sm font-semibold text-primary">Career support</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-900">Career assistant</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
              Explore practical ideas for your resume, skills, interviews, and learning goals.
            </p>
          </div>
          <span className="inline-flex w-fit items-center gap-2 rounded-full border border-amber-200 bg-white px-3 py-1.5 text-xs font-medium text-amber-800">
            <span className="h-2 w-2 rounded-full bg-amber-500" />
            Demonstration mode
          </span>
        </header>

        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_1px_2px_rgba(15,23,42,0.04),0_6px_18px_rgba(15,23,42,0.04)]" aria-labelledby="chat-heading">
          <div className="flex items-center justify-between gap-4 border-b border-slate-200 px-4 py-4 sm:px-6">
            <div className="flex min-w-0 items-center gap-3">
              <AssistantMark />
              <div className="min-w-0">
                <h2 id="chat-heading" className="truncate font-semibold text-slate-900">Road2Hire career guide</h2>
                <p className="text-xs text-slate-500">Local interactive demo</p>
              </div>
            </div>
            <span className="hidden rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700 sm:inline-flex">Ready</span>
          </div>

          <div className="max-h-[min(56vh,620px)] min-h-[320px] space-y-5 overflow-y-auto bg-slate-50/70 p-4 sm:p-6" aria-label="Conversation" aria-live="polite" aria-relevant="additions text">
            {messages.map((message) => (
              <article key={message.id} className={`flex min-w-0 gap-3 ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                {message.role === "assistant" && <AssistantMark small />}
                <div className={`min-w-0 max-w-[min(90%,650px)] rounded-2xl px-4 py-3 ${message.role === "user" ? "rounded-br-md bg-primary text-white" : "rounded-tl-md border border-slate-200 bg-white text-slate-700 shadow-sm"}`}>
                  {message.isDemo && <p className="mb-1 text-[10px] font-semibold uppercase tracking-[0.1em] text-indigo-600">Demo response</p>}
                  <p className="break-words text-sm leading-6">{message.text}</p>
                </div>
                {message.role === "user" && (
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-slate-200 text-xs font-bold text-slate-700" aria-label="You">You</span>
                )}
              </article>
            ))}
          </div>

          <div className="border-t border-slate-200 p-4 sm:p-6">
            <p className="mb-3 text-sm font-semibold text-slate-800">Try a prompt</p>
            <div className="flex flex-wrap gap-2">
              {suggestions.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => sendMessage(suggestion)}
                  className="max-w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-left text-xs leading-5 text-slate-600 transition hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300"
                >
                  {suggestion}
                </button>
              ))}
            </div>

            <form onSubmit={handleSubmit} className="mt-5">
              <label htmlFor="career-question" className="mb-2 block text-sm font-semibold text-slate-800">Your message</label>
              <div className="flex flex-col gap-2 sm:flex-row">
                <input
                  id="career-question"
                  type="text"
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  placeholder="Ask about your career goals..."
                  autoComplete="off"
                  className="min-h-11 min-w-0 flex-1 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
                />
                <button
                  type="submit"
                  className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-white transition hover:bg-primary-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300 focus-visible:ring-offset-2"
                >
                  Send <span aria-hidden="true">→</span>
                </button>
              </div>
              <p className="mt-2 min-h-5 text-xs text-slate-500" aria-live="polite">{announcement || "Press Enter or select Send to add your message."}</p>
            </form>
          </div>
        </section>

        <p className="mt-4 rounded-xl border border-slate-200 bg-white px-4 py-3 text-xs leading-5 text-slate-500">
          Mock assistant for demonstration only. Responses are predefined examples generated locally in your browser; no real AI service or career profile is connected.
        </p>
      </div>
    </div>
  );
}
