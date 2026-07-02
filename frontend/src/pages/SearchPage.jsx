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
  { key: "linkedin", label: "LinkedIn", countries: ["de", "at", "ch", "gb", "be", "nl", "tr"], scraped: true },
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
  { key: "english_jobs_be", label: "EnglishJobs.be", countries: ["be"] },
  { key: "stepstone_be", label: "StepStone Belgium", countries: ["be"] },
  { key: "iamexpat_nl", label: "IamExpat Netherlands", countries: ["nl"] },
  { key: "undutchables_nl", label: "Undutchables", countries: ["nl"] },
  { key: "bcf_career_nl", label: "BCF Career", countries: ["nl"] },
  { key: "leiden_bioscience_nl", label: "Leiden Bio Science Park", countries: ["nl"] },
  { key: "academictransfer_nl", label: "AcademicTransfer", countries: ["nl"] },
  { key: "northcyprus_cv", label: "NorthCyprus.cv", countries: ["tr"] },
  { key: "iskibris", label: "İş Kıbrıs", countries: ["tr"] },
  { key: "trnc_research", label: "TRNC Research", countries: ["tr"] },
];

const COUNTRIES = [
  { code: "de", label: "Germany" },
  { code: "at", label: "Austria" },
  { code: "ch", label: "Switzerland" },
  { code: "gb", label: "United Kingdom" },
  { code: "be", label: "Belgium" },
  { code: "nl", label: "Netherlands" },
  { code: "tr", label: "Northern Cyprus" },
];

const RESEARCH_SOURCES = ["northcyprus_cv", "iskibris", "trnc_research"];
const RESEARCH_PRESETS = ["Human IVF", "IVF laboratory", "Research assistant", "Biomedical"];
const RESEARCH_PORTALS = [
  { name: "Eastern Mediterranean University", label: "Research Assistantships", location: "Famagusta", href: "https://grad.emu.edu.tr/en/fees/research-assistantships-opportunities" },
  { name: "Near East University", label: "Academic Careers", location: "Nicosia", href: "https://neu.edu.tr/career/career-opportunities/?lang=en" },
  { name: "Cyprus International University", label: "Career Application", location: "Nicosia", href: "https://intranet.ciu.edu.tr/hr/career-apply" },
];

function providerKeysForCountries(countryCodes) {
  return PROVIDERS
    .filter((provider) => provider.countries.some((country) => countryCodes.includes(country)))
    .map((provider) => provider.key);
}

const SAVED_SEARCHES_KEY = "jobPortal.savedSearches.v1";
const MAX_SAVED_SEARCHES = 12;

function normalizeSearchText(value) { return value.trim().replace(/\s+/g, " "); }

function searchKey({ query, location, country, sources, includeRemote }) {
  return JSON.stringify({ query: normalizeSearchText(query).toLowerCase(), location: normalizeSearchText(location).toLowerCase(), country, sources: [...sources].sort(), includeRemote });
}

function searchLabel({ query, location }) {
  const category = normalizeSearchText(query) || "All jobs";
  const place = normalizeSearchText(location);
  return place ? `${category} – ${place}` : category;
}

function readSavedSearches() {
  try { const parsed = JSON.parse(window.localStorage.getItem(SAVED_SEARCHES_KEY) || "[]"); return Array.isArray(parsed) ? parsed : []; }
  catch { return []; }
}

function writeSavedSearches(searches) { window.localStorage.setItem(SAVED_SEARCHES_KEY, JSON.stringify(searches)); }

