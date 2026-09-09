export default function ResumePage() {
  return (
    <div className="min-h-screen bg-background p-8">
      {/* Header */}
      <div className="mb-8">
        <p className="mb-2 text-sm font-medium text-primary">
          Resume Analysis
        </p>

        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          Upload Your Resume
        </h1>

        <p className="mt-2 max-w-2xl text-muted">
          Upload your resume to analyze your skills, identify gaps, and build a
          personalized career roadmap.
        </p>
      </div>

      {/* Upload Card */}
      <section className="mx-auto max-w-3xl rounded-xl border border-border bg-card p-8 shadow-sm">
        <div className="rounded-xl border-2 border-dashed border-border bg-slate-50 p-12 text-center">
          <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-blue-50 text-2xl">
            ↑
          </div>

          <h2 className="text-xl font-semibold text-foreground">
            Upload your resume
          </h2>

          <p className="mt-2 text-sm text-muted">
            Drag and drop your resume here, or select a file from your
            computer.
          </p>

          <button
            type="button"
            className="mt-6 rounded-lg bg-primary px-6 py-3 text-sm font-semibold text-white transition hover:bg-primary-dark"
          >
            Choose Resume
          </button>

          <p className="mt-4 text-xs text-muted">
            Supported formats: PDF, DOC, DOCX
          </p>
        </div>

        {/* Analysis Steps */}
        <div className="mt-8">
          <h3 className="text-lg font-semibold text-foreground">
            What happens next?
          </h3>

          <div className="mt-5 grid gap-4 sm:grid-cols-3">
            <div className="rounded-lg border border-border p-4">
              <p className="text-sm font-semibold text-primary">
                01. Analyze
              </p>
              <p className="mt-2 text-sm text-muted">
                Extract your skills and experience.
              </p>
            </div>

            <div className="rounded-lg border border-border p-4">
              <p className="text-sm font-semibold text-primary">
                02. Identify
              </p>
              <p className="mt-2 text-sm text-muted">
                Find gaps between your skills and career goals.
              </p>
            </div>

            <div className="rounded-lg border border-border p-4">
              <p className="text-sm font-semibold text-primary">
                03. Personalize
              </p>
              <p className="mt-2 text-sm text-muted">
                Generate your personalized learning roadmap.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}