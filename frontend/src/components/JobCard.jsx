import {
  Banknote,
  BriefcaseBusiness,
  CalendarDays,
  ExternalLink,
  MapPin,
} from "lucide-react";

function formatDate(value) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}

function formatSalary(job) {
  if (!job.salary_min && !job.salary_max) return null;
  const currency = job.currency || "";
  if (job.salary_min && job.salary_max) {
    return `${currency} ${Math.round(job.salary_min).toLocaleString()} – ${Math.round(
      job.salary_max,
    ).toLocaleString()}`.trim();
  }
  const value = job.salary_min || job.salary_max;
  return `${currency} ${Math.round(value).toLocaleString()}`.trim();
}

export default function JobCard({ job }) {
  const postedAt = formatDate(job.date_posted);
  const salary = job.salary_text || formatSalary(job);
  const link = job.apply_url || job.source_url;
  const sources = job.sources?.length ? job.sources : [job.source].filter(Boolean);

  return (
    <article className="glass glow-border rounded-xl p-4 transition-all duration-300">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 space-y-3">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="break-words text-base font-semibold leading-snug text-ink sm:text-lg">
                {job.title || "Untitled role"}
              </h2>
              {job.is_remote && (
                <span className="chip chip-active text-cyan">
                  Remote
                </span>
              )}
            </div>

            <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-sm text-ink-muted">
              {job.company && (
                <span className="inline-flex items-center gap-1.5">
                  <BriefcaseBusiness className="h-3.5 w-3.5" aria-hidden="true" />
                  {job.company}
                </span>
              )}
              {job.location && (
                <span className="inline-flex items-center gap-1.5">
                  <MapPin className="h-3.5 w-3.5" aria-hidden="true" />
                  {job.location}
                </span>
              )}
              {postedAt && (
                <span className="inline-flex items-center gap-1.5">
                  <CalendarDays className="h-3.5 w-3.5" aria-hidden="true" />
                  {postedAt}
                </span>
              )}
              {salary && (
                <span className="inline-flex items-center gap-1.5 text-mint">
                  <Banknote className="h-3.5 w-3.5" aria-hidden="true" />
                  {salary}
                </span>
              )}
            </div>
          </div>

          {job.description && (
            <p className="line-clamp-3 text-sm leading-6 text-ink-faint">
              {job.description}
            </p>
          )}
        </div>

        <div className="flex shrink-0 items-center justify-between gap-3 sm:flex-col sm:items-end">
          <div className="flex flex-wrap justify-end gap-1.5">
            {sources.map((source) => (
              <span
                key={source}
                className="chip chip-inactive text-xs uppercase tracking-wide"
              >
                {source}
              </span>
            ))}
          </div>
          {link && (
            <a
              href={link}
              target="_blank"
              rel="noreferrer"
              className="btn-primary whitespace-nowrap"
            >
              Apply
              <ExternalLink className="h-4 w-4" aria-hidden="true" />
            </a>
          )}
        </div>
      </div>
    </article>
  );
}
