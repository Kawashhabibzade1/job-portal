import {
  BriefcaseBusiness,
  Check,
  CheckCircle2,
  ChevronDown,
  Clock3,
  FileText,
  FolderKanban,
  Loader2,
  MapPin,
  MessageSquareText,
  Navigation,
  PenLine,
  Save,
  Search,
  Send,
  Settings,
  Sparkles,
  Trash2,
  Upload,
  UserRound,
  Menu,
  X,
  ArrowRight,
  Map,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import {
  createApplication,
  createApplicationPackage,
  createCoverLetter,
  exportCoverLetter,
  buildRoadmap,
  generateArtifactRoadmap,
  generateProfileSummary,
  getCvSuggestions,
  getLlmStatus,
  getProfile,
  improveCv,
  analyzeRejection,
  listApplications,
  listDocuments,
  listGeneratedFiles,
  matchJobs,
  organizePdf,
  prepareApplyAutomation,
  searchJobs,
  sendChatMessage,
  saveLlmSettings,
  streamChatMessage,
  updateApplication,
  updateDocument,
  updateProfile,
  uploadDocument,
} from "./api/jobs.js";
import JobCard from "./components/JobCard.jsx";

const tabs = [
  { key: "chat", label: "Chat", icon: MessageSquareText },
  { key: "jobs", label: "Jobs", icon: BriefcaseBusiness },
  { key: "profile", label: "Profile", icon: UserRound },
  { key: "documents", label: "Docs", icon: FileText },
  { key: "applications", label: "Tracker", icon: FolderKanban },
];

const PROVIDERS = [
  { key: "arbeitsagentur", label: "Arbeitsagentur", countries: ["de"] },
  { key: "arbeitnow", label: "Arbeitnow", countries: ["de"] },
  { key: "indeed", label: "Indeed", countries: ["de"] },
  { key: "linkedin", label: "LinkedIn", countries: ["de", "at", "ch", "gb", "be", "nl", "tr"] },
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
  { key: "iskibris", label: "Is Kibris", countries: ["tr"] },
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

const AI_PROVIDERS = [
  { key: "gemini", label: "Gemini", icon: "✦" },
  { key: "grok", label: "Grok", icon: "⚡" },
  { key: "openai", label: "OpenAI", icon: "◎" },
];

const SEARCH_STEPS = [
  "Fetching jobs from sources…",
  "Deduplicating results…",
  "AI filtering & ranking…",
  "Finalising…",
];

function providerKeysForCountries(countryCodes) {
  return PROVIDERS
    .filter((provider) => provider.countries.some((country) => countryCodes.includes(country)))
    .map((provider) => provider.key);
}

function csvToList(value) {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

function listToCsv(value) {
  return Array.isArray(value) ? value.join(", ") : "";
}

function actionPayload(response, type) {
  return response.actions?.find((action) => action.type === type)?.data || null;
}

function downloadUrl(file) {
  const base = import.meta.env.VITE_API_BASE_URL || "";
  return `${base}/api/documents/generated/${file.id}/download`;
}

function newMessageId(role) {
  return `${role}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

const SAVED_SEARCHES_KEY = "jobPortal.savedSearches.v1";
const MAX_SAVED_SEARCHES = 8;

function searchKey({ query, location, country, sources, includeRemote }) {
  return [
    query || "",
    location || "",
    country || "",
    Array.isArray(sources) ? sources.join(",") : sources || "",
    includeRemote ? "remote" : "onsite",
  ].join("|").toLowerCase();
}

function searchLabel({ query, location }) {
  const role = (query || "All jobs").trim();
  const place = (location || "any location").trim();
  return `${role} in ${place}`;
}

function readSavedSearches() {
  try {
    return JSON.parse(window.localStorage.getItem(SAVED_SEARCHES_KEY) || "[]");
  } catch {
    return [];
  }
}

function writeSavedSearches(searches) {
  window.localStorage.setItem(SAVED_SEARCHES_KEY, JSON.stringify(searches));
}

function Logo({ className = "h-8 w-8" }) {
  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden="true">
      <defs>
        <linearGradient id="logoGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#2563eb" />
          <stop offset="100%" stopColor="#0891b2" />
        </linearGradient>
      </defs>
      <rect width="64" height="64" rx="14" fill="#ffffff" stroke="#dbe3ea" />
      <circle cx="32" cy="26" r="10" fill="url(#logoGrad)" opacity="0.9" />
      <path d="M22 40c0-5.5 4.5-10 10-10s10 4.5 10 10" fill="none" stroke="url(#logoGrad)" strokeWidth="3.5" strokeLinecap="round" />
      <path d="M26 50h12" stroke="#0891b2" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

function BackgroundWash() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="background-wash" />
    </div>
  );
}

function DebatePanel({ debate }) {
  if (!debate) return null;
  const opinions = [["Grok", debate.grok], ["Gemini", debate.gemini], ["Judge", debate.judge]];
  return (
    <div className="mt-3 space-y-2">
      {opinions.map(([label, opinion]) => (
        <div key={label} className="glass-light rounded-lg p-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs font-bold uppercase text-ink-muted">{label}</span>
            <span className="chip chip-active text-xs">
              {opinion.recommendation?.replaceAll("_", " ")} · {opinion.confidence}%
            </span>
          </div>
          <p className="mt-1 text-xs leading-5 text-ink-muted">{opinion.summary}</p>
          {opinion.status !== "ok" && (
            <p className="mt-1 text-xs font-medium text-amber">{opinion.status}: {opinion.error || "fallback used"}</p>
          )}
        </div>
      ))}
    </div>
  );
}

function CvSuggestionsPanel({ suggestions }) {
  if (!suggestions) return null;
  const priorityConfig = {
    high: { color: "text-rose-600", bg: "bg-rose-50 border-rose-200", label: "High" },
    medium: { color: "text-amber-600", bg: "bg-amber-50 border-amber-200", label: "Medium" },
    low: { color: "text-emerald-600", bg: "bg-emerald-50 border-emerald-200", label: "Low" },
  };
  const scoreColor = suggestions.overall_score >= 80 ? "text-emerald-600" : suggestions.overall_score >= 60 ? "text-amber-600" : "text-rose-600";
  return (
    <div className="space-y-4">
      <div className="glass rounded-xl p-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h3 className="text-lg font-bold text-ink">CV Analysis</h3>
            <p className="mt-1 text-sm text-ink-muted">{suggestions.summary}</p>
          </div>
          <div className="flex h-16 w-16 shrink-0 flex-col items-center justify-center rounded-full border-2 border-ocean/30 bg-ocean/5">
            <span className={`text-xl font-bold ${scoreColor}`}>{suggestions.overall_score}</span>
            <span className="text-xs text-ink-faint">score</span>
          </div>
        </div>
        <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-100">
          <div className="h-full rounded-full bg-gradient-to-r from-ocean to-cyan transition-all duration-700" style={{ width: `${suggestions.overall_score}%` }} />
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {suggestions.suggestions?.map((s, i) => {
          const cfg = priorityConfig[s.priority] || priorityConfig.medium;
          return (
            <div key={i} className={`rounded-xl border p-4 ${cfg.bg}`}>
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <PenLine className="h-4 w-4 text-ocean-light shrink-0" />
                  <span className="text-sm font-semibold text-ink">{s.section}</span>
                </div>
                <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase ${cfg.color} ${cfg.bg}`}>{cfg.label}</span>
              </div>
              <p className="mt-2 text-xs text-ink-muted leading-5">{s.issue}</p>
              <div className="mt-2 flex items-start gap-1.5">
                <ArrowRight className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ocean" />
                <p className="text-xs font-medium text-ink leading-5">{s.recommendation}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ArtifactRoadmapPanel({ roadmap }) {
  if (!roadmap) return null;
  const categoryColors = {
    Documents: "bg-blue-50 border-blue-200 text-blue-700",
    Immigration: "bg-purple-50 border-purple-200 text-purple-700",
    Language: "bg-emerald-50 border-emerald-200 text-emerald-700",
    Application: "bg-sky-50 border-sky-200 text-sky-700",
    "Follow-up": "bg-amber-50 border-amber-200 text-amber-700",
  };
  return (
    <div className="space-y-4">
      <div className="glass rounded-xl p-4">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-ocean to-cyan">
            <Map className="h-5 w-5 text-white" />
          </div>
          <div>
            <h3 className="font-bold text-ink">{roadmap.job_title}</h3>
            {roadmap.company && <p className="text-sm text-ink-muted">{roadmap.company}</p>}
            <div className="mt-1 flex flex-wrap gap-2">
              {roadmap.country && <span className="chip chip-active text-xs"><MapPin className="h-3 w-3" /> {roadmap.country.toUpperCase()}</span>}
              <span className="chip chip-inactive text-xs"><Clock3 className="h-3 w-3" /> ~{roadmap.timeline_weeks} weeks</span>
            </div>
          </div>
        </div>
      </div>
      <div className="space-y-2">
        <h4 className="text-sm font-semibold text-ink-muted px-1">Application Checklist</h4>
        {roadmap.steps?.map((step, i) => {
          const color = categoryColors[step.category] || "bg-slate-50 border-slate-200 text-slate-700";
          return (
            <div key={i} className="glass-light rounded-xl p-3 flex items-start gap-3">
              <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border text-xs font-bold ${color}`}>{i + 1}</div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-semibold text-ink">{step.title}</p>
                  <span className={`shrink-0 rounded-full border px-2 py-0 text-[10px] font-bold ${color}`}>{step.category}</span>
                  {!step.required && <span className="text-[10px] text-ink-faint">optional</span>}
                </div>
                <p className="mt-0.5 text-xs text-ink-muted leading-5">{step.description}</p>
                {step.link && (
                  <a href={step.link} target="_blank" rel="noreferrer" className="mt-1 inline-flex items-center gap-1 text-xs font-medium text-ocean hover:underline">
                    Apply here <ArrowRight className="h-3 w-3" />
                  </a>
                )}
              </div>
            </div>
          );
        })}
      </div>
      {roadmap.documents_needed?.length > 0 && (
        <div className="glass rounded-xl p-4">
          <h4 className="text-sm font-semibold text-ink mb-2">Documents Required</h4>
          <ul className="space-y-1">
            {roadmap.documents_needed.map((doc, i) => (
              <li key={i} className="flex items-center gap-2 text-sm text-ink-muted">
                <CheckCircle2 className="h-3.5 w-3.5 text-mint shrink-0" />{doc}
              </li>
            ))}
          </ul>
        </div>
      )}
      {roadmap.tips?.length > 0 && (
        <div className="glass rounded-xl p-4 border-l-4 border-ocean">
          <h4 className="text-sm font-semibold text-ink mb-2 flex items-center gap-2"><Sparkles className="h-4 w-4 text-ocean" /> Pro Tips</h4>
          <ul className="space-y-1">
            {roadmap.tips.map((tip, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-ink-muted"><span className="mt-1 text-ocean">›</span> {tip}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function SearchProgress({ step }) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-10">
      <div className="relative flex h-14 w-14 items-center justify-center">
        <div className="absolute inset-0 rounded-full border-4 border-ocean/20" />
        <div className="absolute inset-0 animate-spin rounded-full border-4 border-transparent border-t-ocean" />
        <Search className="h-5 w-5 text-ocean" />
      </div>
      <div className="text-center">
        <p className="text-sm font-semibold text-ink">AI is searching…</p>
        <p className="mt-1 text-xs text-ink-faint">{SEARCH_STEPS[step] || "Working…"}</p>
      </div>
      <div className="flex gap-1.5">
        {SEARCH_STEPS.map((_, i) => (
          <div key={i} className={`h-1.5 rounded-full transition-all duration-500 ${i <= step ? "w-6 bg-ocean" : "w-1.5 bg-slate-200"}`} />
        ))}
      </div>
    </div>
  );
}

export default function App() {
  const [activeView, setActiveView] = useState("chat");
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([
    {
      id: "assistant-welcome",
      role: "assistant",
      content: "Hi! I'm your AI career assistant. I can search jobs, analyse your CV, rank opportunities, draft cover letters, and control this app — all from here. What would you like to do?",
    },
  ]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [matches, setMatches] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [profile, setProfile] = useState(null);
  const [profileDraft, setProfileDraft] = useState({
    skills: "", preferred_locations: "", languages: "", target_roles: "", cv_summary: "",
  });
  const [documents, setDocuments] = useState([]);
  const [generatedFiles, setGeneratedFiles] = useState([]);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [documentDraft, setDocumentDraft] = useState("");
  const [llmStatus, setLlmStatus] = useState(null);
  const [llmDraft, setLlmDraft] = useState({
    LLM_PROVIDER: "gemini", GEMINI_API_KEY: "", GROK_API_KEY: "", OPENAI_API_KEY: "",
  });
  const [applications, setApplications] = useState([]);
  const [coverLetter, setCoverLetter] = useState(null);
  const [toolOutput, setToolOutput] = useState(null);
  const [cvSuggestions, setCvSuggestions] = useState(null);
  const [cvSuggestionsLoading, setCvSuggestionsLoading] = useState(false);
  const [artifactRoadmap, setArtifactRoadmap] = useState(null);
  const [artifactLoading, setArtifactLoading] = useState(false);
  const [manualSearch, setManualSearch] = useState({ query: "developer", location: "", includeRemote: true });
  const [selectedCountries, setSelectedCountries] = useState(["de"]);
  const [selectedSources, setSelectedSources] = useState(
    PROVIDERS.filter((p) => p.countries.includes("de")).map((p) => p.key),
  );
  const [savedSearches, setSavedSearches] = useState([]);
  const [mobileChat, setMobileChat] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchStep, setSearchStep] = useState(0);
  const [providerDropdownOpen, setProviderDropdownOpen] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [profileSummaryLoading, setProfileSummaryLoading] = useState(false);
  const [editingKeys, setEditingKeys] = useState({});

  const chatEndRef = useRef(null);
  const textareaRef = useRef(null);
  const uploadInputRef = useRef(null);
  const searchStepTimer = useRef(null);
  const providerDropdownRef = useRef(null);

  const contextJobs = useMemo(() => {
    if (selectedJob) return [selectedJob];
    return result?.jobs?.slice(0, 10) || [];
  }, [result, selectedJob]);
  const filteredJobs = useMemo(() => {
    if (!result?.jobs) return [];
    return result.jobs.filter((job) => {
      const jobCountry = (job.country || "").toLowerCase().trim();
      const matchCountry = selectedCountries.includes(jobCountry);

      const jobSources = job.sources?.length 
        ? job.sources 
        : [job.source].filter(Boolean);
      const matchSource = jobSources.some(src => 
        selectedSources.includes((src || "").toLowerCase().trim())
      );

      return matchCountry && matchSource;
    });
  }, [result, selectedCountries, selectedSources]);
  const allCountriesSelected = selectedCountries.length === COUNTRIES.length;
  const countryParam = allCountriesSelected ? "all" : selectedCountries.join(",");
  const availableProviders = useMemo(
    () => PROVIDERS.filter((p) => p.countries.some((c) => selectedCountries.includes(c))),
    [selectedCountries],
  );
  const currentProvider = AI_PROVIDERS.find((p) => p.key === llmDraft.LLM_PROVIDER) || AI_PROVIDERS[0];

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    function handle(e) {
      if (providerDropdownRef.current && !providerDropdownRef.current.contains(e.target)) {
        setProviderDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, []);

  useEffect(() => {
    refreshWorkspace();
    setSavedSearches(readSavedSearches());
  }, []);

  useEffect(() => {
    setSelectedSources((current) => {
      const keys = availableProviders.map((p) => p.key);
      const next = current.filter((s) => keys.includes(s));
      return next.length ? next : keys;
    });
  }, [availableProviders]);

  async function refreshWorkspace() {
    const [nextProfile, nextDocuments, nextApplications, nextGeneratedFiles, nextLlmStatus] =
      await Promise.all([getProfile(), listDocuments(), listApplications(), listGeneratedFiles(), getLlmStatus()]);
    setProfile(nextProfile);
    setDocuments(nextDocuments);
    setApplications(nextApplications);
    setGeneratedFiles(nextGeneratedFiles);
    setLlmStatus(nextLlmStatus);
    setLlmDraft((c) => ({ ...c, LLM_PROVIDER: nextLlmStatus.default_provider || c.LLM_PROVIDER || "gemini" }));
    setProfileDraft({
      skills: listToCsv(nextProfile.skills),
      preferred_locations: listToCsv(nextProfile.preferred_locations),
      languages: listToCsv(nextProfile.languages),
      target_roles: listToCsv(nextProfile.target_roles),
      cv_summary: nextProfile.cv_summary || "",
    });
  }

  function applyChatResponse(response) {
    setConversationId(response.conversation_id);
    const searchPayload = actionPayload(response, "job_search");
    if (searchPayload?.result) {
      setResult(searchPayload.result);
      saveSearchResult(searchPayload.result, { query: searchPayload.result.query || "", location: searchPayload.result.location || "", country: searchPayload.result.country || "all", sources: [], includeRemote: true });
      setActiveView("jobs");
    }
    const matchPayload = actionPayload(response, "job_match");
    if (matchPayload?.matches) { setMatches(matchPayload.matches); setActiveView("jobs"); }
    const letterPayload = actionPayload(response, "cover_letter");
    if (letterPayload?.cover_letter) { setCoverLetter(letterPayload.cover_letter); setActiveView("documents"); }
    const applicationPayload = actionPayload(response, "application_prepare");
    if (applicationPayload?.application) {
      setApplications((c) => [applicationPayload.application, ...c]);
      setActiveView("applications");
    }
    if (response.navigation?.view) setActiveView(response.navigation.view);
    const selectJobPayload = actionPayload(response, "select_job");
    if (selectJobPayload?.job) { setSelectedJob(selectJobPayload.job); setActiveView("jobs"); }
  }

  function autoResize(el) {
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 128)}px`;
  }

  async function submitChat(event, overrideMessage = null) {
    event?.preventDefault();
    const message = (overrideMessage || chatInput).trim();
    if (!message || chatLoading) return;
    const assistantId = newMessageId("assistant");
    const chatContextMessages = [
      ...messages.filter((i) => i.content && (i.role === "user" || i.role === "assistant")).slice(-8).map((i) => ({ role: i.role, content: i.content })),
      { role: "user", content: message },
    ];
    setError(""); setChatInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    setMessages((c) => [...c,
      { id: newMessageId("user"), role: "user", content: message },
      { id: assistantId, role: "assistant", content: "", actions: [], suggestions: [], streaming: true, status: "Connecting…" },
    ]);
    setChatLoading(true);
    const updateAssistant = (patcher) => setMessages((c) => c.map((i) => i.id === assistantId ? { ...i, ...patcher(i) } : i));
    let receivedLiveEvent = false;
    try {
      await streamChatMessage({
        message, conversationId,
        context: { jobs: contextJobs, messages: chatContextMessages },
        onEvent: (eventData) => {
          receivedLiveEvent = true;
          if (eventData.event === "conversation") setConversationId(eventData.conversation_id);
          if (eventData.event === "status") updateAssistant(() => ({ status: eventData.message || "Working…" }));
          if (eventData.event === "chunk") updateAssistant((c) => ({ content: `${c.content || ""}${eventData.text || ""}`, status: "" }));
          if (eventData.event === "response") {
            const r = eventData.response;
            updateAssistant(() => ({ content: r.message, actions: r.actions || [], suggestions: r.suggestions || [], streaming: false, status: "" }));
            applyChatResponse(r);
          }
        },
      });
    } catch (err) {
      if (!receivedLiveEvent && err.fallbackable) {
        try {
          const r = await sendChatMessage({ message, conversationId, context: { jobs: contextJobs, messages: chatContextMessages } });
          updateAssistant(() => ({ content: r.message, actions: r.actions || [], suggestions: r.suggestions || [], streaming: false, status: "" }));
          applyChatResponse(r); return;
        } catch (fallbackErr) { setError(fallbackErr.response?.data?.detail || fallbackErr.message || "Chat failed."); }
      } else { setError(err.response?.data?.detail || err.message || "Chat failed."); }
      updateAssistant((c) => ({ content: c.content || "I could not complete that live response.", streaming: false, status: "" }));
    } finally { setChatLoading(false); }
  }

  function handleChatKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submitChat(e);
    }
  }

  async function handleUploadFile(file) {
    if (!file) return;
    setUploading(true); setError("");
    try {
      const doc = await uploadDocument(file);
      await refreshWorkspace();
      if (doc.document_type === "cv" || doc.filename.toLowerCase().includes("cv") || doc.filename.toLowerCase().includes("resume")) {
        setProfileSummaryLoading(true);
        try {
          const summaryResult = await generateProfileSummary({ document_id: doc.id });
          if (summaryResult.summary) {
            setProfileDraft((c) => ({ ...c, cv_summary: summaryResult.summary }));
            setProfile((p) => p ? { ...p, cv_summary: summaryResult.summary } : p);
          }
        } catch (_) {}
        finally { setProfileSummaryLoading(false); }
      }
      setMessages((c) => [...c, { id: newMessageId("assistant"), role: "assistant", content: `Processed ${doc.filename}. ${doc.text ? "Profile memory updated from it." : doc.message}` }]);
      setActiveView("profile");
    } catch (err) { setError(err.response?.data?.detail || err.message || "Upload failed."); }
    finally { setUploading(false); }
  }

  async function handleUploadChange(event) {
    const file = event.target.files?.[0];
    await handleUploadFile(file);
    event.target.value = "";
  }

  function handleDrop(e) {
    e.preventDefault(); setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleUploadFile(file);
  }

  function openUploadPicker() {
    if (uploading) return;
    uploadInputRef.current?.click();
  }

  async function runManualSearch(event) {
    event.preventDefault(); setError(""); setSearchLoading(true); setSearchStep(0); setResult(null);
    searchStepTimer.current = setInterval(() => setSearchStep((s) => Math.min(s + 1, SEARCH_STEPS.length - 1)), 2500);
    try {
      const data = await searchJobs({ query: manualSearch.query, location: manualSearch.location, country: countryParam, sources: selectedSources, includeRemote: manualSearch.includeRemote });
      setResult(data); setMatches([]); setActiveView("jobs");
      saveSearchResult(data, { query: manualSearch.query, location: manualSearch.location, country: countryParam, sources: selectedSources, includeRemote: manualSearch.includeRemote });
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Search failed.");
    } finally {
      clearInterval(searchStepTimer.current); setSearchLoading(false); setSearchStep(0);
    }
  }

  function saveSearchResult(data, descriptor) {
    if (!data?.jobs?.length) return;
    const savedSearch = {
      key: searchKey(descriptor), label: searchLabel(descriptor),
      query: descriptor.query || "", location: descriptor.location || "",
      country: descriptor.country || "all", sources: descriptor.sources || [],
      includeRemote: Boolean(descriptor.includeRemote),
      count: data.count || data.jobs.length, savedAt: new Date().toISOString(), result: data,
    };
    setSavedSearches((current) => {
      const next = [savedSearch, ...current.filter((item) => item.key !== savedSearch.key)].slice(0, MAX_SAVED_SEARCHES);
      writeSavedSearches(next);
      return next;
    });
  }

  function loadSavedSearch(savedSearch) {
    setManualSearch({ query: savedSearch.query || "", location: savedSearch.location || "", includeRemote: Boolean(savedSearch.includeRemote) });
    setSelectedCountries(savedSearch.country === "all" ? COUNTRIES.map((item) => item.code) : String(savedSearch.country || "de").split(",").filter(Boolean));
    if (savedSearch.sources?.length) setSelectedSources(savedSearch.sources);
    setResult(savedSearch.result); setMatches([]); setSelectedJob(null); setActiveView("jobs");
  }

  function removeSavedSearch(key) {
    setSavedSearches((current) => { const next = current.filter((item) => item.key !== key); writeSavedSearches(next); return next; });
  }

  async function rankCurrentJobs() {
    if (!result?.jobs?.length) return;
    const data = await matchJobs({ jobs: result.jobs });
    setMatches(data.matches); setActiveView("jobs");
  }

  async function saveProfile() {
    const nextProfile = await updateProfile({ skills: csvToList(profileDraft.skills), preferred_locations: csvToList(profileDraft.preferred_locations), languages: csvToList(profileDraft.languages), target_roles: csvToList(profileDraft.target_roles), cv_summary: profileDraft.cv_summary });
    setProfile(nextProfile);
  }

  async function saveAiSettings(event) {
    event.preventDefault(); setError("");
    const payload = Object.fromEntries(Object.entries(llmDraft).filter(([, v]) => String(v || "").trim()));
    const status = await saveLlmSettings(payload);
    setLlmStatus(status);
    setLlmDraft((c) => ({ ...c, GEMINI_API_KEY: "", GROK_API_KEY: "", OPENAI_API_KEY: "", LLM_PROVIDER: status.default_provider || c.LLM_PROVIDER }));
    setEditingKeys({});
    // Re-fetch fresh status so the panel immediately shows the correct configured state
    try {
      const fresh = await getLlmStatus();
      setLlmStatus(fresh);
      setLlmDraft((c) => ({ ...c, LLM_PROVIDER: fresh.default_provider || c.LLM_PROVIDER }));
    } catch (_) {}
    setMessages((c) => [...c, { id: newMessageId("assistant"), role: "assistant", content: status.available?.length ? `AI providers connected: ${status.available.join(", ")}.` : "Saved AI settings. No provider connected yet." }]);
  }

  async function quickSwitchProvider(providerKey) {
    setLlmDraft((c) => ({ ...c, LLM_PROVIDER: providerKey }));
    setProviderDropdownOpen(false);
    try { await saveLlmSettings({ LLM_PROVIDER: providerKey }); } catch (_) {}
  }

  async function draftCoverLetter(job = selectedJob) {
    if (!job) return;
    const letter = await createCoverLetter({ job, language: "en", tone: "professional", profile });
    setCoverLetter(letter); setActiveView("documents");
  }

  async function exportLetter(format) {
    const file = await exportCoverLetter({ format, cover_letter_id: coverLetter?.id || null, text: coverLetter?.text || "", filename: `CoverLetter-${selectedJob?.company || "Application"}` });
    setGeneratedFiles((c) => [file, ...c]);
    window.open(downloadUrl(file), "_blank", "noreferrer");
  }

  async function buildPackage() {
    const pkg = await createApplicationPackage({ application_name: selectedJob?.company || selectedJob?.title || "Application", job: selectedJob, cover_letter_id: coverLetter?.id || null, certificate_document_ids: documents.filter((d) => d.document_type === "certificate").map((d) => d.id), cv_document_id: documents.find((d) => d.document_type === "cv")?.id || null });
    setGeneratedFiles((c) => [...pkg.files, ...c]);
    setToolOutput({ title: "Application package", data: pkg });
  }

  async function runCvSuggestions() {
    setCvSuggestionsLoading(true); setActiveView("documents");
    const assistantId = newMessageId("assistant");
    setMessages((c) => [...c, { id: assistantId, role: "assistant", content: "", streaming: true, status: "Analysing your CV…" }]);
    try {
      const r = await getCvSuggestions({ cv_text: profileDraft.cv_summary, target_role: profileDraft.target_roles.split(",")[0]?.trim() || "", job: selectedJob || null });
      setCvSuggestions(r);
      const highCount = r.suggestions?.filter((s) => s.priority === "high").length || 0;
      const medCount  = r.suggestions?.filter((s) => s.priority === "medium").length || 0;
      const summary = [
        `**CV Analysis complete** — score: **${r.overall_score}/100**.`,
        r.summary,
        highCount > 0 ? `⚠️ **${highCount} high-priority** issue${highCount > 1 ? "s" : ""} found${selectedJob ? " for **" + selectedJob.title + "**" : ""}.` : "",
        medCount  > 0 ? `📌 ${medCount} medium-priority suggestion${medCount > 1 ? "s" : ""} to review.` : "",
        r.overall_score >= 80 ? "Great shape! Minor polish and you're ready to apply." : r.overall_score >= 60 ? "Focus on the high-priority cards in the Docs section first." : "Work through the high-priority items — they'll have the biggest impact on your application success.",
      ].filter(Boolean).join("\n");
      setMessages((c) => c.map((i) => i.id === assistantId ? { ...i, content: summary, streaming: false, status: "" } : i));
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "CV analysis failed.");
      setMessages((c) => c.map((i) => i.id === assistantId ? { ...i, content: "CV analysis failed. Please try again.", streaming: false, status: "" } : i));
    } finally { setCvSuggestionsLoading(false); }
  }

  async function runGenerateArtifactRoadmap() {
    if (!selectedJob) return;
    setArtifactLoading(true);
    const assistantId = newMessageId("assistant");
    setMessages((c) => [...c, { id: assistantId, role: "assistant", content: "", streaming: true, status: `Building roadmap for ${selectedJob.title}…` }]);
    try {
      const r = await generateArtifactRoadmap({ job: selectedJob, target_country: selectedCountries[0] || "de", languages: profile?.languages || [] });
      setArtifactRoadmap(r);
      const stepSummary = r.steps?.map((s, i) => `${i + 1}. **${s.title}** (${s.category})`).join("\n") || "";
      const message = [
        `**Application Roadmap ready** for **${r.job_title}** at ${r.company || "the company"} 🗺️`,
        "",
        `📍 **Country:** ${r.country?.toUpperCase() || "—"}  |  ⏱️ Estimated timeline: ~${r.timeline_weeks} weeks`,
        "",
        "**Your checklist:**",
        stepSummary,
        "",
        `🛂 **Visa info:** ${r.visa_info}`,
        "",
        `🗣️ **Language:** ${r.language_requirements}`,
        "",
        "Full details with clickable links are in the **Docs → Application Artifacts** section.",
      ].join("\n");
      setMessages((c) => c.map((i) => i.id === assistantId ? { ...i, content: message, streaming: false, status: "" } : i));
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Roadmap generation failed.");
      setMessages((c) => c.map((i) => i.id === assistantId ? { ...i, content: "Roadmap generation failed. Please try again.", streaming: false, status: "" } : i));
    } finally { setArtifactLoading(false); }
  }

  async function runRoadmap() {
    const r = await buildRoadmap({ target_role: profileDraft.target_roles.split(",")[0] || selectedJob?.title || "target role", job: selectedJob });
    setToolOutput({ title: "Skill roadmap", data: r });
  }

  async function runRejectionAnalysis(application = applications[0]) {
    const r = await analyzeRejection({ application_id: application?.id || null, rejection_text: application?.notes || "Rejected application", job: application?.job || selectedJob });
    setToolOutput({ title: "Rejection feedback", data: r });
  }

  async function runApplyAutomation(application) {
    const r = await prepareApplyAutomation({ job: application?.job || selectedJob, confirm_submit: false });
    setToolOutput({ title: "Apply automation", data: r });
  }

  function openDocument(doc) { setSelectedDocument(doc); setDocumentDraft(doc.text || ""); }

  async function saveDocumentEdits() {
    if (!selectedDocument) return;
    const updated = await updateDocument(selectedDocument.id, { text: documentDraft, document_type: selectedDocument.document_type });
    setDocuments((c) => c.map((d) => (d.id === updated.id ? updated : d)));
    setSelectedDocument(updated);
  }

  async function organizeSelectedPdf() {
    if (!selectedDocument) return;
    const r = await organizePdf({ document_id: selectedDocument.id, filename: `${selectedDocument.filename}-organized`, page_order: [], delete_pages: [], rotate_pages: {} });
    setGeneratedFiles((c) => [r.file, ...c]);
    setToolOutput({ title: "Organized PDF", data: r });
  }

  async function trackApplication(job = selectedJob) {
    if (!job) return;
    const application = await createApplication({ job, status: "prepared", notes: "Prepared from career assistant.", cover_letter_id: coverLetter?.id || null });
    setApplications((c) => [application, ...c]); setActiveView("applications");
  }

  async function changeApplicationStatus(application, status) {
    const updated = await updateApplication(application.id, { status });
    setApplications((c) => c.map((i) => (i.id === updated.id ? updated : i)));
  }

  function toggleCountry(code) {
    setSelectedCountries((c) => {
      if (c.includes(code)) { const n = c.filter((i) => i !== code); return n.length ? n : c; }
      setSelectedSources((sources) => Array.from(new Set([...sources, ...providerKeysForCountries([code])])));
      return [...c, code];
    });
  }

  function toggleAllCountries() {
    setSelectedCountries(allCountriesSelected ? [COUNTRIES[0].code] : COUNTRIES.map((i) => i.code));
  }

  function toggleSource(key) {
    setSelectedSources((c) => {
      if (c.includes(key)) { const n = c.filter((i) => i !== key); return n.length ? n : c; }
      return [...c, key];
    });
  }

  return (
    <main className="relative min-h-screen bg-navy-950 text-ink">
      <BackgroundWash />

      {/* HEADER */}
      <header className="glass sticky top-0 z-30 border-b border-line">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3">
            <Logo className="h-9 w-9" />
            <div>
              <h1 className="text-lg font-bold tracking-tight sm:text-xl">
                <span className="text-gradient">YourJob</span>{" "}
                <span className="text-ink">YourChoice</span>
              </h1>
              <p className="hidden text-xs text-ink-faint sm:block">AI-powered career assistant</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* AI Settings panel trigger */}
            <div className="relative" ref={providerDropdownRef}>
              <button
                type="button"
                id="ai-settings-toggle"
                onClick={() => setProviderDropdownOpen(!providerDropdownOpen)}
                className="btn-secondary btn-press h-10 gap-2 px-3 text-xs"
                title="AI Settings"
              >
                <span className="text-base leading-none">{currentProvider.icon}</span>
                <span className="hidden sm:inline font-medium">{currentProvider.label}</span>
                <Settings className={`h-3.5 w-3.5 transition-transform duration-300 ${providerDropdownOpen ? "rotate-90" : ""}`} />
              </button>
              {/* Full settings panel */}
              {providerDropdownOpen && (
                <div className="absolute right-0 top-full z-50 mt-2 w-80 overflow-hidden rounded-2xl border border-line bg-white shadow-2xl settings-panel">
                  {/* Header */}
                  <div className="flex items-center justify-between gap-2 border-b border-line bg-slate-50 px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Settings className="h-4 w-4 text-ocean" />
                      <span className="text-sm font-bold text-ink">AI Settings</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      {llmStatus?.configured?.length > 0 ? (
                        <span className="flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-semibold text-emerald-700">
                          <Check className="h-3 w-3" /> {llmStatus.configured.length} provider{llmStatus.configured.length > 1 ? "s" : ""} set
                        </span>
                      ) : (
                        <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-700">No key added yet</span>
                      )}
                    </div>
                  </div>

                  <form onSubmit={(e) => { saveAiSettings(e); setProviderDropdownOpen(false); }} className="p-4 space-y-4">
                    {/* Provider selector row */}
                    <div>
                      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-faint">Active provider</p>
                      <div className="grid grid-cols-3 gap-1.5">
                        {AI_PROVIDERS.map((p) => (
                          <button
                            key={p.key}
                            type="button"
                            onClick={() => setLlmDraft((c) => ({ ...c, LLM_PROVIDER: p.key }))}
                            className={`btn-press flex flex-col items-center gap-1 rounded-xl border py-2.5 text-xs font-semibold transition-all ${
                              p.key === llmDraft.LLM_PROVIDER
                                ? "border-ocean bg-ocean/5 text-ocean shadow-sm"
                                : "border-line text-ink-muted hover:border-ocean/30 hover:text-ink"
                            }`}
                          >
                            <span className="text-xl">{p.icon}</span>
                            {p.label}
                            {p.key === llmDraft.LLM_PROVIDER && <Check className="h-3 w-3 text-ocean" />}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* API Keys */}
                    <div>
                      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-faint">API Keys</p>
                      <div className="space-y-2.5">
                        {[
                          ["GEMINI_API_KEY", "Gemini", "✦"],
                          ["GROK_API_KEY", "Grok", "⚡"],
                          ["OPENAI_API_KEY", "OpenAI", "◎"],
                        ].map(([key, label, icon]) => {
                          const shortKey = key.split("_")[0].toLowerCase();
                          const isConfigured = llmStatus?.configured?.includes(shortKey);
                          const isActive = llmStatus?.available?.includes(shortKey);
                          const isEditing = editingKeys[key];

                          return (
                            <div key={key} className="block">
                              <div className="mb-1 flex items-center gap-1.5">
                                <span className="text-sm">{icon}</span>
                                <span className="text-xs font-semibold text-ink-muted">{label}</span>
                              </div>

                              {isConfigured && !isEditing ? (
                                <div className={`flex items-center justify-between rounded-lg border px-3 py-1.5 text-xs transition-all ${
                                  isActive
                                    ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                                    : "border-amber-200 bg-amber-50 text-amber-800"
                                }`}>
                                  <span className="flex items-center gap-1.5 font-semibold">
                                    <span className={`inline-block h-2 w-2 rounded-full ${isActive ? "bg-emerald-500 animate-pulse" : "bg-amber-500"}`} />
                                    {isActive ? "Active & Working" : "Key Saved"}
                                  </span>
                                  <button
                                    type="button"
                                    onClick={() => setEditingKeys(c => ({ ...c, [key]: true }))}
                                    className="font-bold underline opacity-80 hover:opacity-100 btn-press"
                                  >
                                    Change
                                  </button>
                                </div>
                              ) : (
                                <div className="relative">
                                  <input
                                    type="password"
                                    value={llmDraft[key]}
                                    onChange={(e) => setLlmDraft((c) => ({ ...c, [key]: e.target.value }))}
                                    className="w-full rounded-lg border border-line bg-slate-50 px-3 py-2 text-sm text-ink placeholder-ink-faint focus:border-ocean focus:outline-none focus:ring-1 focus:ring-ocean/30"
                                    placeholder={`Paste new ${label} API key`}
                                    autoFocus={isEditing}
                                  />
                                  {isEditing && (
                                    <button
                                      type="button"
                                      onClick={() => {
                                        setLlmDraft(c => ({ ...c, [key]: "" }));
                                        setEditingKeys(c => ({ ...c, [key]: false }));
                                      }}
                                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] font-bold text-ink-muted hover:text-ink hover:underline"
                                    >
                                      Cancel
                                    </button>
                                  )}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    <button type="submit" className="btn-primary btn-press w-full">
                      <Save className="h-4 w-4" /> Save &amp; Connect
                    </button>
                  </form>
                </div>
              )}
            </div>

            <button type="button" onClick={() => setMobileChat(!mobileChat)} className="btn-secondary btn-press lg:hidden h-10 w-10 !p-0" aria-label="Toggle chat">
              {mobileChat ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl items-start gap-4 px-4 py-4 sm:px-6 lg:grid-cols-[380px_1fr]">

        {/* SIDEBAR */}
        <aside className={`${mobileChat ? "fixed inset-x-0 bottom-0 z-40 max-h-[82vh] rounded-t-2xl shadow-2xl" : "hidden lg:sticky lg:top-20 lg:flex lg:h-[calc(100vh-96px)] lg:min-h-0 lg:self-start"} glass flex flex-col overflow-hidden rounded-xl`}>
          {/* Tab bar */}
          <div className="border-b border-line p-3">
            <div className="grid grid-cols-5 gap-1">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                const selected = activeView === tab.key;
                return (
                  <button key={tab.key} type="button" onClick={() => setActiveView(tab.key)}
                    className={`btn-press group inline-flex h-10 flex-col items-center justify-center rounded-lg text-xs transition-all duration-200 ${selected ? "bg-gradient-to-r from-ocean/20 to-cyan/10 text-ocean-light" : "text-ink-faint hover:bg-navy-800 hover:text-ink"}`}
                    aria-label={tab.label} title={tab.label}>
                    <Icon className="h-4 w-4" />
                    <span className="mt-0.5 hidden text-[10px] font-medium lg:block">{tab.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Messages */}
          <div className="stagger min-h-0 flex-1 space-y-3 overflow-y-auto p-3">
            {messages.map((message, index) => (
              <div key={message.id || `${message.role}-${index}`}
                className={`message-enter rounded-xl p-3 text-sm leading-6 ${message.role === "user" ? "ml-4 glass-light border border-ocean/20 text-ink" : "mr-4 glass-light text-ink-muted"}`}>
                {message.status && (
                  <div className="mb-2 inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-ocean-light">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />{message.status}
                  </div>
                )}
                {message.content && <p className={`whitespace-pre-wrap ${message.streaming ? "streaming-text" : ""}`}>{message.content}</p>}
                {message.actions?.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {message.actions.map((action) => (
                      <div key={`${action.type}-${action.label}`}>
                        <div className="flex items-center gap-2 text-xs font-semibold text-ink-faint">
                          <CheckCircle2 className="h-3.5 w-3.5 text-mint" />{action.label}
                        </div>
                        {action.type === "agent_debate" && <DebatePanel debate={action.data?.debate} />}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>

          {error && (
            <div className="mx-3 mb-2 rounded-xl border border-rose/30 bg-rose/10 p-3 text-sm text-rose">
              {typeof error === "string" ? error : JSON.stringify(error)}
            </div>
          )}

          {/* Chat input */}
          <form onSubmit={submitChat} className="border-t border-line p-3">
            <div className="flex items-end gap-2">
              <textarea
                ref={textareaRef}
                id="chat-input"
                value={chatInput}
                onChange={(e) => { setChatInput(e.target.value); autoResize(e.target); }}
                onKeyDown={handleChatKeyDown}
                className="glass-input min-h-[2.75rem] max-h-32 flex-1 resize-none rounded-xl px-3 py-2 text-sm leading-6"
                placeholder="Ask anything… Enter to send"
                rows={1}
              />
              <button type="submit" id="chat-send-btn" disabled={chatLoading} className="btn-primary btn-press h-11 w-11 shrink-0 !p-0" aria-label="Send">
                {chatLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </button>
            </div>
            <p className="mt-1.5 text-center text-[10px] text-ink-faint">Enter to send · Shift+Enter for newline</p>
          </form>
        </aside>

        {/* MAIN CONTENT */}
        <section className="view-enter min-w-0 space-y-4" key={activeView}>

          {toolOutput && activeView !== "documents" && (
            <div className="glass rounded-xl p-4">
              <h2 className="text-lg font-semibold text-ink">{toolOutput.title}</h2>
              <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap rounded-xl glass-light p-4 text-sm leading-6 text-ink-muted">{JSON.stringify(toolOutput.data, null, 2)}</pre>
            </div>
          )}

          {/* CHAT VIEW */}
          {activeView === "chat" && (
            <div className="glass glow-border rounded-xl p-6">
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-ocean to-cyan">
                  <Sparkles className="h-5 w-5 text-white" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-ink">Career command center</h2>
                  <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-muted">
                    Type any request in the chat. The AI can search jobs, rank results, draft cover letters, analyse your CV, and navigate the app.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* JOBS VIEW */}
          {activeView === "jobs" && (
            <div className="space-y-4">
              <form onSubmit={runManualSearch} className="glass rounded-xl p-4 space-y-4">
                <div className="grid gap-3 sm:grid-cols-[1fr_1fr_auto]">
                  <label>
                    <span className="mb-1 block text-sm font-medium text-ink-muted">Keyword</span>
                    <input value={manualSearch.query} onChange={(e) => setManualSearch((c) => ({ ...c, query: e.target.value }))} className="glass-input min-h-10 w-full rounded-xl px-3 text-sm" />
                  </label>
                  <label>
                    <span className="mb-1 block text-sm font-medium text-ink-muted">Location</span>
                    <input value={manualSearch.location} onChange={(e) => setManualSearch((c) => ({ ...c, location: e.target.value }))} className="glass-input min-h-10 w-full rounded-xl px-3 text-sm" placeholder="Optional" />
                  </label>
                  <div className="flex items-end gap-2">
                    <button id="search-btn" className="btn-primary btn-press" disabled={searchLoading}>
                      {searchLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
                      {searchLoading ? "Searching…" : "Search"}
                    </button>
                    <button type="button" onClick={rankCurrentJobs} disabled={!result?.jobs?.length} className="btn-secondary btn-press">
                      <Sparkles className="h-4 w-4" /> Rank
                    </button>
                  </div>
                </div>
                <div className="grid gap-4 lg:grid-cols-[1fr_1.4fr]">
                  <fieldset>
                    <legend className="mb-2 text-sm font-medium text-ink-muted">Countries</legend>
                    <div className="flex flex-wrap gap-2">
                      <button type="button" onClick={toggleAllCountries} className={`btn-press chip ${allCountriesSelected ? "chip-active" : "chip-inactive"} cursor-pointer`}>
                        {allCountriesSelected && <Check className="h-3.5 w-3.5" />} All
                      </button>
                      {COUNTRIES.map((c) => {
                        const checked = selectedCountries.includes(c.code);
                        return (
                          <button key={c.code} type="button" onClick={() => toggleCountry(c.code)} className={`btn-press chip ${checked ? "chip-active" : "chip-inactive"} cursor-pointer`}>
                            {checked && <Check className="h-3.5 w-3.5" />} {c.label}
                          </button>
                        );
                      })}
                    </div>
                  </fieldset>
                  <fieldset>
                    <legend className="mb-2 text-sm font-medium text-ink-muted">Sources</legend>
                    <div className="flex flex-wrap gap-2">
                      {availableProviders.map((p) => {
                        const checked = selectedSources.includes(p.key);
                        return (
                          <button key={p.key} type="button" onClick={() => toggleSource(p.key)} className={`btn-press chip ${checked ? "chip-active" : "chip-inactive"} cursor-pointer`}>
                            {checked && <Check className="h-3.5 w-3.5" />} {p.label}
                          </button>
                        );
                      })}
                    </div>
                  </fieldset>
                </div>
                <label className="glass-light flex min-h-10 max-w-sm items-center justify-between gap-3 rounded-xl px-3 py-2 text-sm text-ink-muted">
                  <span className="font-medium">Include remote jobs</span>
                  <input type="checkbox" checked={manualSearch.includeRemote} onChange={(e) => setManualSearch((c) => ({ ...c, includeRemote: e.target.checked }))} className="h-4 w-4 rounded border-line accent-ocean" />
                </label>
              </form>

              {searchLoading && <div className="glass rounded-xl"><SearchProgress step={searchStep} /></div>}

              {!searchLoading && (
                <>
                  <div className="glass rounded-xl p-4">
                    <div className="flex min-h-10 flex-wrap items-center justify-between gap-3">
                      <h2 className="text-lg font-semibold text-ink">Saved searches</h2>
                      <span className="chip chip-active">{savedSearches.length} saved</span>
                    </div>
                    {savedSearches.length === 0 ? (
                      <div className="mt-3 rounded-xl border border-dashed border-line p-5 text-center text-sm text-ink-faint">Saved searches will appear here after a search returns jobs.</div>
                    ) : (
                      <div className="mt-3 grid gap-3 md:grid-cols-2">
                        {savedSearches.map((item) => (
                          <div key={item.key} className="glass-light rounded-xl p-3">
                            <div className="flex items-start justify-between gap-3">
                              <button type="button" onClick={() => loadSavedSearch(item)} className="min-w-0 flex-1 text-left">
                                <span className="block truncate text-sm font-semibold text-ink">{item.label}</span>
                                <span className="mt-1 flex items-center gap-1 text-xs text-ink-faint"><Clock3 className="h-3.5 w-3.5" /> {item.count || item.result?.count || 0} jobs</span>
                              </button>
                              <button type="button" onClick={() => removeSavedSearch(item.key)}
                                className="btn-press inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-ink-faint transition hover:bg-rose/10 hover:text-rose" aria-label={`Remove ${item.label}`}>
                                <Trash2 className="h-4 w-4" />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {matches.length > 0 && (
                    <div className="glass rounded-xl p-4">
                      <h2 className="text-lg font-semibold text-ink">Ranked matches</h2>
                      <div className="stagger mt-3 grid gap-3">
                        {matches.slice(0, 5).map((match) => (
                          <button key={`${match.job.title}-${match.job.apply_url || match.score}`} type="button" onClick={() => setSelectedJob(match.job)}
                            className="btn-press glass-light glow-border rounded-xl p-3 text-left">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <span className="font-semibold text-ink">{match.job.title}</span>
                              <span className="chip chip-active">{match.score}% {match.recommendation}</span>
                            </div>
                            <p className="mt-1 text-sm text-ink-muted">Strengths: {match.strengths.join(", ")}</p>
                            {match.gaps.length > 0 && <p className="mt-1 text-sm text-ink-faint">Gaps: {match.gaps.join(", ")}</p>}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                   <div className="flex min-h-10 flex-wrap items-center justify-between gap-3">
                    <h2 className="text-lg font-semibold text-ink">
                      {result 
                        ? `${filteredJobs.length} of ${result.jobs?.length || 0} jobs` 
                        : "Job dashboard"}
                    </h2>
                    <div className="flex gap-2">
                      <button type="button" onClick={() => draftCoverLetter()} disabled={!selectedJob} className="btn-secondary btn-press"><FileText className="h-4 w-4" /> Cover letter</button>
                      <button type="button" onClick={() => trackApplication()} disabled={!selectedJob} className="btn-primary btn-press"><Navigation className="h-4 w-4" /> Track</button>
                    </div>
                  </div>
                  {!result && <div className="glass rounded-xl border border-dashed border-line p-8 text-center text-sm text-ink-faint">Ask the chat to find jobs or run a manual search.</div>}
                  {result && filteredJobs.length === 0 && (
                    <div className="glass rounded-xl border border-dashed border-line p-8 text-center text-sm text-ink-faint">
                      No jobs match the selected country &amp; source filters. Adjust checkboxes above to see matches.
                    </div>
                  )}
                  <div className="stagger space-y-3">
                    {filteredJobs.map((job, index) => (
                      <div key={`${job.source}-${job.apply_url || job.source_url || index}`} onClick={() => setSelectedJob(job)}
                        className={`btn-press cursor-pointer rounded-xl transition-all ${selectedJob === job ? "ring-2 ring-ocean/60" : ""}`}>
                        <JobCard job={job} />
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}

          {/* PROFILE VIEW */}
          {activeView === "profile" && (
            <div className="space-y-4">
              <div className="glass rounded-xl p-4">
                <div className="mb-4 flex items-center justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-semibold text-ink">Profile memory</h2>
                    <p className="text-xs text-ink-faint mt-0.5">Written & maintained by AI from your CV</p>
                  </div>
                  <div className="flex gap-2">
                    {profileSummaryLoading && <div className="btn-secondary h-11 gap-2 px-3 text-sm"><Loader2 className="h-4 w-4 animate-spin" /> AI writing…</div>}
                    <button type="button" onClick={saveProfile} className="btn-primary btn-press"><Save className="h-4 w-4" /> Save</button>
                  </div>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  {[["skills", "Skills"], ["preferred_locations", "Preferred locations"], ["languages", "Languages"], ["target_roles", "Target roles"]].map(([key, label]) => (
                    <label key={key}>
                      <span className="mb-1 block text-sm font-medium text-ink-muted">{label}</span>
                      <input value={profileDraft[key]} onChange={(e) => setProfileDraft((c) => ({ ...c, [key]: e.target.value }))} className="glass-input min-h-10 w-full rounded-xl px-3 text-sm" placeholder="Comma separated" />
                    </label>
                  ))}
                </div>
                <label className="mt-3 block">
                  <span className="mb-1 block text-sm font-medium text-ink-muted">CV summary (AI-generated)</span>
                  <textarea value={profileDraft.cv_summary} onChange={(e) => setProfileDraft((c) => ({ ...c, cv_summary: e.target.value }))} className="glass-input min-h-44 w-full rounded-xl px-3 py-2 text-sm" />
                </label>
              </div>

              {/* AI settings notice */}
              <div className="glass-light rounded-xl border border-ocean/20 p-4 flex items-center gap-3">
                <Settings className="h-5 w-5 text-ocean shrink-0" />
                <div>
                  <p className="text-sm font-semibold text-ink">AI provider settings are in the navbar</p>
                  <p className="text-xs text-ink-faint mt-0.5">
                    {llmStatus?.available?.length
                      ? `Connected: ${llmStatus.available.join(", ")}`
                      : "Click the provider button in the top bar to add API keys."}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* DOCUMENTS VIEW */}
          {activeView === "documents" && (
            <div className="space-y-4">
              {/* Upload zone */}
              <label
                htmlFor="doc-upload"
                className={`glass block w-full rounded-xl border-2 p-6 text-center transition-all duration-200 cursor-pointer ${dragOver ? "border-ocean bg-ocean/5 scale-[1.01]" : "border-dashed border-line"}`}
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
              >
                <div className="flex flex-col items-center gap-3">
                  <div className={`flex h-14 w-14 items-center justify-center rounded-2xl transition-all ${dragOver ? "bg-ocean text-white scale-110" : "bg-ocean/10 text-ocean"}`}>
                    {uploading ? <Loader2 className="h-7 w-7 animate-spin" /> : <Upload className="h-7 w-7" />}
                  </div>
                  <div>
                    <p className="font-semibold text-ink">{uploading ? "Uploading & processing…" : dragOver ? "Drop to upload!" : "Upload your CV or documents"}</p>
                    <p className="mt-1 text-sm text-ink-faint">Drag & drop, or tap to browse · PDF, DOCX, TXT</p>
                  </div>
                  <span className="btn-primary btn-press pointer-events-none cursor-pointer">
                    <Upload className="h-4 w-4" />{uploading ? "Processing…" : "Choose file"}
                  </span>
                </div>
              </label>
              <input
                id="doc-upload"
                ref={uploadInputRef}
                type="file"
                accept="application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,.pdf,.doc,.docx,.txt"
                className="sr-only"
                onChange={handleUploadChange}
                disabled={uploading}
              />

              {cvSuggestions && <CvSuggestionsPanel suggestions={cvSuggestions} />}

              {coverLetter && (
                <div className="glass rounded-xl p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <h2 className="text-lg font-semibold text-ink">Cover letter draft</h2>
                    <div className="flex flex-wrap gap-2">
                      {["pdf", "docx", "txt"].map((format) => (
                        <button key={format} type="button" onClick={() => exportLetter(format)} className="btn-secondary btn-press text-xs uppercase">{format}</button>
                      ))}
                      <button type="button" onClick={buildPackage} className="btn-primary btn-press">Build package</button>
                    </div>
                  </div>
                  <pre className="mt-3 whitespace-pre-wrap rounded-xl glass-light p-4 text-sm leading-6 text-ink-muted">{coverLetter.text}</pre>
                </div>
              )}

              {toolOutput && (
                <div className="glass rounded-xl p-4">
                  <h2 className="text-lg font-semibold text-ink">{toolOutput.title}</h2>
                  <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap rounded-xl glass-light p-4 text-sm leading-6 text-ink-muted">{JSON.stringify(toolOutput.data, null, 2)}</pre>
                </div>
              )}

              <div className="glass rounded-xl p-4">
                <h2 className="text-lg font-semibold text-ink">Documents</h2>
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  {documents.map((doc) => (
                    <button key={doc.id} type="button" onClick={() => openDocument(doc)} className="btn-press glass-light glow-border rounded-xl p-3 text-left">
                      <div className="flex items-start gap-2">
                        <FileText className="mt-1 h-4 w-4 text-ocean-light" />
                        <div className="min-w-0">
                          <p className="truncate font-semibold text-ink">{doc.filename}</p>
                          <p className="text-sm text-ink-faint">{doc.document_type} – {doc.status}</p>
                        </div>
                      </div>
                      {doc.message && <p className="mt-2 text-sm text-ink-faint">{doc.message}</p>}
                    </button>
                  ))}
                  {documents.length === 0 && (
                    <div className="col-span-2 glass-light rounded-xl border border-dashed border-line p-8 text-center text-sm text-ink-faint">Uploaded CVs, job descriptions, and certificates will appear here.</div>
                  )}
                </div>
              </div>

              {selectedDocument && (
                <div className="glass rounded-xl p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <h2 className="text-lg font-semibold text-ink">File preview</h2>
                    <div className="flex flex-wrap gap-2">
                      <select value={selectedDocument.document_type} onChange={(e) => setSelectedDocument((c) => ({ ...c, document_type: e.target.value }))} className="glass-input min-h-9 rounded-xl px-2 text-sm">
                        {["cv", "job_description", "certificate", "other"].map((type) => (<option key={type} value={type}>{type}</option>))}
                      </select>
                      <button type="button" onClick={saveDocumentEdits} className="btn-primary btn-press text-sm">Save edits</button>
                      {selectedDocument.filename.toLowerCase().endsWith(".pdf") && (
                        <button type="button" onClick={organizeSelectedPdf} className="btn-secondary btn-press text-sm">Organize PDF</button>
                      )}
                    </div>
                  </div>
                  <textarea value={documentDraft} onChange={(e) => setDocumentDraft(e.target.value)} className="glass-input mt-3 min-h-64 w-full rounded-xl px-3 py-2 text-sm leading-6" />
                </div>
              )}

              {/* CAREER TOOLS */}
              <div className="glass rounded-xl p-4">
                <div className="flex items-center justify-between gap-3 mb-3">
                  <div>
                    <h2 className="text-lg font-semibold text-ink flex items-center gap-2">
                      <Sparkles className="h-5 w-5 text-ocean" /> Career Tools
                    </h2>
                    <p className="text-xs text-ink-faint mt-0.5">AI analyses your CV and the selected job — results appear in chat & below</p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={runCvSuggestions}
                    disabled={cvSuggestionsLoading}
                    className="btn-secondary btn-press"
                  >
                    {cvSuggestionsLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <PenLine className="h-4 w-4" />}
                    {cvSuggestionsLoading ? "Analysing…" : "Analyse CV"}
                  </button>
                  <button type="button" onClick={runRoadmap} className="btn-secondary btn-press">
                    <Sparkles className="h-4 w-4" /> Skill roadmap
                  </button>
                  <button
                    type="button"
                    onClick={runGenerateArtifactRoadmap}
                    disabled={!selectedJob || artifactLoading}
                    className="btn-primary btn-press"
                    title={!selectedJob ? "Select a job from the Jobs tab first" : ""}
                  >
                    {artifactLoading ? <><Loader2 className="h-4 w-4 animate-spin" /> Generating…</> : <><Map className="h-4 w-4" /> Generate Roadmap</>}
                  </button>
                  {!selectedJob && (
                    <p className="w-full text-xs text-ink-faint mt-1">← Select a job in the Jobs tab to enable roadmap generation</p>
                  )}
                </div>
              </div>

              {/* CV SUGGESTIONS (shown after analysis) */}

              <div className="glass rounded-xl p-4">
                <h2 className="text-lg font-semibold text-ink">Generated files</h2>
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  {generatedFiles.map((file) => (
                    <a key={file.id} href={downloadUrl(file)} target="_blank" rel="noreferrer" className="btn-press glass-light glow-border rounded-xl p-3 text-sm">
                      <span className="block font-semibold text-ink">{file.filename}</span>
                      <span className="text-ink-faint">{file.kind}</span>
                    </a>
                  ))}
                  {generatedFiles.length === 0 && (
                    <div className="col-span-2 glass-light rounded-xl border border-dashed border-line p-8 text-center text-sm text-ink-faint">Exported cover letters, merged PDFs, and application packages will appear here.</div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* APPLICATIONS VIEW */}
          {activeView === "applications" && (
            <div className="glass rounded-xl p-4">
              <h2 className="text-lg font-semibold text-ink">Application tracker</h2>
              <div className="stagger mt-3 space-y-3">
                {applications.map((app) => (
                  <div key={app.id} className="glass-light glow-border rounded-xl p-3">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold text-ink">{app.job.title}</p>
                        <p className="text-sm text-ink-muted">{app.job.company || "Unknown company"} – {app.status}</p>
                      </div>
                      <select value={app.status} onChange={(e) => changeApplicationStatus(app, e.target.value)} className="glass-input min-h-9 rounded-xl px-2 text-sm">
                        {["saved", "prepared", "applied", "rejected", "interview"].map((s) => (<option key={s} value={s}>{s}</option>))}
                      </select>
                    </div>
                    {app.notes && <p className="mt-2 text-sm text-ink-faint">{app.notes}</p>}
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button type="button" onClick={() => runApplyAutomation(app)} className="btn-secondary btn-press text-sm">Prepare portal fields</button>
                      <button type="button" onClick={() => runRejectionAnalysis(app)} className="btn-secondary btn-press text-sm">Analyze rejection</button>
                    </div>
                  </div>
                ))}
                {applications.length === 0 && (
                  <div className="glass-light rounded-xl border border-dashed border-line p-8 text-center text-sm text-ink-faint">Prepared and submitted applications will appear here.</div>
                )}
              </div>
            </div>
          )}
        </section>
      </div>

      {/* Mobile bottom nav */}
      {!mobileChat && (
        <nav className="glass fixed bottom-0 inset-x-0 z-30 border-t border-line lg:hidden">
          <div className="grid grid-cols-5">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const selected = activeView === tab.key;
              return (
                <button key={tab.key} type="button" onClick={() => setActiveView(tab.key)}
                  className={`btn-press flex flex-col items-center gap-0.5 py-2.5 text-[10px] font-medium transition ${selected ? "text-ocean-light" : "text-ink-faint"}`}>
                  <Icon className="h-5 w-5" />
                  {tab.label}
                </button>
              );
            })}
          </div>
        </nav>
      )}
    </main>
  );
}
