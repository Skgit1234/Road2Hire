const categories = [
  {
    name: "Technical Skills",
    score: 78,
    description: "Your technical skill coverage for the target role.",
  },
  {
    name: "Resume Strength",
    score: 82,
    description: "How effectively your resume presents your experience.",
  },
  {
    name: "Interview Preparation",
    score: 64,
    description: "Your current level of interview readiness.",
  },
  {
    name: "Industry Knowledge",
    score: 68,
    description: "Understanding of tools, trends, and industry expectations.",
  },
];

export default function CareerReadinessPage() {
  return (
    <div className="min-h-screen bg-background p-8">
      {/* Header */}
      <header className="mb-8">
        <p className="mb-2 text-sm font-medium text-primary">
          Career Assessment
        </p>

        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          Career Readiness
        </h1>

        <p className="mt-2 max-w-2xl text-muted">
          Get a clear picture of how prepared you are for your target career
          and where you can improve.
        </p>
      </header>

      {/* Overall Score */}
      <section className="mb-8 rounded-xl border border-border bg-card p-8 shadow-sm">
        <div className="flex flex-col gap-8 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm font-medium text-muted">
              Overall Readiness Score
            </p>

            <h2 className="mt-2 text-5xl font-bold text-primary">72%</h2>

            <p className="mt-3 max-w-xl text-sm leading-6 text-muted">
              You are making good progress. Focus on your interview
              preparation and industry knowledge to become more job ready.
            </p>
          </div>

          <div className="w-full max-w-md">
            <div className="mb-2 flex justify-between text-sm text-muted">
              <span>Current readiness</span>
              <span>72%</span>
            </div>

            <div className="h-4 overflow-hidden rounded-full bg-slate-100">
              <div className="h-full w-[72%] rounded-full bg-primary" />
            </div>

            <div className="mt-2 flex justify-between text-xs text-muted">
              <span>Getting Started</span>
              <span>Job Ready</span>
            </div>
          </div>
        </div>
      </section>

      {/* Readiness Categories */}
      <section>
        <div className="mb-5">
          <h2 className="text-xl font-semibold text-foreground">
            Readiness Breakdown
          </h2>

          <p className="mt-1 text-sm text-muted">
            Your performance across key career preparation areas.
          </p>
        </div>

        <div className="grid gap-5 md:grid-cols-2">
          {categories.map((category) => (
            <div
              key={category.name}
              className="rounded-xl border border-border bg-card p-6 shadow-sm"
            >
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-foreground">
                  {category.name}
                </h3>

                <span className="text-xl font-bold text-primary">
                  {category.score}%
                </span>
              </div>

              <p className="mt-2 text-sm text-muted">
                {category.description}
              </p>

              <div className="mt-5 h-2 overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full bg-primary"
                  style={{ width: `${category.score}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Recommendation */}
      <section className="mt-8 rounded-xl border border-purple-100 bg-purple-50 p-6">
        <h2 className="text-lg font-semibold text-foreground">
          AI Recommendation
        </h2>

        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
          Based on your current readiness, prioritize interview preparation
          and strengthen your industry knowledge. Completing these areas can
          significantly improve your overall career readiness.
        </p>
      </section>
    </div>
  );
}