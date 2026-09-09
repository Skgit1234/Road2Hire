const skills = [
  {
    name: "React.js",
    current: "Intermediate",
    target: "Advanced",
    progress: 65,
    priority: "High",
  },
  {
    name: "TypeScript",
    current: "Beginner",
    target: "Advanced",
    progress: 35,
    priority: "High",
  },
  {
    name: "Data Structures",
    current: "Intermediate",
    target: "Advanced",
    progress: 55,
    priority: "Medium",
  },
  {
    name: "System Design",
    current: "Beginner",
    target: "Intermediate",
    progress: 25,
    priority: "Medium",
  },
];

export default function SkillGapPage() {
  return (
    <div className="min-h-screen bg-background p-8">
      {/* Header */}
      <header className="mb-8">
        <p className="mb-2 text-sm font-medium text-primary">Skill Analysis</p>

        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          Your Skill Gap
        </h1>

        <p className="mt-2 max-w-2xl text-muted">
          Understand where your current skills stand and what you should focus
          on next.
        </p>
      </header>

      {/* Summary */}
      <section className="mb-8 grid gap-5 sm:grid-cols-3">
        <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
          <p className="text-sm font-medium text-muted">Skills Analyzed</p>
          <p className="mt-3 text-3xl font-bold text-foreground">25</p>
          <p className="mt-2 text-sm text-muted">
            Skills identified from your profile
          </p>
        </div>

        <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
          <p className="text-sm font-medium text-muted">Skills to Improve</p>
          <p className="mt-3 text-3xl font-bold text-foreground">7</p>
          <p className="mt-2 text-sm text-muted">
            Recommended areas for improvement
          </p>
        </div>

        <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
          <p className="text-sm font-medium text-muted">Priority Skills</p>
          <p className="mt-3 text-3xl font-bold text-primary">2</p>
          <p className="mt-2 text-sm text-muted">
            Skills requiring immediate attention
          </p>
        </div>
      </section>

      {/* Skills */}
      <section className="rounded-xl border border-border bg-card p-6 shadow-sm">
        <div className="mb-6">
          <h2 className="text-xl font-semibold text-foreground">
            Recommended Skills
          </h2>

          <p className="mt-1 text-sm text-muted">
            Focus on these skills to improve your career readiness.
          </p>
        </div>

        <div className="space-y-5">
          {skills.map((skill) => (
            <div
              key={skill.name}
              className="rounded-lg border border-border p-5"
            >
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h3 className="font-semibold text-foreground">
                    {skill.name}
                  </h3>

                  <p className="mt-1 text-sm text-muted">
                    Current: {skill.current} → Target: {skill.target}
                  </p>
                </div>

                <span
                  className={`w-fit rounded-full px-3 py-1 text-xs font-semibold ${
                    skill.priority === "High"
                      ? "bg-red-50 text-red-600"
                      : "bg-amber-50 text-amber-600"
                  }`}
                >
                  {skill.priority} Priority
                </span>
              </div>

              <div className="mt-4">
                <div className="mb-2 flex justify-between text-xs text-muted">
                  <span>Current proficiency</span>
                  <span>{skill.progress}%</span>
                </div>

                <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className="h-full rounded-full bg-primary"
                    style={{ width: `${skill.progress}%` }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}