
"use client";

import Link from "next/link";
import { useCandidateProfile } from "@/components/profile/CandidateProfileProvider";
import { calculateRoadmapProgress, getRoadmapPhases } from "@/components/profile/candidate-profile-state";
import { sampleMetrics, sampleSkills } from "./data/sample-data";

const statCards = [
  {
    title: "Resume Score",
    value: String(sampleMetrics.resumeScore),
    delta: "/ 100",
    trend: "Great! Keep improving",
    progress: sampleMetrics.resumeScore,
    accent: "bg-emerald-500",
    track: "bg-emerald-100",
    icon: "✦",
    iconTone: "bg-emerald-100 text-emerald-600",
  },
  {
    title: "Career Readiness",
    value: String(sampleMetrics.careerReadiness),
    delta: "%",
    trend: "Almost there!",
    progress: sampleMetrics.careerReadiness,
    accent: "bg-emerald-500",
    track: "bg-emerald-100",
    icon: "↗",
    iconTone: "bg-emerald-100 text-emerald-600",
  },
  {
    title: "Skills Match",
    value: "68",
    delta: "%",
    trend: "Good match",
    progress: 68,
    accent: "bg-blue-500",
    track: "bg-blue-100",
    icon: "◎",
    iconTone: "bg-blue-100 text-blue-600",
  },
  {
    title: "Interview Readiness",
    value: String(sampleMetrics.interviewReadiness),
    delta: "%",
    trend: "Keep practicing",
    progress: sampleMetrics.interviewReadiness,
    accent: "bg-indigo-500",
    track: "bg-indigo-100",
    icon: "◌",
    iconTone: "bg-indigo-100 text-indigo-600",
  },
  {
    title: "Learning Streak",
    value: "7",
    delta: " Days",
    trend: "Keep it up!",
    progress: 78,
    accent: "bg-violet-500",
    track: "bg-violet-100",
    icon: "✦",
    iconTone: "bg-violet-100 text-violet-600",
  },
];

const skillStrength = [
  { name: "Frontend", current: 82, target: 90 },
  { name: "Backend", current: 66, target: 80 },
  { name: "Database", current: 42, target: 75 },
  { name: "Problem Solving", current: 58, target: 78 },
];

const trendPoints = [
  32, 38, 44, 48, 55, 61, 68, 72, 75, 80, 76, 82,
];

const aiInsights = [
  {
    title: "Great Progress!",
    description: "Your resume score improved by 12% this week.",
    icon: "↗",
    tone: "bg-emerald-100 text-emerald-700",
  },
  {
    title: "Top Strength",
    description: "You are strong in JavaScript and problem solving.",
    icon: "★",
    tone: "bg-violet-100 text-violet-700",
  },
  {
    title: "Focus Area",
    description: "Improve your system design skills to increase job match.",
    icon: "!",
    tone: "bg-orange-100 text-orange-700",
  },
];

const skillGaps = sampleSkills
  .filter((skill) => skill.current < skill.target)
  .slice(0, 5)
  .map((skill) => ({
    name: skill.name,
    gap: skill.target - skill.current,
    level: skill.priority,
    color: skill.priority === "High" ? "bg-rose-500" : skill.priority === "Medium" ? "bg-amber-500" : "bg-emerald-500",
  }));

const planItems = [
  { label: "Complete React Basics Course", time: "45 min", done: true },
  { label: "Solve 2 DSA Problems", time: "30 min", done: true },
  { label: "Attend Mock Interview", time: "60 min", done: false },
];

const recentAnalysis = [
  { title: "Arjun_Mehta_Resume_May2025.pdf", meta: "Sample analysis · 20 May 2025", score: `${sampleMetrics.resumeScore}/100` },
  { title: "Resume score preview", meta: "Illustrative sample entry", score: `${sampleMetrics.resumeScore}/100` },
];

const recentActivity = [
  { title: "Resume analyzed successfully", time: "2h ago" },
  { title: "React Advanced course completed", time: "5h ago" },
  { title: "Solved 2 DSA problems", time: "1d ago" },
  { title: "Mock interview completed", time: "2d ago" },
];

const quickActions = [
  { title: "Upload Resume", icon: "↑", href: "/resume" },
  { title: "AI Assistant", icon: "✦", href: "/career-assistant" },
  { title: "Mock Interview", icon: "◫", href: null },
  { title: "Skill Assessment", icon: "▣", href: "/skill-gap" },
];

