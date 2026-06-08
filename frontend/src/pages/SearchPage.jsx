import { AlertCircle, Loader2, MapPin, Search } from "lucide-react";
import { useMemo, useState } from "react";

import { searchJobs } from "../api/jobs.js";
import JobCard from "../components/JobCard.jsx";

const PROVIDERS = [
  { key: "arbeitsagentur", label: "Arbeitsagentur" },
  { key: "arbeitnow", label: "Arbeitnow" },
  { key: "remotive", label: "Remotive" },
  { key: "adzuna", label: "Adzuna" },
  { key: "jsearch", label: "JSearch" },
  { key: "jooble", label: "Jooble" },
];

const COUNTRIES = [
  { code: "de", label: "Germany", defaultLocation: "Berlin" },
  { code: "gb", label: "United Kingdom", defaultLocation: "" },
  { code: "us", label: "United States", defaultLocation: "" },
  { code: "at", label: "Austria", defaultLocation: "" },
  { code: "ch", label: "Switzerland", defaultLocation: "" },
  { code: "tr", label: "Northern Cyprus (TRNC)", defaultLocation: "Northern Cyprus" },
];

export default function SearchPage() {
  const [query, setQuery] = useState("developer");
  const [location, setLocation] = useState("Berlin");
  const [country, setCountry] = useState("de");
  const [selectedSources, setSelectedSources] = useState(
    PROVIDERS.map((provider) => provider.key),
  );
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const providerSummary = useMemo(() => {
    if (!result?.sources) return [];
    return Object.entries(result.sources).map(([source, count]) => ({
      source,
      count,
    }));
  }, [result]);

  function toggleSource(source) {
    setSelectedSources((current) => {
      if (current.includes(source)) {
        const next = current.filter((item) => item !== source);
        return next.length ? next : current;
      }
      return [...current, source];
    });
  }

  function handleCountryChange(event) {
    const nextCountry = COUNTRIES.find((item) => item.code === event.target.value);
    const currentCountry = COUNTRIES.find((item) => item.code === country);
    setCountry(event.target.value);

    if (
      nextCountry?.defaultLocation &&
      (!location.trim() || location === currentCountry?.defaultLocation)
    ) {
      setLocation(nextCountry.defaultLocation);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const data = await searchJobs({
        query,
        location,
        country,
        sources: selectedSources,
      });
      setResult(data);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          "Search failed. Check that the backend is running.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-100 text-ink">
      <header className="border-b border-line bg-panel">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-5 sm:px-6 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-normal">Job Portal</h1>
            <p className="mt-1 text-sm text-slate-600">
              Multi-source search for roles across local and remote boards.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-sm text-slate-600">
            {providerSummary.length > 0 &&
              providerSummary.map((item) => (
                <span
                  key={item.source}
                  className="rounded-full border border-line bg-slate-50 px-2.5 py-1"
                >
                  {item.source}: {item.count}
                </span>
              ))}
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-6xl gap-5 px-4 py-5 sm:px-6 lg:grid-cols-[320px_1fr]">
        <aside className="space-y-4">
          <form
            onSubmit={handleSubmit}
            className="rounded-lg border border-line bg-panel p-4 shadow-sm"
          >
            <div className="space-y-4">
              <label className="block">
                <span className="mb-1.5 block text-sm font-medium text-slate-700">
                  Keyword
                </span>
                <span className="relative block">
                  <Search
                    className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
                    aria-hidden="true"
                  />
                  <input
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    className="min-h-11 w-full rounded-lg border border-line bg-white py-2 pl-10 pr-3 text-sm outline-none transition focus:border-ocean focus:ring-2 focus:ring-blue-100"
                    placeholder="Role, skill, company"
                  />
                </span>
              </label>

              <label className="block">
                <span className="mb-1.5 block text-sm font-medium text-slate-700">
                  Location
                </span>
                <span className="relative block">
                  <MapPin
                    className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
                    aria-hidden="true"
                  />
                  <input
                    value={location}
                    onChange={(event) => setLocation(event.target.value)}
                    className="min-h-11 w-full rounded-lg border border-line bg-white py-2 pl-10 pr-3 text-sm outline-none transition focus:border-ocean focus:ring-2 focus:ring-blue-100"
                    placeholder="City, country, remote"
                  />
                </span>
              </label>

              <label className="block">
                <span className="mb-1.5 block text-sm font-medium text-slate-700">
                  Country
                </span>
                <select
                  value={country}
                  onChange={handleCountryChange}
                  className="min-h-11 w-full rounded-lg border border-line bg-white px-3 py-2 text-sm outline-none transition focus:border-ocean focus:ring-2 focus:ring-blue-100"
                >
                  {COUNTRIES.map((item) => (
                    <option key={`${item.code}-${item.label}`} value={item.code}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </label>

              <fieldset>
                <legend className="mb-2 text-sm font-medium text-slate-700">
                  Sources
                </legend>
                <div className="grid grid-cols-2 gap-2">
                  {PROVIDERS.map((provider) => {
                    const checked = selectedSources.includes(provider.key);
                    return (
                      <button
                        key={provider.key}
                        type="button"
                        onClick={() => toggleSource(provider.key)}
                        className={`min-h-10 rounded-lg border px-3 text-sm font-medium transition ${
                          checked
                            ? "border-ocean bg-blue-50 text-ocean"
                            : "border-line bg-white text-slate-600 hover:border-slate-300"
                        }`}
                        aria-pressed={checked}
                      >
                        {provider.label}
                      </button>
                    );
                  })}
                </div>
              </fieldset>

              <button
                type="submit"
                disabled={loading}
                className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg bg-ocean px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-ocean focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-70"
              >
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                ) : (
                  <Search className="h-4 w-4" aria-hidden="true" />
                )}
                Search
              </button>
            </div>
          </form>

          {result?.errors && Object.keys(result.errors).length > 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber">
              <div className="flex items-start gap-2">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                <div className="space-y-1">
                  {Object.entries(result.errors).map(([source, message]) => (
                    <p key={source}>
                      <span className="font-semibold">{source}</span>: {message}
                    </p>
                  ))}
                </div>
              </div>
            </div>
          )}
        </aside>

        <section className="space-y-4">
          <div className="flex min-h-10 flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-semibold">
              {result ? `${result.count} results` : "Results"}
            </h2>
            {result && (
              <p className="text-sm text-slate-600">
                {result.query || "Any role"} in {result.location || "any location"}
              </p>
            )}
          </div>

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              {error}
            </div>
          )}

          {!result && !error && (
            <div className="rounded-lg border border-dashed border-line bg-panel p-8 text-center text-sm text-slate-600">
              Search jobs by title, company, or keyword.
            </div>
          )}

          {result?.jobs?.length === 0 && (
            <div className="rounded-lg border border-line bg-panel p-8 text-center text-sm text-slate-600">
              No matching jobs found.
            </div>
          )}

          <div className="space-y-3">
            {result?.jobs?.map((job, index) => (
              <JobCard
                key={`${job.source}-${job.apply_url || job.source_url || index}`}
                job={job}
              />
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
