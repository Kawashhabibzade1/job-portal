import { AlertCircle, Check, Loader2, MapPin, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { searchJobs } from "../api/jobs.js";
import JobCard from "../components/JobCard.jsx";

const PROVIDERS = [
  { key: "arbeitsagentur", label: "Arbeitsagentur", countries: ["de"] },
  { key: "arbeitnow", label: "Arbeitnow", countries: ["de"] },
  { key: "karriere_at", label: "Karriere.at", countries: ["at"] },
  { key: "jobs_ch", label: "Jobs.ch", countries: ["ch"] },
  { key: "jobup_ch", label: "Jobup.ch", countries: ["ch"] },
  { key: "reed_uk", label: "Reed UK", countries: ["gb"] },
  { key: "nhs_jobs", label: "NHS Jobs", countries: ["gb"] },
  { key: "healthjobs_uk", label: "HealthJobsUK", countries: ["gb"] },
  { key: "jobs_ac_uk", label: "Jobs.ac.uk", countries: ["gb"] },
  { key: "new_scientist_jobs", label: "New Scientist Jobs", countries: ["gb"] },
  { key: "ifs_uk", label: "IFS", countries: ["gb"] },
  { key: "arcs_community", label: "ARCS Community", countries: ["gb"] },
];

const COUNTRIES = [
  { code: "de", label: "Germany" },
  { code: "at", label: "Austria" },
  { code: "ch", label: "Switzerland" },
  { code: "gb", label: "United Kingdom" },
  { code: "tr", label: "Northern Cyprus" },
];

export default function SearchPage() {
  const [query, setQuery] = useState("developer");
  const [location, setLocation] = useState("");
  const [selectedCountries, setSelectedCountries] = useState(["de"]);
  const [includeRemote, setIncludeRemote] = useState(false);
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

  const allCountriesSelected = selectedCountries.length === COUNTRIES.length;
  const countryParam = allCountriesSelected ? "all" : selectedCountries.join(",");
  const availableProviders = useMemo(
    () =>
      PROVIDERS.filter((provider) => {
        if (provider.remoteOnly && !includeRemote) return false;
        return provider.countries.some((countryCode) =>
          selectedCountries.includes(countryCode),
        );
      }),
    [includeRemote, selectedCountries],
  );

  useEffect(() => {
    setSelectedSources((current) => {
      const availableSourceKeys = availableProviders.map((provider) => provider.key);
      const next = current.filter((source) => availableSourceKeys.includes(source));
      return next.length ? next : availableSourceKeys;
    });
  }, [availableProviders]);

  function toggleSource(source) {
    setSelectedSources((current) => {
      if (current.includes(source)) {
        const next = current.filter((item) => item !== source);
        return next.length ? next : current;
      }
      return [...current, source];
    });
  }

  function toggleCountry(countryCode) {
    setSelectedCountries((current) => {
      if (current.includes(countryCode)) {
        const next = current.filter((item) => item !== countryCode);
        return next.length ? next : current;
      }
      return [...current, countryCode];
    });
  }

  function toggleAllCountries() {
    setSelectedCountries(
      allCountriesSelected ? [COUNTRIES[0].code] : COUNTRIES.map((item) => item.code),
    );
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const data = await searchJobs({
        query,
        location,
        country: countryParam,
        sources: selectedSources,
        includeRemote,
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
                    placeholder="Optional city"
                  />
                </span>
              </label>

              <fieldset>
                <legend className="mb-2 text-sm font-medium text-slate-700">
                  Countries
                </legend>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={toggleAllCountries}
                    className={`col-span-2 inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border px-3 text-sm font-medium transition ${
                      allCountriesSelected
                        ? "border-ocean bg-blue-50 text-ocean"
                        : "border-line bg-white text-slate-600 hover:border-slate-300"
                    }`}
                    aria-pressed={allCountriesSelected}
                  >
                    {allCountriesSelected && <Check className="h-4 w-4" aria-hidden="true" />}
                    All countries
                  </button>
                  {COUNTRIES.map((item) => {
                    const checked = selectedCountries.includes(item.code);
                    return (
                      <button
                        key={item.code}
                        type="button"
                        onClick={() => toggleCountry(item.code)}
                        className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border px-3 text-sm font-medium transition ${
                          checked
                            ? "border-ocean bg-blue-50 text-ocean"
                            : "border-line bg-white text-slate-600 hover:border-slate-300"
                        }`}
                        aria-pressed={checked}
                      >
                        {checked && <Check className="h-4 w-4" aria-hidden="true" />}
                        {item.label}
                      </button>
                    );
                  })}
                </div>
              </fieldset>

              <label className="flex min-h-11 items-center justify-between gap-3 rounded-lg border border-line bg-white px-3 py-2 text-sm text-slate-700">
                <span className="font-medium">Include remote jobs</span>
                <input
                  type="checkbox"
                  checked={includeRemote}
                  onChange={(event) => setIncludeRemote(event.target.checked)}
                  className="h-4 w-4 rounded border-line text-ocean focus:ring-ocean"
                />
              </label>

              <fieldset>
                <legend className="mb-2 text-sm font-medium text-slate-700">
                  Sources
                </legend>
                <div className="grid grid-cols-2 gap-2">
                  {availableProviders.length === 0 && (
                    <p className="col-span-2 rounded-lg border border-line bg-slate-50 px-3 py-2 text-sm text-slate-600">
                      No local source configured for the selected country.
                    </p>
                  )}
                  {availableProviders.map((provider) => {
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
