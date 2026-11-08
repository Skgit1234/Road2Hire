import {
  isVerifiedExtractedField,
  type ExtractedDateRange,
  type ExtractedField,
  type ResumeExtractionResultV1,
} from "./resume-extraction-contract";

const card = "rounded-2xl border border-slate-200 bg-white p-5 shadow-sm";

function value(field: ExtractedField<string> | undefined): string | null {
  return field && isVerifiedExtractedField(field) && typeof field.value === "string"
    ? field.value
    : null;
}

function dateRange(dates: ExtractedDateRange): string {
  const start = isVerifiedExtractedField(dates.start)
    ? dates.start.value.value
    : null;
  const end = dates.isCurrent
    ? "Present"
    : isVerifiedExtractedField(dates.end)
      ? dates.end.value.value
      : null;

  return [start, end].filter(Boolean).join(" – ");
}

function Empty({ children = "No information extracted yet." }: { children?: string }) {
  return <p className="mt-3 text-sm text-slate-500">{children}</p>;
}

export function ProfileSkills({ data }: { data: ResumeExtractionResultV1 | null }) {
  const skills = data?.skills.filter((skill) => value(skill.name)) ?? [];

  return (
    <section className={card} aria-labelledby="profile-skills">
      <h2 id="profile-skills" className="font-semibold text-slate-900">Skills</h2>
      {skills.length ? (
        <ul className="mt-3 flex flex-wrap gap-2">
          {skills.map((skill) => {
            const confidence = skill.name.confidence;
            const source = skill.source === "explicit" ? "Explicit" : "Inferred";

            return (
              <li key={skill.id} className="rounded-lg bg-indigo-50 px-3 py-2 text-sm text-indigo-800">
                {value(skill.name)}{" "}
                <span className="text-xs text-slate-500">
                  ({source}{confidence !== undefined ? ` · ${Math.round(confidence * 100)}% confidence` : ""})
                </span>
              </li>
            );
          })}
        </ul>
      ) : <Empty />}
    </section>
  );
}

export function EducationSection({ data }: { data: ResumeExtractionResultV1 | null }) {
  const items = data?.education ?? [];

  return (
    <section className={card} aria-labelledby="profile-education">
      <h2 id="profile-education" className="font-semibold text-slate-900">Education</h2>
      {items.length ? (
        <ul className="mt-3 space-y-4">
          {items.map((item) => {
            const fieldOfStudy = value(item.fieldOfStudy);

            return (
              <li key={item.id}>
                <p className="font-medium text-slate-800">
                  {value(item.degree) ?? "Degree not specified"}{fieldOfStudy ? ` · ${fieldOfStudy}` : ""}
                </p>
                <p className="text-sm text-slate-600">{value(item.institution) ?? "Institution not specified"}</p>
                <p className="text-xs text-slate-500">{dateRange(item.dates)}</p>
              </li>
            );
          })}
        </ul>
      ) : <Empty />}
    </section>
  );
}

export function ExperienceSection({ data }: { data: ResumeExtractionResultV1 | null }) {
  const items = data?.experience ?? [];

  return (
    <section className={card} aria-labelledby="profile-experience">
      <h2 id="profile-experience" className="font-semibold text-slate-900">Work experience</h2>
      {items.length ? (
        <ul className="mt-3 space-y-4">
          {items.map((item) => (
            <li key={item.id}>
              <p className="font-medium text-slate-800">{value(item.title) ?? "Role not specified"}</p>
              <p className="text-sm text-slate-600">{value(item.organization) ?? "Organization not specified"}</p>
              <p className="text-xs text-slate-500">{dateRange(item.dates)}</p>
              {item.highlights.map((highlight, index) => {
                const text = value(highlight);
                return text ? <p key={`${item.id}-${index}`} className="mt-1 text-sm text-slate-600">{text}</p> : null;
              })}
            </li>
          ))}
        </ul>
      ) : <Empty />}
    </section>
  );
}

export function ProjectsSection({ data }: { data: ResumeExtractionResultV1 | null }) {
  const items = data?.projects ?? [];

  return (
    <section className={card} aria-labelledby="profile-projects">
      <h2 id="profile-projects" className="font-semibold text-slate-900">Projects</h2>
      {items.length ? (
        <ul className="mt-3 space-y-4">
          {items.map((item) => {
            const description = value(item.description);

            return (
              <li key={item.id}>
                <p className="font-medium text-slate-800">{value(item.name) ?? "Project name not specified"}</p>
                {description && <p className="mt-1 text-sm text-slate-600">{description}</p>}
                {item.skills.length > 0 && <p className="mt-1 text-xs text-slate-500">Skills: {item.skills.join(", ")}</p>}
              </li>
            );
          })}
        </ul>
      ) : <Empty />}
    </section>
  );
}

export function CertificationsSection({ data }: { data: ResumeExtractionResultV1 | null }) {
  const items = data?.certifications ?? [];

  return (
    <section className={card} aria-labelledby="profile-certifications">
      <h2 id="profile-certifications" className="font-semibold text-slate-900">Certifications</h2>
      {items.length ? (
        <ul className="mt-3 space-y-3">
          {items.map((item) => (
            <li key={item.id}>
              <p className="font-medium text-slate-800">{value(item.name) ?? "Certification not specified"}</p>
              <p className="text-sm text-slate-600">{value(item.issuer) ?? "Issuer not specified"}</p>
            </li>
          ))}
        </ul>
      ) : <Empty />}
    </section>
  );
}
