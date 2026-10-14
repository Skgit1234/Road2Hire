export type SkillPriority = "High" | "Medium" | "Low";

export type DataProvenance =
  | { kind: "sample"; label: string }
  | { kind: "user_provided"; updatedAt: string }
  | { kind: "resume_extracted"; sourceFingerprint: string; extractionVersion: string }
  | { kind: "calculated"; method: string; sourceFingerprint: string }
  | { kind: "inferred"; method: string; sourceFingerprint: string };

export type AnalysisStatus = "sample" | "ready" | "insufficient-data" | "stale";
export type ResumeProcessingStatus =
  | "empty"
  | "selected"
  | "sample-preview"
  | "processing"
  | "unsupported"
  | "malformed"
  | "failed"
  | "ready"
  | "stale";

export const sampleProvenance = {
  kind: "sample",
  label: "Road2Hire demo profile",
} as const satisfies Extract<DataProvenance, { kind: "sample" }>;

export type SampleSkill = {
  name: string;
  category: string;
  current: number;
  target: number;
  priority: SkillPriority;
  status: AnalysisStatus;
  provenance: Extract<DataProvenance, { kind: "sample" }>;
};

export type RoadmapStatus = "Completed" | "In progress" | "Upcoming";

export type RoadmapPhase = {
  phase: string;
  name: string;
  timeframe: string;
  items: Array<{
    id: string;
    title: string;
    skill: string;
    duration: string;
    status: RoadmapStatus;
    progress: number;
    statusDetail: AnalysisStatus;
    provenance: DataProvenance;
  }>;
};

export type RoadmapRecommendationPhase = {
  phase: string;
  name: string;
  timeframe: string;
  recommendations: Array<{
    id: string;
    title: string;
    skill: string;
    duration: string;
    statusDetail: AnalysisStatus;
    provenance: DataProvenance;
  }>;
};

export type RoadmapCompletion = {
  recommendationId: string;
  status: RoadmapStatus;
  progress: number;
};

export type SampleReadinessCategory = {
  name: string;
  score: number;
  note: string;
  status: "On track" | "Build next" | "Priority";
  statusDetail: AnalysisStatus;
  provenance: DataProvenance;
};

export const sampleMetrics = {
  resumeScore: 84,
  careerReadiness: 72,
  interviewReadiness: 61,
  status: "sample" as const,
  provenance: sampleProvenance,
};

export const sampleReadinessCategories: SampleReadinessCategory[] = [
  { name: "Technical skills", score: 78, note: "Strong foundation across core role technologies.", status: "On track", statusDetail: "sample", provenance: sampleProvenance },
  { name: "Projects & experience", score: 74, note: "Add one project that demonstrates end-to-end ownership.", status: "Build next", statusDetail: "sample", provenance: sampleProvenance },
  { name: "Resume quality", score: 82, note: "Impact is clear; quantify more of your results.", status: "On track", statusDetail: "sample", provenance: sampleProvenance },
  { name: "Interview preparation", score: sampleMetrics.interviewReadiness, note: "Practice explaining decisions and trade-offs aloud.", status: "Priority", statusDetail: "sample", provenance: sampleProvenance },
  { name: "Communication", score: 68, note: "Make your project stories concise and outcome-focused.", status: "Build next", statusDetail: "sample", provenance: sampleProvenance },
];

export const sampleSkills: SampleSkill[] = [
  { name: "Cloud Fundamentals", category: "Data & Cloud", current: 42, target: 75, priority: "High", status: "sample", provenance: sampleProvenance },
  { name: "TypeScript", category: "Web Development", current: 58, target: 85, priority: "High", status: "sample", provenance: sampleProvenance },
  { name: "System Design", category: "Career Skills", current: 48, target: 75, priority: "High", status: "sample", provenance: sampleProvenance },
  { name: "React", category: "Web Development", current: 72, target: 85, priority: "Medium", status: "sample", provenance: sampleProvenance },
  { name: "Node.js", category: "Web Development", current: 69, target: 80, priority: "Medium", status: "sample", provenance: sampleProvenance },
  { name: "SQL", category: "Data & Cloud", current: 74, target: 80, priority: "Low", status: "sample", provenance: sampleProvenance },
  { name: "Communication", category: "Career Skills", current: 78, target: 85, priority: "Low", status: "sample", provenance: sampleProvenance },
  { name: "Accessibility", category: "Web Development", current: 82, target: 85, priority: "Low", status: "sample", provenance: sampleProvenance },
  { name: "HTML & CSS", category: "Web Development", current: 90, target: 85, priority: "Low", status: "sample", provenance: sampleProvenance },
];

export const sampleRoadmap: RoadmapPhase[] = [
  {
    phase: "01",
    name: "Frontend foundations",
    timeframe: "Weeks 1–3",
    items: [
      { id: "frontend-foundations-react-patterns", title: "Modern React patterns", skill: "React", duration: "6 hours", status: "Completed", progress: 100, statusDetail: "sample", provenance: sampleProvenance },
      { id: "frontend-foundations-type-safe-features", title: "Type-safe application features", skill: "TypeScript", duration: "5 hours", status: "In progress", progress: 55, statusDetail: "sample", provenance: sampleProvenance },
    ],
  },
  {
    phase: "02",
    name: "Build and ship an application",
    timeframe: "Weeks 4–6",
    items: [
      { id: "ship-application-routing", title: "Routing and server rendering", skill: "Next.js", duration: "7 hours", status: "In progress", progress: 25, statusDetail: "sample", provenance: sampleProvenance },
      { id: "ship-application-deploy-portfolio", title: "Deploy a portfolio project", skill: "Projects", duration: "8 hours", status: "Upcoming", progress: 0, statusDetail: "sample", provenance: sampleProvenance },
    ],
  },
  {
    phase: "03",
    name: "Backend and data",
    timeframe: "Weeks 7–10",
    items: [
      { id: "backend-data-rest-endpoints", title: "Design and build REST endpoints", skill: "Node.js APIs", duration: "8 hours", status: "Upcoming", progress: 0, statusDetail: "sample", provenance: sampleProvenance },
      { id: "backend-data-query-data", title: "Persist and query application data", skill: "SQL & databases", duration: "6 hours", status: "Upcoming", progress: 0, statusDetail: "sample", provenance: sampleProvenance },
    ],
  },
  {
    phase: "04",
    name: "Prepare for your next role",
    timeframe: "Weeks 11–12",
    items: [
      { id: "next-role-system-design-interviews", title: "Practice system design and interviews", skill: "Interview preparation", duration: "6 hours", status: "Upcoming", progress: 0, statusDetail: "sample", provenance: sampleProvenance },
      { id: "next-role-project-stories", title: "Tell your project stories clearly", skill: "Communication", duration: "3 hours", status: "Upcoming", progress: 0, statusDetail: "sample", provenance: sampleProvenance },
    ],
  },
];

export const sampleRoadmapRecommendations: RoadmapRecommendationPhase[] = sampleRoadmap.map((phase) => ({
  phase: phase.phase,
  name: phase.name,
  timeframe: phase.timeframe,
  recommendations: phase.items.map(({ id, title, skill, duration, statusDetail, provenance }) => ({
    id,
    title,
    skill,
    duration,
    statusDetail,
    provenance,
  })),
}));

export const sampleRoadmapCompletions: RoadmapCompletion[] = sampleRoadmap.flatMap((phase) =>
  phase.items.map((item) => ({
    recommendationId: item.id,
    status: item.status,
    progress: item.progress,
  })),
);