/* SVG Logo */
function Logo({ className = "h-8 w-8" }) {
  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden="true">
      <defs><linearGradient id="sLogo" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stopColor="#6366f1" /><stop offset="50%" stopColor="#8b5cf6" /><stop offset="100%" stopColor="#06b6d4" /></linearGradient></defs>
      <rect width="64" height="64" rx="14" fill="#0f172a" /><circle cx="32" cy="26" r="10" fill="url(#sLogo)" opacity="0.9" />
      <path d="M22 40c0-5.5 4.5-10 10-10s10 4.5 10 10" fill="none" stroke="url(#sLogo)" strokeWidth="3.5" strokeLinecap="round" />
      <path d="M26 50h12" stroke="#06b6d4" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

export default function SearchPage() {
  const [query, setQuery] = useState("developer");
  const [location, setLocation] = useState("");
  const [selectedCountries, setSelectedCountries] = useState(["de"]);
  const [includeRemote, setIncludeRemote] = useState(false);
  const [selectedSources, setSelectedSources] = useState(PROVIDERS.map((p) => p.key));
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [refreshCooldown, setRefreshCooldown] = useState(0);
  const [savedSearches, setSavedSearches] = useState([]);
  const [loadedFromSaved, setLoadedFromSaved] = useState(false);
  const [activeTab, setActiveTab] = useState("results");

  const providerSummary = useMemo(() => {
    if (!result?.sources) return [];
    return Object.entries(result.sources).map(([source, count]) => ({ source, count }));
  }, [result]);

  const allCountriesSelected = selectedCountries.length === COUNTRIES.length;
  const countryParam = allCountriesSelected ? "all" : selectedCountries.join(",");
  const availableProviders = useMemo(
    () => PROVIDERS.filter((p) => { if (p.remoteOnly && !includeRemote) return false; return p.countries.some((c) => selectedCountries.includes(c)); }),
    [includeRemote, selectedCountries],
  );

  useEffect(() => { setSavedSearches(readSavedSearches()); }, []);
  useEffect(() => {
    setSelectedSources((c) => { const keys = availableProviders.map((p) => p.key); const n = c.filter((s) => keys.includes(s)); return n.length ? n : keys; });
  }, [availableProviders]);
  useEffect(() => {
    if (refreshCooldown <= 0) return undefined;
    const timer = window.setTimeout(() => { setRefreshCooldown((c) => Math.max(0, c - 1)); }, 1000);
    return () => window.clearTimeout(timer);
  }, [refreshCooldown]);

  function toggleSource(s) { setSelectedSources((c) => { if (c.includes(s)) { const n = c.filter((i) => i !== s); return n.length ? n : c; } return [...c, s]; }); }
  function toggleCountry(code) {
    setSelectedCountries((c) => {
      if (c.includes(code)) { const n = c.filter((i) => i !== code); return n.length ? n : c; }
      setSelectedSources((sources) => Array.from(new Set([...sources, ...providerKeysForCountries([code])])));
      return [...c, code];
    });
  }
  function toggleAllCountries() { setSelectedCountries(allCountriesSelected ? [COUNTRIES[0].code] : COUNTRIES.map((i) => i.code)); }

  function saveSearchResult(data, overrideDescriptor = null) {
    if (!data?.jobs?.length) return;
    const descriptor = overrideDescriptor || { query, location, country: countryParam, sources: selectedSources, includeRemote };
    const savedSearch = { key: searchKey(descriptor), label: searchLabel(descriptor), category: normalizeSearchText(descriptor.query) || "All jobs", location: normalizeSearchText(descriptor.location), country: descriptor.country, sources: descriptor.sources, includeRemote: descriptor.includeRemote, result: data, savedAt: new Date().toISOString() };
    const next = [savedSearch, ...savedSearches.filter((i) => i.key !== savedSearch.key)].slice(0, MAX_SAVED_SEARCHES);
    setSavedSearches(next); writeSavedSearches(next);
  }

  function loadSavedSearch(s) {
    setQuery(s.category === "All jobs" ? "" : s.category); setLocation(s.location || ""); setIncludeRemote(Boolean(s.includeRemote));
    setSelectedSources(s.sources?.length ? s.sources : selectedSources);
    setSelectedCountries(s.country === "all" ? COUNTRIES.map((i) => i.code) : s.country.split(",").filter(Boolean));
    setResult(s.result); setLoadedFromSaved(true); setActiveTab("results"); setError("");
  }

  function removeSavedSearch(key) { const next = savedSearches.filter((i) => i.key !== key); setSavedSearches(next); writeSavedSearches(next); }

  async function runSearch({ refresh = false } = {}) {
    setLoading(true); setError(""); setLoadedFromSaved(false); setActiveTab("results");
    try {
      const data = await searchJobs({ query, location, country: countryParam, sources: selectedSources, includeRemote, refresh });
      setResult(data); saveSearchResult(data); if (refresh) setRefreshCooldown(30);
    } catch (err) { setError(err.response?.data?.detail || err.message || "Search failed."); }
    finally { setLoading(false); }
  }

  async function handleSubmit(event) { event.preventDefault(); await runSearch(); }

  function applyResearchPreset(q) { setQuery(q); setLocation(""); setSelectedCountries(["tr"]); setSelectedSources(RESEARCH_SOURCES); setIncludeRemote(false); setActiveTab("results"); }

  async function runResearchPreset(q) {
    applyResearchPreset(q); setLoading(true); setError(""); setLoadedFromSaved(false);
    try {
      const data = await searchJobs({ query: q, location: "", country: "tr", sources: RESEARCH_SOURCES, includeRemote: false, refresh: false });
      setResult(data); saveSearchResult(data, { query: q, location: "", country: "tr", sources: RESEARCH_SOURCES, includeRemote: false });
    } catch (err) { setError(err.response?.data?.detail || err.message || "Search failed."); }
    finally { setLoading(false); }
  }

  return (
    <main className="relative min-h-screen bg-navy-950 text-ink">
      {/* Background orbs */}
      <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
        <div className="orb orb-1 animate-float-slow" />
        <div className="orb orb-2 animate-float-medium" />
        <div className="orb orb-3 animate-float-fast" />
      </div>

      <header className="glass sticky top-0 z-30 border-b border-line">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div className="flex items-center gap-3">
            <Logo className="h-9 w-9" />
            <div>
              <h1 className="text-lg font-bold tracking-tight sm:text-xl">
                <span className="text-gradient">YourJob</span>{" "}
                <span className="text-ink">YourChoice</span>
              </h1>
              <p className="text-xs text-ink-faint">Multi-source job search</p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-sm text-ink-faint">
            {providerSummary.length > 0 && providerSummary.map((item) => (
              <span key={item.source} className="chip chip-inactive">{item.source}: {item.count}</span>
            ))}
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-6xl gap-5 px-4 py-5 sm:px-6 lg:grid-cols-[320px_1fr]">
        <aside className="space-y-4">
          <form onSubmit={handleSubmit} className="glass rounded-xl p-4">
            <div className="space-y-4">
              <label className="block">
                <span className="mb-1.5 block text-sm font-medium text-ink-muted">Keyword</span>
                <span className="relative block">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-faint" aria-hidden="true" />
                  <input value={query} onChange={(e) => setQuery(e.target.value)}
                    className="glass-input min-h-11 w-full rounded-xl py-2 pl-10 pr-3 text-sm" placeholder="Role, skill, company" />
                </span>
              </label>

              <label className="block">
                <span className="mb-1.5 block text-sm font-medium text-ink-muted">Location</span>
                <span className="relative block">
                  <MapPin className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-faint" aria-hidden="true" />
                  <input value={location} onChange={(e) => setLocation(e.target.value)}
                    className="glass-input min-h-11 w-full rounded-xl py-2 pl-10 pr-3 text-sm" placeholder="Optional city" />
                </span>
              </label>

              <fieldset>
                <legend className="mb-2 text-sm font-medium text-ink-muted">Countries</legend>
                <div className="grid grid-cols-2 gap-2">
                  <button type="button" onClick={toggleAllCountries}
                    className={`col-span-2 chip ${allCountriesSelected ? "chip-active" : "chip-inactive"} min-h-10 cursor-pointer justify-center`}
                    aria-pressed={allCountriesSelected}>
                    {allCountriesSelected && <Check className="h-4 w-4" />} All countries
                  </button>
                  {COUNTRIES.map((item) => {
                    const checked = selectedCountries.includes(item.code);
                    return (
                      <button key={item.code} type="button" onClick={() => toggleCountry(item.code)}
                        className={`chip ${checked ? "chip-active" : "chip-inactive"} min-h-10 cursor-pointer justify-center`}
                        aria-pressed={checked}>
                        {checked && <Check className="h-4 w-4" />} {item.label}
                      </button>
                    );
                  })}
                </div>
              </fieldset>

              <label className="glass-light flex min-h-11 items-center justify-between gap-3 rounded-xl px-3 py-2 text-sm text-ink-muted">
                <span className="font-medium">Include remote jobs</span>
                <input type="checkbox" checked={includeRemote} onChange={(e) => setIncludeRemote(e.target.checked)}
                  className="h-4 w-4 rounded border-line accent-ocean" />
              </label>

              <fieldset>
                <legend className="mb-2 text-sm font-medium text-ink-muted">Sources</legend>
                <div className="grid grid-cols-2 gap-2">
                  {availableProviders.length === 0 && (
                    <p className="col-span-2 glass-light rounded-xl px-3 py-2 text-sm text-ink-faint">No source for selected country.</p>
                  )}
                  {availableProviders.map((p) => {
                    const checked = selectedSources.includes(p.key);
                    return (
                      <button key={p.key} type="button" onClick={() => toggleSource(p.key)}
                        className={`chip ${checked ? "chip-active" : "chip-inactive"} min-h-10 cursor-pointer justify-center`}
                        aria-pressed={checked}>{p.label}</button>
                    );
                  })}
                </div>
              </fieldset>

              <button type="submit" disabled={loading} className="btn-primary w-full">
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />} Search
              </button>
              <button type="button" disabled={loading || refreshCooldown > 0} onClick={() => runSearch({ refresh: true })} className="btn-secondary w-full">
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                {refreshCooldown > 0 ? `Refresh in ${refreshCooldown}s` : "Refresh"}
              </button>
            </div>
          </form>

          {result?.errors && Object.keys(result.errors).length > 0 && (
            <div className="rounded-xl border border-amber/30 bg-amber/10 p-4 text-sm text-amber">
              <div className="flex items-start gap-2">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <div className="space-y-1">
                  {Object.entries(result.errors).map(([source, message]) => (
                    <p key={source}><span className="font-semibold">{source}</span>: {message}</p>
                  ))}
                </div>
              </div>
            </div>
          )}
        </aside>

        <section className="space-y-4">
          {/* Tabs */}
          <div className="glass rounded-xl p-1">
            <div className="grid grid-cols-3 gap-1">
              {[
                { key: "results", label: "Results", icon: SearchCheck },
                { key: "saved", label: "Saved", icon: Clock3 },
                { key: "research", label: "Research", icon: BookOpen },
              ].map((tab) => {
                const Icon = tab.icon;
                const selected = activeTab === tab.key;
                return (
                  <button key={tab.key} type="button" onClick={() => setActiveTab(tab.key)}
                    className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-lg px-3 text-sm font-semibold transition ${
                      selected ? "bg-gradient-to-r from-ocean/20 to-cyan/10 text-ocean-light shadow-sm" : "text-ink-faint hover:bg-navy-800 hover:text-ink"
                    }`} aria-pressed={selected}>
                    <Icon className="h-4 w-4" /> {tab.label}
                  </button>
                );
              })}
            </div>
          </div>

          {activeTab === "saved" && (
            <div className="glass rounded-xl p-4 view-enter">
              <div className="mb-3 flex min-h-10 flex-wrap items-center justify-between gap-3">
                <h2 className="text-lg font-semibold text-ink">Saved searches</h2>
                <span className="chip chip-active">Local cache</span>
              </div>
              {savedSearches.length === 0 ? (
                <div className="glass-light rounded-xl border border-dashed border-line p-8 text-center text-sm text-ink-faint">
                  Saved searches will appear here after a search returns jobs.
                </div>
              ) : (
                <div className="stagger grid gap-3 sm:grid-cols-2">
                  {savedSearches.map((item) => (
                    <div key={item.key} className="glass-light glow-border rounded-xl p-3">
                      <div className="flex items-start justify-between gap-3">
                        <button type="button" onClick={() => loadSavedSearch(item)} className="min-w-0 flex-1 text-left">
                          <span className="block truncate text-sm font-semibold text-ink">{item.label}</span>
                          <span className="mt-1 flex items-center gap-1 text-xs text-ink-faint">
                            <Clock3 className="h-3.5 w-3.5" /> {item.result?.count || 0} jobs saved
                          </span>
                        </button>
                        <button type="button" onClick={() => removeSavedSearch(item.key)}
                          className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-ink-faint transition hover:bg-rose/10 hover:text-rose" aria-label={`Remove ${item.label}`}>
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                      <button type="button" onClick={() => loadSavedSearch(item)} className="btn-primary mt-3 w-full">
                        <SearchCheck className="h-4 w-4" /> Open
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === "research" && (
            <div className="view-enter space-y-4">
              <div className="glass rounded-xl p-4">
                <div className="flex min-h-10 flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-semibold text-ink">Northern Cyprus Research</h2>
                    <p className="mt-1 text-sm text-ink-faint">Academic, laboratory, biomedical, and IVF-focused sources.</p>
                  </div>
                  <button type="button" onClick={() => runResearchPreset("Human IVF")} disabled={loading} className="btn-primary">
                    {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />} Search IVF
                  </button>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  {RESEARCH_PRESETS.map((preset) => (
                    <button key={preset} type="button" onClick={() => runResearchPreset(preset)} disabled={loading}
                      className="chip chip-inactive cursor-pointer transition hover:border-ocean/40 hover:text-ocean-light">{preset}</button>
                  ))}
                </div>
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                {RESEARCH_PORTALS.map((portal) => (
                  <article key={portal.href} className="glass glow-border rounded-xl p-4">
                    <div className="space-y-2">
                      <h3 className="text-base font-semibold leading-snug text-ink">{portal.name}</h3>
                      <p className="text-sm font-medium text-ink-muted">{portal.label}</p>
                      <p className="inline-flex items-center gap-1.5 text-sm text-ink-faint">
                        <MapPin className="h-4 w-4" /> {portal.location}
                      </p>
                    </div>
                    <a href={portal.href} target="_blank" rel="noreferrer" className="btn-secondary mt-4 w-full">
                      Open portal <ExternalLink className="h-4 w-4" />
                    </a>
                  </article>
                ))}
              </div>
            </div>
          )}

          {activeTab === "results" && (
            <div className="view-enter">
              <div className="flex min-h-10 flex-wrap items-center justify-between gap-3">
                <h2 className="text-lg font-semibold text-ink">{result ? `${result.count} results` : "Results"}</h2>
                <div className="flex flex-wrap items-center gap-2 text-sm text-ink-faint">
                  {loadedFromSaved && <span className="chip chip-active">Saved result</span>}
                  {result && <p>{result.query || "Any role"} in {result.location || "any location"}</p>}
                </div>
              </div>

              {result?.search_queries?.length > 1 && (
                <div className="mt-3 glass-light rounded-xl p-3 text-sm text-ink-muted">
                  <span className="font-medium text-ink">Smart search used:</span>{" "}
                  {result.search_queries.slice(0, 6).join(", ")}{result.search_queries.length > 6 ? "..." : ""}
                </div>
              )}

              {result?.ai_filter_note && (
                <div className="mt-3 rounded-xl border border-mint/30 bg-mint/10 p-3 text-sm text-mint">{result.ai_filter_note}</div>
              )}

              {error && <div className="mt-3 rounded-xl border border-rose/30 bg-rose/10 p-4 text-sm text-rose">{error}</div>}

              {!result && !error && (
                <div className="mt-4 glass rounded-xl border border-dashed border-line p-8 text-center text-sm text-ink-faint">
                  Search jobs by title, company, or keyword.
                </div>
              )}

              {result?.jobs?.length === 0 && (
                <div className="mt-4 glass rounded-xl p-8 text-center text-sm text-ink-faint">No matching jobs found.</div>
              )}

              <div className="stagger mt-4 space-y-3">
                {result?.jobs?.map((job, index) => (
                  <JobCard key={`${job.source}-${job.apply_url || job.source_url || index}`} job={job} />
                ))}
              </div>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
