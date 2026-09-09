const stats = [
  {
    label: "Career Readiness",
    value: "72%",
    description: "Overall readiness score",
  },
  {
    label: "Skills Matched",
    value: "18",
    description: "Relevant skills identified",
  },
  {
    label: "Skills to Improve",
    value: "7",
    description: "Skills recommended to learn",
  },
  {
    label: "Learning Progress",
    value: "34%",
    description: "Roadmap completion",
  },
];

const quickActions = [
  {
    title: "Upload Resume",
    description: "Analyze your resume and discover skill gaps.",
    href: "/resume",
  },
  {
    title: "View Skill Gap",
    description: "See which skills you need to improve.",
    href: "/skill-gap",
  },
  {
    title: "Career Readiness",
    description: "Check your current career preparation score.",
    href: "/career-readiness",
  },
  {
    title: "Learning Roadmap",
    description: "Follow your personalized learning journey.",
    href: "/learning-roadmap",
  },
];

export default function Dashboard() {
  return (
    <div className="min-h-screen bg-background p-8">
      {/* Header */}
      <header className="mb-8">
        <p className="mb-2 text-sm font-medium text-primary">
          Welcome to Road2Hire
        </p>

        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          Your Career Dashboard
        </h1>

        <p className="mt-2 text-muted">
          Track your progress, identify skill gaps, and prepare for your dream
          career.
        </p>
      </header>

      {/* Stats */}
      <section className="mb-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <div
            key={stat.label}
            className="rounded-xl border border-border bg-card p-6 shadow-sm"
          >
            <p className="text-sm font-medium text-muted">{stat.label}</p>

            <p className="mt-3 text-3xl font-bold text-foreground">
              {stat.value}
            </p>

            <p className="mt-2 text-sm text-muted">{stat.description}</p>
          </div>
        ))}
      </section>

      {/* Career Readiness */}
      <section className="mb-8 rounded-xl border border-border bg-card p-6 shadow-sm">
        <div className="mb-5 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-foreground">
              Career Readiness
            </h2>

            <p className="mt-1 text-sm text-muted">
              Your overall preparation for your target career.
            </p>
          </div>

          <span className="text-2xl font-bold text-primary">72%</span>
        </div>

        <div className="h-3 overflow-hidden rounded-full bg-slate-100">
          <div className="h-full w-[72%] rounded-full bg-primary" />
        </div>

        <div className="mt-4 flex justify-between text-sm text-muted">
          <span>Getting Started</span>
          <span>Job Ready</span>
        </div>
      </section>

      {/* Quick Actions */}
      <section>
        <div className="mb-5">
          <h2 className="text-xl font-semibold text-foreground">
            Quick Actions
          </h2>

          <p className="mt-1 text-sm text-muted">
            Continue building your career readiness.
          </p>
        </div>

        <div className="grid gap-5 md:grid-cols-2">
          {quickActions.map((action) => (
            <a
              key={action.title}
              href={action.href}
              className="group rounded-xl border border-border bg-card p-6 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
            >
              <h3 className="text-lg font-semibold text-foreground group-hover:text-primary">
                {action.title}
              </h3>

              <p className="mt-2 text-sm leading-6 text-muted">
                {action.description}
              </p>

              <span className="mt-4 inline-block text-sm font-medium text-primary">
                Explore →
              </span>
            </a>
          ))}
        </div>
      </section>
    </div>
  );
}