const roadmap = [
  {
    step: "01",
    title: "Master React.js",
    description:
      "Strengthen your React fundamentals, hooks, state management, and component architecture.",
    duration: "2 weeks",
    progress: 65,
    status: "In Progress",
  },
  {
    step: "02",
    title: "Learn Next.js",
    description:
      "Build modern applications using routing, server components, API integration, and deployment.",
    duration: "2 weeks",
    progress: 30,
    status: "In Progress",
  },
  {
    step: "03",
    title: "Backend Development",
    description:
      "Learn REST APIs, authentication, databases, and backend application development.",
    duration: "3 weeks",
    progress: 0,
    status: "Upcoming",
  },
  {
    step: "04",
    title: "Interview Preparation",
    description:
      "Practice DSA, technical interviews, behavioral questions, and real-world problem solving.",
    duration: "2 weeks",
    progress: 0,
    status: "Upcoming",
  },
];

export default function LearningRoadmapPage() {
  return (
    <div className="min-h-screen bg-background p-8">
      {/* Header */}
      <header className="mb-8">
        <p className="mb-2 text-sm font-medium text-primary">
          Personalized Learning
        </p>

        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          Learning Roadmap
        </h1>

        <p className="mt-2 max-w-2xl text-muted">
          Follow your personalized learning path and build the skills needed
          for your target career.
        </p>
      </header>

      {/* Progress Overview */}
      <section className="mb-8 rounded-xl border border-border bg-card p-7 shadow-sm">
        <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm font-medium text-muted">
              Overall Roadmap Progress
            </p>

            <h2 className="mt-1 text-4xl font-bold text-primary">34%</h2>

            <p className="mt-2 text-sm text-muted">
              2 of 4 learning stages started
            </p>
          </div>

          <div className="w-full max-w-lg">
            <div className="mb-2 flex justify-between text-sm text-muted">
              <span>Progress</span>
              <span>34%</span>
            </div>

            <div className="h-3 overflow-hidden rounded-full bg-slate-100">
              <div className="h-full w-[34%] rounded-full bg-primary" />
            </div>
          </div>
        </div>
      </section>

      {/* Roadmap */}
      <section>
        <div className="mb-5">
          <h2 className="text-xl font-semibold text-foreground">
            Your Learning Path
          </h2>

          <p className="mt-1 text-sm text-muted">
            Complete each stage to move closer to your career goal.
          </p>
        </div>

        <div className="space-y-5">
          {roadmap.map((item) => (
            <div
              key={item.step}
              className="rounded-xl border border-border bg-card p-6 shadow-sm"
            >
              <div className="flex flex-col gap-5 md:flex-row md:items-start">
                {/* Step */}
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-blue-50 font-bold text-primary">
                  {item.step}
                </div>

                {/* Content */}
                <div className="flex-1">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <h3 className="text-lg font-semibold text-foreground">
                      {item.title}
                    </h3>

                    <span
                      className={`w-fit rounded-full px-3 py-1 text-xs font-medium ${
                        item.status === "In Progress"
                          ? "bg-blue-50 text-primary"
                          : "bg-slate-100 text-muted"
                      }`}
                    >
                      {item.status}
                    </span>
                  </div>

                  <p className="mt-2 text-sm leading-6 text-muted">
                    {item.description}
                  </p>

                  <div className="mt-5 flex items-center justify-between text-sm">
                    <span className="text-muted">
                      Estimated duration: {item.duration}
                    </span>

                    <span className="font-medium text-foreground">
                      {item.progress}%
                    </span>
                  </div>

                  <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className="h-full rounded-full bg-primary"
                      style={{ width: `${item.progress}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* AI Recommendation */}
      <section className="mt-8 rounded-xl border border-purple-100 bg-purple-50 p-6">
        <h2 className="text-lg font-semibold text-foreground">
          AI Learning Recommendation
        </h2>

        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
          Continue focusing on React.js and Next.js before moving to backend
          development. Completing these priority skills will improve your
          readiness for full-stack developer roles.
        </p>
      </section>
    </div>
  );
}