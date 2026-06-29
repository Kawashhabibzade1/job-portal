import {
  AlertCircle,
  BookOpen,
  Check,
  Clock3,
  ExternalLink,
  Loader2,
  MapPin,
  RefreshCw,
  Search,
  SearchCheck,
  Trash2,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { searchJobs } from "../api/jobs.js";
import JobCard from "../components/JobCard.jsx";

const PROVIDERS = [
  { key: "arbeitsagentur", label: "Arbeitsagentur", countries: ["de"] },
  { key: "arbeitnow", label: "Arbeitnow", countries: ["de"] },
  { key: "indeed", label: "Indeed", countries: ["de"], scraped: true },
  { key: "linkedin", label: "LinkedIn", countries: ["de"], scraped: true },
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
  { key: "northcyprus_cv", label: "NorthCyprus.cv", countries: ["tr"] },
  { key: "iskibris", label: "İş Kıbrıs", countries: ["tr"] },
  { key: "trnc_research", label: "TRNC Research", countries: ["tr"] },
];

const COUNTRIES = [
  { code: "de", label: "Germany" },
  { code: "at", label: "Austria" },
  { code: "ch", label: "Switzerland" },
  { code: "gb", label: "United Kingdom" },
  { code: "tr", label: "Northern Cyprus" },
];

const RESEARCH_SOURCES = ["northcyprus_cv", "iskibris", "trnc_research"];

const RESEARCH_PRESETS = [
  "Human IVF",
  "IVF laboratory",
  "Research assistant",
  "Biomedical",
];

const RESEARCH_PORTALS = [
  {
    name: "Eastern Mediterranean University",
    label: "Research Assistantships",
    location: "Famagusta",
    href: "https://grad.emu.edu.tr/en/fees/research-assistantships-opportunities",
  },
  {
    name: "Near East University",
    label: "Academic Careers",
    location: "Nicosia",
    href: "https://neu.edu.tr/career/career-opportunities/?lang=en",
  },
  {
    name: "Cyprus International University",
    label: "Career Application",
    location: "Nicosia",
    href: "https://intranet.ciu.edu.tr/hr/career-apply",
  },
];

const SAVED_SEARCHES_KEY = "jobPortal.savedSearches.v1";
const MAX_SAVED_SEARCHES = 12;

function normalizeSearchText(value) {
  return value.trim().replace(/\s+/g, " ");
}

function searchKey({ query, location, country, sources, includeRemote }) {
  return JSON.stringify({
    query: normalizeSearchText(query).toLowerCase(),
    location: normalizeSearchText(location).toLowerCase(),
    country,
    sources: [...sources].sort(),
    includeRemote,
  });
}

function searchLabel({ query, location }) {
  const category = normalizeSearchText(query) || "All jobs";
  const place = normalizeSearchText(location);
  return place ? `${category} - ${place}` : category;
}

function readSavedSearches() {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(SAVED_SEARCHES_KEY) || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeSavedSearches(searches) {
  window.localStorage.setItem(SAVED_SEARCHES_KEY, JSON.stringify(searches));
}

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
  const [refreshCooldown, setRefreshCooldown] = useState(0);
  const [savedSearches, setSavedSearches] = useState([]);
  const [loadedFromSaved, setLoadedFromSaved] = useState(false);
  const [activeTab, setActiveTab] = useState("results");

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
    setSavedSearches(readSavedSearches());
  }, []);

  useEffect(() => {
    setSelectedSources((current) => {
      const availableSourceKeys = availableProviders.map((provider) => provider.key);
      const next = current.filter((source) => availableSourceKeys.includes(source));
      return next.length ? next : availableSourceKeys;
    });
  }, [availableProviders]);

  useEffect(() => {
    if (refreshCooldown <= 0) return undefined;
    const timer = window.setTimeout(() => {
      setRefreshCooldown((current) => Math.max(0, current - 1));
    }, 1000);
    return () => window.clearTimeout(timer);
  }, [refreshCooldown]);

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

  function saveSearchResult(data, overrideDescriptor = null) {
    if (!data?.jobs?.length) return;

    const descriptor =
      overrideDescriptor || {
        query,
        location,
        country: countryParam,
        sources: selectedSources,
        includeRemote,
      };
    const savedSearch = {
      key: searchKey(descriptor),
      label: searchLabel(descriptor),
      category: normalizeSearchText(descriptor.query) || "All jobs",
      location: normalizeSearchText(descriptor.location),
      country: descriptor.country,
      sources: descriptor.sources,
      includeRemote: descriptor.includeRemote,
      result: data,
      savedAt: new Date().toISOString(),
    };

    const next = [
      savedSearch,
      ...savedSearches.filter((item) => item.key !== savedSearch.key),
    ].slice(0, MAX_SAVED_SEARCHES);
    setSavedSearches(next);
    writeSavedSearches(next);
  }

  function loadSavedSearch(savedSearch) {
    setQuery(savedSearch.category === "All jobs" ? "" : savedSearch.category);
    setLocation(savedSearch.location || "");
    setIncludeRemote(Boolean(savedSearch.includeRemote));
    setSelectedSources(savedSearch.sources?.length ? savedSearch.sources : selectedSources);
    setSelectedCountries(
      savedSearch.country === "all"
        ? COUNTRIES.map((item) => item.code)
        : savedSearch.country.split(",").filter(Boolean),
    );
    setResult(savedSearch.result);
    setLoadedFromSaved(true);
    setActiveTab("results");
    setError("");
  }

  function removeSavedSearch(key) {
    const next = savedSearches.filter((item) => item.key !== key);
    setSavedSearches(next);
    writeSavedSearches(next);
  }

  async function runSearch({ refresh = false } = {}) {
    setLoading(true);
    setError("");
    setLoadedFromSaved(false);
    setActiveTab("results");

    try {
      const data = await searchJobs({
        query,
        location,
        country: countryParam,
        sources: selectedSources,
        includeRemote,
        refresh,
      });
      setResult(data);
      saveSearchResult(data);
      if (refresh) setRefreshCooldown(30);
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

  async function handleSubmit(event) {
    event.preventDefault();
    await runSearch();
  }

  function applyResearchPreset(nextQuery) {
    setQuery(nextQuery);
    setLocation("");
    setSelectedCountries(["tr"]);
    setSelectedSources(RESEARCH_SOURCES);
    setIncludeRemote(false);
    setActiveTab("results");
  }

  async function runResearchPreset(nextQuery) {
    applyResearchPreset(nextQuery);
    setLoading(true);
    setError("");
    setLoadedFromSaved(false);

    try {
      const data = await searchJobs({
        query: nextQuery,
        location: "",
        country: "tr",
        sources: RESEARCH_SOURCES,
        includeRemote: false,
        refresh: false,
      });
      setResult(data);
      saveSearchResult(data, {
        query: nextQuery,
        location: "",
        country: "tr",
        sources: RESEARCH_SOURCES,
        includeRemote: false,
      });
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

              <button
                type="button"
                disabled={loading || refreshCooldown > 0}
                onClick={() => runSearch({ refresh: true })}
                className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg border border-line bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-300 focus:outline-none focus:ring-2 focus:ring-ocean focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                ) : (
                  <RefreshCw className="h-4 w-4" aria-hidden="true" />
                )}
                {refreshCooldown > 0 ? `Refresh in ${refreshCooldown}s` : "Refresh"}
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
          <div className="rounded-lg border border-line bg-panel p-1 shadow-sm">
            <div className="grid grid-cols-3 gap-1">
              {[
                { key: "results", label: "Results", icon: SearchCheck },
                { key: "saved", label: "Saved", icon: Clock3 },
                { key: "research", label: "Research", icon: BookOpen },
              ].map((tab) => {
                const Icon = tab.icon;
                const selected = activeTab === tab.key;
                return (
                  <button
                    key={tab.key}
                    type="button"
                    onClick={() => setActiveTab(tab.key)}
                    className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-md px-3 text-sm font-semibold transition ${
                      selected
                        ? "bg-ink text-white shadow-sm"
                        : "text-slate-600 hover:bg-slate-100 hover:text-ink"
                    }`}
                    aria-pressed={selected}
                  >
                    <Icon className="h-4 w-4" aria-hidden="true" />
                    {tab.label}
                  </button>
                );
              })}
            </div>
          </div>

          {activeTab === "saved" && (
            <div className="rounded-lg border border-line bg-panel p-4 shadow-sm">
              <div className="mb-3 flex min-h-10 flex-wrap items-center justify-between gap-3">
                <h2 className="text-lg font-semibold">Saved searches</h2>
                <span className="rounded-full border border-teal-200 bg-teal-50 px-2.5 py-1 text-xs font-semibold text-mint">
                  Local cache
                </span>
              </div>

              {savedSearches.length === 0 ? (
                <div className="rounded-lg border border-dashed border-line bg-slate-50 p-8 text-center text-sm text-slate-600">
                  Saved searches will appear here after a search returns jobs.
                </div>
              ) : (
                <div className="grid gap-3 md:grid-cols-2">
                  {savedSearches.map((item) => (
                    <div
                      key={item.key}
                      className="rounded-lg border border-line bg-white p-3 shadow-sm"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <button
                          type="button"
                          onClick={() => loadSavedSearch(item)}
                          className="min-w-0 flex-1 text-left"
                        >
                          <span className="block truncate text-sm font-semibold text-ink">
                            {item.label}
                          </span>
                          <span className="mt-1 flex items-center gap-1 text-xs text-slate-500">
                            <Clock3 className="h-3.5 w-3.5" aria-hidden="true" />
                            {item.result?.count || 0} jobs saved
                          </span>
                        </button>
                        <button
                          type="button"
                          onClick={() => removeSavedSearch(item.key)}
                          className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-slate-500 transition hover:bg-slate-100 hover:text-red-700 focus:outline-none focus:ring-2 focus:ring-ocean"
                          aria-label={`Remove ${item.label}`}
                        >
                          <Trash2 className="h-4 w-4" aria-hidden="true" />
                        </button>
                      </div>
                      <button
                        type="button"
                        onClick={() => loadSavedSearch(item)}
                        className="mt-3 inline-flex min-h-9 w-full items-center justify-center gap-2 rounded-lg bg-ink px-3 text-sm font-semibold text-white transition hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-ocean focus:ring-offset-2"
                      >
                        <SearchCheck className="h-4 w-4" aria-hidden="true" />
                        Open
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === "research" && (
            <div className="space-y-4">
              <div className="rounded-lg border border-line bg-panel p-4 shadow-sm">
                <div className="flex min-h-10 flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-semibold">Northern Cyprus Research</h2>
                    <p className="mt-1 text-sm text-slate-600">
                      Academic, laboratory, biomedical, and IVF-focused sources.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => runResearchPreset("Human IVF")}
                    disabled={loading}
                    className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-ocean px-3 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-70"
                  >
                    {loading ? (
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                    ) : (
                      <Search className="h-4 w-4" aria-hidden="true" />
                    )}
                    Search IVF
                  </button>
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                  {RESEARCH_PRESETS.map((preset) => (
                    <button
                      key={preset}
                      type="button"
                      onClick={() => runResearchPreset(preset)}
                      disabled={loading}
                      className="inline-flex min-h-9 items-center justify-center rounded-full border border-line bg-white px-3 text-sm font-medium text-slate-700 transition hover:border-ocean hover:text-ocean disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {preset}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                {RESEARCH_PORTALS.map((portal) => (
                  <article
                    key={portal.href}
                    className="rounded-lg border border-line bg-panel p-4 shadow-sm"
                  >
                    <div className="space-y-2">
                      <h3 className="text-base font-semibold leading-snug text-ink">
                        {portal.name}
                      </h3>
                      <p className="text-sm font-medium text-slate-600">{portal.label}</p>
                      <p className="inline-flex items-center gap-1.5 text-sm text-slate-600">
                        <MapPin className="h-4 w-4" aria-hidden="true" />
                        {portal.location}
                      </p>
                    </div>
                    <a
                      href={portal.href}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-4 inline-flex min-h-10 w-full items-center justify-center gap-2 rounded-lg border border-line bg-white px-3 text-sm font-semibold text-slate-700 transition hover:border-slate-300 focus:outline-none focus:ring-2 focus:ring-ocean focus:ring-offset-2"
                    >
                      Open portal
                      <ExternalLink className="h-4 w-4" aria-hidden="true" />
                    </a>
                  </article>
                ))}
              </div>
            </div>
          )}

          {activeTab === "results" && (
            <>
          <div className="flex min-h-10 flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-semibold">
              {result ? `${result.count} results` : "Results"}
            </h2>
            <div className="flex flex-wrap items-center gap-2 text-sm text-slate-600">
              {loadedFromSaved && (
                <span className="rounded-full border border-teal-200 bg-teal-50 px-2.5 py-1 text-xs font-semibold text-mint">
                  Saved result
                </span>
              )}
              {result && (
                <p>
                  {result.query || "Any role"} in {result.location || "any location"}
                </p>
              )}
            </div>
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
            </>
          )}
        </section>
      </div>
    </main>
  );
}