function DashboardCard({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`rounded-[18px] border border-slate-200 bg-white shadow-[0_1px_2px_rgba(15,23,42,0.04),0_6px_18px_rgba(15,23,42,0.04)] ${className}`}>
      {children}
    </div>
  );
}

export default function Dashboard() {
  const { profile } = useCandidateProfile();
  const roadmapPhases = getRoadmapPhases(profile.roadmap);
  const roadmapItems = roadmapPhases.flatMap((phase) => phase.items);
  const roadmapProgress = calculateRoadmapProgress(profile.roadmap);
  const roadmapPreviewItems = roadmapItems.slice(0, 5).map((item) => ({
    name: item.skill,
    status: item.status,
    icon: item.status === "Completed" ? "✓" : item.status === "In progress" ? "⌁" : "◌",
  }));

  return (
    <div className="min-h-screen bg-background px-3 py-4 md:px-5 lg:px-6 xl:px-8">
      <div className="mx-auto max-w-[1520px]">
        <header className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="mb-1 text-[0.95rem] font-medium text-slate-700">Good morning, Arjun!</h1>
            <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400">
              Sample dashboard data
            </p>
          </div>

          <div className="flex items-center gap-3 self-start lg:self-auto">
            <label className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 shadow-sm" title="Search is not available in this prototype">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-4 w-4 text-slate-400" aria-hidden="true">
                <circle cx="11" cy="11" r="5.5" />
                <path d="M16 16l4 4" strokeLinecap="round" />
              </svg>
              <input type="search" aria-label="Search unavailable in this prototype" placeholder="Search unavailable" disabled className="w-36 bg-transparent text-sm text-slate-400 outline-none placeholder:text-slate-400 disabled:cursor-not-allowed" />
            </label>

            <button type="button" aria-label="Notifications unavailable in demo" title="Notifications are not available in this demo" disabled className="flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-500 opacity-50 shadow-sm">
              <span aria-hidden="true">🔔</span>
            </button>
            <button type="button" aria-label="Theme unavailable in demo" title="Theme switching is not available in this demo" disabled className="flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-500 opacity-50 shadow-sm">
              <span aria-hidden="true">☾</span>
            </button>
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-sky-400 to-indigo-500 text-sm font-semibold text-white">
              A
            </div>
          </div>
        </header>

        <section className="mb-5 grid gap-4 md:grid-cols-2 2xl:grid-cols-5">
          {statCards.map((card) => (
            <DashboardCard key={card.title} className="p-4 md:p-4">
              <div className="mb-3 flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-slate-500">{card.title}</p>
                </div>
                <div className={`flex h-10 w-10 items-center justify-center rounded-xl text-lg font-semibold ${card.iconTone}`}>
                  {card.icon}
                </div>
              </div>

              <div className="flex items-end gap-1">
                <span className="text-[2rem] font-bold tracking-[-0.06em] text-slate-900">{card.value}</span>
                <span className="pb-2 text-sm font-medium text-slate-400">{card.delta}</span>
              </div>

              <p className="mt-2 text-sm text-slate-500">{card.trend}</p>

              <div className={`mt-4 h-2 overflow-hidden rounded-full ${card.track}`}>
                <div className={`h-full rounded-full ${card.accent}`} style={{ width: `${card.progress}%` }} />
              </div>
            </DashboardCard>
          ))}
        </section>

        <section className="mb-5 grid gap-4 xl:grid-cols-[1.18fr_1.6fr_1.08fr]">
          <DashboardCard className="p-4">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-slate-900">Skill Strength Overview</h2>
              <span className="text-sm font-medium text-slate-400">Your Strength</span>
            </div>

            <div className="space-y-4">
              {skillStrength.map((skill) => (
                <div key={skill.name}>
                  <div className="mb-2 flex items-center justify-between text-sm">
                    <span className="font-medium text-slate-700">{skill.name}</span>
                    <span className="text-slate-500">{skill.current}%</span>
                  </div>

                  <div className="relative h-2.5 overflow-hidden rounded-full bg-slate-200">
                    <div className="absolute inset-y-0 left-0 rounded-full bg-indigo-500" style={{ width: `${skill.current}%` }} />
                    <div className="absolute inset-y-0 rounded-full border border-dashed border-slate-400" style={{ left: `${skill.target}%`, width: "2px" }} />
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-5 flex items-center gap-5 text-xs text-slate-500">
              <div className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-indigo-500" />Current</div>
              <div className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full border border-slate-400 bg-white" />Target</div>
            </div>
          </DashboardCard>

          <DashboardCard className="p-4">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-slate-900">Career Readiness Trend</h2>
              <button type="button" disabled title="Date filtering is not available in this demo" className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-500 opacity-60">
                This Month ▾
              </button>
            </div>

            <div className="h-56 w-full">
              <svg viewBox="0 0 460 200" className="h-full w-full" preserveAspectRatio="none" aria-label="Career readiness trend chart">
                <defs>
                  <linearGradient id="trendFill" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="#4f46e5" stopOpacity="0.22" />
                    <stop offset="100%" stopColor="#4f46e5" stopOpacity="0.02" />
                  </linearGradient>
                </defs>
                {[0, 25, 50, 75, 100].map((value) => (
                  <line key={value} x1="0" x2="460" y1={170 - value * 1.3} y2={170 - value * 1.3} stroke="#e2e8f0" strokeDasharray="3 6" />
                ))}
                <path d="M0 150 C 40 148, 50 142, 85 120 S 160 92, 210 108 S 300 86, 340 70 S 400 48, 460 38 L 460 200 L 0 200 Z" fill="url(#trendFill)" />
                <path d="M0 150 C 40 148, 50 142, 85 120 S 160 92, 210 108 S 300 86, 340 70 S 400 48, 460 38" fill="none" stroke="#4f46e5" strokeWidth="3" strokeLinecap="round" />
                {trendPoints.map((point, index) => {
                  const x = index * 38 + 14;
                  const y = 170 - point * 1.15;
                  return <circle key={`${point}-${index}`} cx={x} cy={y} r="3.8" fill="#4f46e5" stroke="white" strokeWidth="2" />;
                })}
                {["1 May", "8 May", "15 May", "22 May", "29 May"].map((label, index) => (
                  <text key={label} x={index * 115} y="190" textAnchor={index === 0 ? "start" : index === 4 ? "end" : "middle"} fill="#94a3b8" fontSize="11">{label}</text>
                ))}
              </svg>
            </div>
          </DashboardCard>

          <DashboardCard className="p-4">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-slate-900">AI Insights</h2>
              <Link href="/career-assistant" className="text-sm font-medium text-indigo-600 hover:text-indigo-800">Open assistant</Link>
            </div>

            <div className="space-y-3">
              {aiInsights.map((item) => (
                <div key={item.title} className="flex items-start gap-3 rounded-xl bg-slate-50 p-3">
                  <div className={`flex h-9 w-9 items-center justify-center rounded-full text-sm font-semibold ${item.tone}`} aria-hidden="true">
                    {item.icon}
                  </div>
                  <div>
                    <p className="font-semibold text-slate-800">{item.title}</p>
                    <p className="mt-1 text-sm leading-5 text-slate-500">{item.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </DashboardCard>
        </section>

        <section className="mb-5 grid gap-4 xl:grid-cols-[1.42fr_1.25fr_1.12fr]">
          <DashboardCard className="p-4">
            <div className="mb-5 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-slate-900">Recommended Learning Path</h2>
              <Link href="/learning-roadmap" className="text-sm font-medium text-indigo-600 hover:text-indigo-800">Open roadmap</Link>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
              {roadmapPreviewItems.length === 0 ? (
                <p className="col-span-full rounded-xl border border-dashed border-slate-300 px-3 py-6 text-center text-sm text-slate-500">
                  No sample learning tasks are available yet.
                </p>
              ) : roadmapPreviewItems.map((item) => (
                <div key={item.name} className="rounded-2xl border border-slate-200 bg-slate-50 p-3 text-center">
                  <div className={`mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-full text-lg font-bold ${item.status === "Completed" ? "bg-emerald-100 text-emerald-700" : item.status === "In progress" ? "bg-indigo-100 text-indigo-700" : "bg-slate-200 text-slate-500"}`} aria-hidden="true">
                    {item.icon}
                  </div>
                  <p className="text-sm font-semibold text-slate-800">{item.name}</p>
                  <p className="mt-1 text-[11px] uppercase tracking-[0.12em] text-slate-500">{item.status}</p>
                </div>
              ))}
            </div>

            <div className="mt-5">
              <div className="mb-2 flex items-center justify-between text-sm text-slate-500">
                <span>Overall Progress</span>
                <span className="font-semibold text-indigo-600">{roadmapProgress}%</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-slate-200" role="progressbar" aria-label="Sample learning roadmap progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={roadmapProgress}>
                <div className="h-full rounded-full bg-indigo-500" style={{ width: `${roadmapProgress}%` }} />
              </div>
            </div>
          </DashboardCard>

          <DashboardCard className="p-4">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-slate-900">Top Skill Gaps</h2>
              <Link href="/skill-gap" className="text-sm font-medium text-indigo-600 hover:text-indigo-800">Explore skill gaps</Link>
            </div>

            <div className="space-y-4">
              {skillGaps.map((skill) => (
                <div key={skill.name}>
                  <div className="mb-2 flex items-center justify-between text-sm">
                    <span className="font-medium text-slate-700">{skill.name}</span>
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500">{skill.level} · {skill.gap} pt gap</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-slate-200">
                    <div className={`h-full rounded-full ${skill.color}`} style={{ width: `${skill.gap}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </DashboardCard>

          <DashboardCard className="p-4">
            <div className="mb-4">
              <h2 className="text-xl font-semibold text-slate-900">Today&apos;s Plan</h2>
            </div>

            <div className="space-y-3">
              {planItems.map((item) => (
                <div key={item.label} className="flex items-center gap-3 rounded-xl bg-slate-50 p-2.5">
                  <span className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold ${item.done ? "bg-emerald-500 text-white" : "border border-slate-300 text-slate-400"}`} aria-hidden="true">
                    {item.done ? "✓" : "○"}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-700">{item.label}</p>
                  </div>
                  <span className="text-xs text-slate-500">{item.time}</span>
                </div>
              ))}
            </div>

            <Link href="/learning-roadmap" className="mt-5 flex w-full items-center justify-center rounded-xl bg-primary px-4 py-3 text-sm font-semibold text-white transition hover:bg-primary-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300 focus-visible:ring-offset-2 focus-visible:ring-offset-white">
              View Full Roadmap →
            </Link>
          </DashboardCard>
        </section>

        <section className="grid gap-4 xl:grid-cols-[1.3fr_1.1fr_1fr]">
          <DashboardCard className="p-4">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-slate-900">Recent Analysis</h2>
              <span className="text-xs font-medium text-slate-400">Sample entries</span>
            </div>

            <div className="space-y-3">
              {recentAnalysis.map((item) => (
                <div key={item.title} className="flex flex-col justify-between gap-3 rounded-xl border border-slate-200 bg-slate-50 p-3 sm:flex-row sm:items-center">
                  <div className="min-w-0 flex-1">
                    <p className="break-words font-medium text-slate-800">{item.title}</p>
                    <p className="mt-1 text-xs text-slate-500">{item.meta}</p>
                  </div>
                  <div className="flex flex-wrap items-center justify-between gap-3 sm:justify-end">
                    <span className="text-lg font-bold text-slate-900">{item.score}</span>
                  </div>
                </div>
              ))}
            </div>
          </DashboardCard>

          <DashboardCard className="p-4">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-slate-900">Recent Activity</h2>
            </div>

            <div className="space-y-3">
              {recentActivity.map((item) => (
                <div key={item.title} className="flex min-w-0 items-start gap-3 rounded-xl bg-slate-50 p-3">
                  <span className="mt-0.5 flex h-6 w-6 items-center justify-center rounded-full bg-slate-200 text-[10px] font-bold text-slate-700" aria-hidden="true">
                    •
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="break-words text-sm font-medium text-slate-700">{item.title}</p>
                  </div>
                  <span className="shrink-0 text-[11px] text-slate-400">{item.time}</span>
                </div>
              ))}
            </div>
          </DashboardCard>

          <DashboardCard className="p-4">
            <div className="mb-4">
              <h2 className="text-xl font-semibold text-slate-900">Quick Actions</h2>
            </div>

            <div className="grid grid-cols-2 gap-3">
              {quickActions.map((action) => {
                const content = (
                  <>
                  <span className="mb-2 flex h-9 w-9 items-center justify-center rounded-xl bg-white text-xl text-slate-600 shadow-sm">{action.icon}</span>
                  <span className="text-sm font-medium text-slate-700">{action.title}</span>
                    {action.href ? null : <span className="mt-1 text-[10px] font-medium text-slate-400">Coming soon</span>}
                  </>
                );
                const className = `flex min-h-[90px] flex-col items-center justify-center rounded-2xl border border-slate-200 bg-slate-50 px-3 py-4 text-center ${action.href ? "transition hover:border-indigo-200 hover:bg-indigo-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300" : "cursor-default opacity-75"}`;
                return action.href ? (
                  <Link key={action.title} href={action.href} className={className}>{content}</Link>
                ) : (
                  <div key={action.title} className={className} aria-label={`${action.title}, coming soon`}>{content}</div>
                );
              })}
            </div>
          </DashboardCard>
        </section>
      </div>
    </div>
  );
}