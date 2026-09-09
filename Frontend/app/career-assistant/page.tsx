const suggestions = [
  "How can I improve my resume?",
  "What skills should I learn next?",
  "Prepare me for a technical interview",
];

export default function CareerAssistantPage() {
  return (
    <div className="min-h-screen bg-background p-8">
      {/* Header */}
      <header className="mb-8">
        <p className="mb-2 text-sm font-medium text-primary">
          AI Career Support
        </p>

        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          AI Career Assistant
        </h1>

        <p className="mt-2 max-w-2xl text-muted">
          Get personalized career guidance, skill recommendations, and
          interview preparation with your AI career assistant.
        </p>
      </header>

      {/* Assistant Card */}
      <section className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
        {/* Assistant Header */}
        <div className="border-b border-border p-6">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-50 text-2xl">
              ✨
            </div>

            <div>
              <h2 className="font-semibold text-foreground">
                Road2Hire AI
              </h2>

              <p className="text-sm text-muted">
                Your personalized career companion
              </p>
            </div>
          </div>
        </div>

        {/* Chat Area */}
        <div className="min-h-[360px] space-y-6 bg-slate-50 p-6">
          {/* AI Message */}
          <div className="flex max-w-2xl gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-blue-100 text-sm">
              ✨
            </div>

            <div className="rounded-xl rounded-tl-none bg-white p-4 shadow-sm">
              <p className="text-sm leading-6 text-muted">
                Hi! I&apos;m your Road2Hire AI career assistant. I can help
                you understand your skill gaps, improve your resume, create a
                learning plan, and prepare for interviews.
              </p>
            </div>
          </div>

          {/* User Message */}
          <div className="ml-auto flex max-w-2xl justify-end">
            <div className="rounded-xl rounded-tr-none bg-primary p-4 text-white shadow-sm">
              <p className="text-sm leading-6">
                What should I focus on to become job ready?
              </p>
            </div>
          </div>

          {/* AI Response */}
          <div className="flex max-w-2xl gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-blue-100 text-sm">
              ✨
            </div>

            <div className="rounded-xl rounded-tl-none bg-white p-4 shadow-sm">
              <p className="text-sm leading-6 text-muted">
                Based on your current profile, I recommend focusing on React,
                Next.js, backend development, and interview preparation. Your
                learning roadmap has been designed around these priorities.
              </p>
            </div>
          </div>
        </div>

        {/* Suggested Questions */}
        <div className="border-t border-border p-6">
          <p className="mb-3 text-sm font-medium text-foreground">
            Try asking
          </p>

          <div className="flex flex-wrap gap-3">
            {suggestions.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                className="rounded-lg border border-border bg-white px-4 py-2 text-sm text-muted transition hover:border-primary hover:text-primary"
              >
                {suggestion}
              </button>
            ))}
          </div>

          {/* Input */}
          <div className="mt-5 flex gap-3">
            <input
              type="text"
              placeholder="Ask your career question..."
              className="flex-1 rounded-lg border border-border bg-white px-4 py-3 text-sm outline-none transition focus:border-primary"
            />

            <button
              type="button"
              className="rounded-lg bg-primary px-6 py-3 text-sm font-medium text-white transition hover:opacity-90"
            >
              Send
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}