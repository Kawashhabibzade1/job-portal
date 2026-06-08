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
    return `${currency} ${Math.round(job.salary_min).toLocaleString()} - ${Math.round(
      job.salary_max,
    ).toLocaleString()}`.trim();
  }
  const value = job.salary_min || job.salary_max;
  return `${currency} ${Math.round(value).toLocaleString()}`.trim();
}

export default function JobCard({ job }) {
  const postedAt = formatDate(job.date_posted);
  const salary = formatSalary(job);
  const link = job.apply_url || job.source_url;

  return (
    <article className="rounded-lg border border-line bg-panel p-4 shadow-sm transition hover:border-slate-300 hover:shadow-md">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0 space-y-3">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="break-words text-lg font-semibold leading-snug text-ink">
                {job.title || "Untitled role"}
              </h2>
              {job.is_remote && (
                <span className="rounded-full border border-teal-200 bg-teal-50 px-2 py-0.5 text-xs font-medium text-mint">
                  Remote
                </span>
              )}
            </div>

            <div className="flex flex-wrap gap-x-4 gap-y-2 text-sm text-slate-600">
              {job.company && (
                <span className="inline-flex items-center gap-1.5">
                  <BriefcaseBusiness className="h-4 w-4" aria-hidden="true" />
                  {job.company}
                </span>
              )}
              {job.location && (
                <span className="inline-flex items-center gap-1.5">
                  <MapPin className="h-4 w-4" aria-hidden="true" />
                  {job.location}
                </span>
              )}
              {postedAt && (
                <span className="inline-flex items-center gap-1.5">
                  <CalendarDays className="h-4 w-4" aria-hidden="true" />
                  {postedAt}
                </span>
              )}
              {salary && (
                <span className="inline-flex items-center gap-1.5">
                  <Banknote className="h-4 w-4" aria-hidden="true" />
                  {salary}
                </span>
              )}
            </div>
          </div>

          {job.description && (
            <p className="line-clamp-3 text-sm leading-6 text-slate-700">
              {job.description}
            </p>
          )}
        </div>

        <div className="flex shrink-0 items-center justify-between gap-3 md:flex-col md:items-end">
          <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
            {job.source}
          </span>
          {link && (
            <a
              href={link}
              target="_blank"
              rel="noreferrer"
              className="inline-flex min-h-10 items-center gap-2 rounded-lg bg-ink px-3 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-ocean focus:ring-offset-2"
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

