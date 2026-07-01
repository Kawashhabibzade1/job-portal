import {
  BriefcaseBusiness,
  Check,
  CheckCircle2,
  FileText,
  FolderKanban,
  Loader2,
  MessageSquareText,
  Navigation,
  Paperclip,
  Save,
  Search,
  Send,
  Sparkles,
  Upload,
  UserRound,
  Menu,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  createApplication,
  createApplicationPackage,
  createCoverLetter,
  exportCoverLetter,
  buildRoadmap,
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
  prepareInterview,
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
  { key: "linkedin", label: "LinkedIn", countries: ["de", "at", "ch", "gb", "be", "tr"] },
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
  { code: "tr", label: "Northern Cyprus" },
];

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

/* === Logo SVG === */
function Logo({ className = "h-8 w-8" }) {
  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden="true">
      <defs>
        <linearGradient id="logoGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#6366f1" />
          <stop offset="50%" stopColor="#8b5cf6" />
          <stop offset="100%" stopColor="#06b6d4" />
        </linearGradient>
      </defs>
      <rect width="64" height="64" rx="14" fill="#0f172a" />
      <circle cx="32" cy="26" r="10" fill="url(#logoGrad)" opacity="0.9" />
      <path d="M22 40c0-5.5 4.5-10 10-10s10 4.5 10 10" fill="none" stroke="url(#logoGrad)" strokeWidth="3.5" strokeLinecap="round" />
      <path d="M26 50h12" stroke="#06b6d4" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

/* === Floating background orbs === */
function BackgroundOrbs() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="orb orb-1 animate-float-slow" />
      <div className="orb orb-2 animate-float-medium" />
      <div className="orb orb-3 animate-float-fast" />
    </div>
  );
}

function DebatePanel({ debate }) {
  if (!debate) return null;
  const opinions = [
    ["Grok", debate.grok],
    ["Gemini", debate.gemini],
    ["Judge", debate.judge],
  ];
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
            <p className="mt-1 text-xs font-medium text-amber">
              {opinion.status}: {opinion.error || "fallback used"}
            </p>
          )}
        </div>
      ))}
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
      content: "Hi, I'm your AI career assistant. I can search jobs, read your CV, rank opportunities, draft cover letters, and track applications — all from this chat.",
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
  const [manualSearch, setManualSearch] = useState({
    query: "developer", location: "", includeRemote: true,
  });
  const [selectedCountries, setSelectedCountries] = useState(["de"]);
  const [selectedSources, setSelectedSources] = useState(
    PROVIDERS.filter((p) => p.countries.includes("de")).map((p) => p.key),
  );
  const [mobileChat, setMobileChat] = useState(false);

  const contextJobs = useMemo(() => {
    if (selectedJob) return [selectedJob];
    return result?.jobs?.slice(0, 10) || [];
  }, [result, selectedJob]);
  const allCountriesSelected = selectedCountries.length === COUNTRIES.length;
  const countryParam = allCountriesSelected ? "all" : selectedCountries.join(",");
  const availableProviders = useMemo(
    () => PROVIDERS.filter((p) => p.countries.some((c) => selectedCountries.includes(c))),
    [selectedCountries],
  );

  useEffect(() => { refreshWorkspace(); }, []);

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
    if (searchPayload?.result) { setResult(searchPayload.result); setActiveView("jobs"); }
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
  }

  async function submitChat(event, overrideMessage = null) {
    event?.preventDefault();
    const message = (overrideMessage || chatInput).trim();
    if (!message || chatLoading) return;

    const assistantId = newMessageId("assistant");
    const chatContextMessages = [
      ...messages.filter((i) => i.content && (i.role === "user" || i.role === "assistant")).slice(-8)
        .map((i) => ({ role: i.role, content: i.content })),
      { role: "user", content: message },
    ];
    setError(""); setChatInput("");
    setMessages((c) => [...c,
      { id: newMessageId("user"), role: "user", content: message },
      { id: assistantId, role: "assistant", content: "", actions: [], suggestions: [], streaming: true, status: "Connecting..." },
    ]);
    setChatLoading(true);
    const updateAssistant = (patcher) => {
      setMessages((c) => c.map((i) => i.id === assistantId ? { ...i, ...patcher(i) } : i));
    };
    let receivedLiveEvent = false;
    try {
      await streamChatMessage({
        message, conversationId,
        context: { jobs: contextJobs, messages: chatContextMessages },
        onEvent: (eventData) => {
          receivedLiveEvent = true;
          if (eventData.event === "conversation") setConversationId(eventData.conversation_id);
          if (eventData.event === "status") updateAssistant(() => ({ status: eventData.message || "Working..." }));
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

  async function handleUpload(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true); setError("");
    try {
      const document = await uploadDocument(file);
      await refreshWorkspace();
      setMessages((c) => [...c, { id: newMessageId("assistant"), role: "assistant", content: `I processed ${document.filename}. ${document.text ? "I updated your profile memory from it." : document.message}` }]);
      setActiveView("profile");
    } catch (err) { setError(err.response?.data?.detail || err.message || "Upload failed."); }
    finally { setUploading(false); event.target.value = ""; }
  }

  async function runManualSearch(event) {
    event.preventDefault(); setError("");
    const data = await searchJobs({ query: manualSearch.query, location: manualSearch.location, country: countryParam, sources: selectedSources, includeRemote: manualSearch.includeRemote });
    setResult(data); setMatches([]); setActiveView("jobs");
  }

  async function rankCurrentJobs() {
    if (!result?.jobs?.length) return;
    const data = await matchJobs({ jobs: result.jobs });
    setMatches(data.matches); setActiveView("jobs");
  }

  async function saveProfile() {
    const nextProfile = await updateProfile({
      skills: csvToList(profileDraft.skills), preferred_locations: csvToList(profileDraft.preferred_locations),
      languages: csvToList(profileDraft.languages), target_roles: csvToList(profileDraft.target_roles),
      cv_summary: profileDraft.cv_summary,
    });
    setProfile(nextProfile);
  }

  async function saveAiSettings(event) {
    event.preventDefault(); setError("");
    const payload = Object.fromEntries(Object.entries(llmDraft).filter(([, v]) => String(v || "").trim()));
    const status = await saveLlmSettings(payload);
    setLlmStatus(status);
    setLlmDraft((c) => ({ ...c, GEMINI_API_KEY: "", GROK_API_KEY: "", OPENAI_API_KEY: "", LLM_PROVIDER: status.default_provider || c.LLM_PROVIDER }));
    setMessages((c) => [...c, { id: newMessageId("assistant"), role: "assistant",
      content: status.available?.length ? `AI providers connected: ${status.available.join(", ")}. I can now use them for chat and agent analysis.` : "I saved the AI settings, but no provider is connected yet. Check that the key field is not empty." }]);
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
    const pkg = await createApplicationPackage({
      application_name: selectedJob?.company || selectedJob?.title || "Application", job: selectedJob,
      cover_letter_id: coverLetter?.id || null,
      certificate_document_ids: documents.filter((d) => d.document_type === "certificate").map((d) => d.id),
      cv_document_id: documents.find((d) => d.document_type === "cv")?.id || null,
    });
    setGeneratedFiles((c) => [...pkg.files, ...c]);
    setToolOutput({ title: "Application package", data: pkg });
  }

  async function runCvImprove() {
    const r = await improveCv({ cv_text: profileDraft.cv_summary, target_role: profileDraft.target_roles.split(",")[0] || "", job: selectedJob });
    setToolOutput({ title: "Improved CV draft", data: r }); setActiveView("documents");
  }

  async function runInterviewPrep() {
    const r = await prepareInterview({ role: profileDraft.target_roles.split(",")[0] || selectedJob?.title || "target role", job: selectedJob });
    setToolOutput({ title: "Interview preparation", data: r });
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

  function openDocument(document) { setSelectedDocument(document); setDocumentDraft(document.text || ""); }

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
      <BackgroundOrbs />

      {/* === HEADER === */}
      <header className="glass sticky top-0 z-30 border-b border-line">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3">
            <Logo className="h-9 w-9" />
            <div>
              <h1 className="text-lg font-bold tracking-tight sm:text-xl">
                <span className="text-gradient">YourJob</span>{" "}
                <span className="text-ink">YourChoice</span>
              </h1>
              <p className="hidden text-xs text-ink-faint sm:block">
                AI-powered career assistant
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <label className="btn-primary cursor-pointer">
              {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
              <span className="hidden sm:inline">Upload CV</span>
              <input className="sr-only" type="file" onChange={handleUpload} />
            </label>
            <button
              type="button"
              onClick={() => setMobileChat(!mobileChat)}
              className="btn-secondary lg:hidden"
              aria-label="Toggle chat"
            >
              {mobileChat ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-4 px-4 py-4 sm:px-6 lg:grid-cols-[380px_1fr]">

        {/* === SIDEBAR (Chat) === */}
        <aside className={`${mobileChat ? "fixed inset-x-0 bottom-0 z-40 max-h-[75vh] rounded-t-2xl shadow-2xl" : "hidden lg:flex"} glass flex min-h-[calc(100vh-80px)] flex-col rounded-xl`}>
          {/* Tab bar */}
          <div className="border-b border-line p-3">
            <div className="grid grid-cols-5 gap-1">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                const selected = activeView === tab.key;
                return (
                  <button
                    key={tab.key}
                    type="button"
                    onClick={() => setActiveView(tab.key)}
                    className={`group inline-flex h-10 flex-col items-center justify-center rounded-lg text-xs transition-all duration-200 ${
                      selected
                        ? "bg-gradient-to-r from-ocean/20 to-cyan/10 text-ocean-light"
                        : "text-ink-faint hover:bg-navy-800 hover:text-ink"
                    }`}
                    aria-label={tab.label}
                    title={tab.label}
                  >
                    <Icon className="h-4 w-4" />
                    <span className="mt-0.5 hidden text-[10px] font-medium lg:block">{tab.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Messages */}
          <div className="stagger flex-1 space-y-3 overflow-y-auto p-3">
            {messages.map((message, index) => (
              <div
                key={message.id || `${message.role}-${index}`}
                className={`rounded-xl p-3 text-sm leading-6 ${
                  message.role === "user"
                    ? "ml-4 glass-light border border-ocean/20 text-ink"
                    : "mr-4 glass-light text-ink-muted"
                }`}
              >
                {message.status && (
                  <div className="mb-2 inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-ocean-light">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    {message.status}
                  </div>
                )}
                {message.content && (
                  <p className={`whitespace-pre-wrap ${message.streaming ? "streaming-text" : ""}`}>
                    {message.content}
                  </p>
                )}
                {message.actions?.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {message.actions.map((action) => (
                      <div key={`${action.type}-${action.label}`}>
                        <div className="flex items-center gap-2 text-xs font-semibold text-ink-faint">
                          <CheckCircle2 className="h-3.5 w-3.5 text-mint" />
                          {action.label}
                        </div>
                        {action.type === "agent_debate" && <DebatePanel debate={action.data?.debate} />}
                      </div>
                    ))}
                  </div>
                )}
                {message.suggestions?.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {message.suggestions.map((suggestion) => (
                      <button
                        key={suggestion}
                        type="button"
                        onClick={(e) => submitChat(e, suggestion)}
                        className="chip chip-inactive cursor-pointer transition hover:border-ocean/40 hover:text-ocean-light"
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>

          {error && (
            <div className="mx-3 mb-2 rounded-xl border border-rose/30 bg-rose/10 p-3 text-sm text-rose">
              {typeof error === "string" ? error : JSON.stringify(error)}
            </div>
          )}

          {/* Chat input */}
          <form onSubmit={submitChat} className="border-t border-line p-3">
            <div className="flex items-end gap-2">
              <label className="btn-secondary h-11 w-11 shrink-0 cursor-pointer !p-0">
                <Paperclip className="h-4 w-4" />
                <input className="sr-only" type="file" onChange={handleUpload} />
              </label>
              <textarea
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                className="glass-input min-h-[2.75rem] max-h-32 flex-1 resize-none rounded-xl px-3 py-2 text-sm"
                placeholder="Ask for jobs, CV help, matching, cover letters..."
                rows={1}
              />
              <button type="submit" disabled={chatLoading} className="btn-primary h-11 w-11 shrink-0 !p-0" aria-label="Send">
                {chatLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </button>
            </div>
          </form>
        </aside>

        {/* === MAIN CONTENT === */}
        <section className="view-enter space-y-4" key={activeView}>

          {toolOutput && activeView !== "documents" && (
            <div className="glass rounded-xl p-4">
              <h2 className="text-lg font-semibold text-ink">{toolOutput.title}</h2>
              <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap rounded-xl glass-light p-4 text-sm leading-6 text-ink-muted">
                {JSON.stringify(toolOutput.data, null, 2)}
              </pre>
            </div>
          )}

          {/* ====== CHAT VIEW ====== */}
          {activeView === "chat" && (
            <div className="glass glow-border rounded-xl p-6">
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-ocean to-cyan">
                  <Sparkles className="h-5 w-5 text-white" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-ink">Career command center</h2>
                  <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-muted">
                    Start with natural language. Try asking for roles in a country, upload a CV,
                    rank the visible jobs, or prepare an application package.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* ====== JOBS VIEW ====== */}
          {activeView === "jobs" && (
            <div className="space-y-4">
              <form onSubmit={runManualSearch} className="glass rounded-xl p-4 space-y-4">
                <div className="grid gap-3 sm:grid-cols-[1fr_1fr_auto]">
                  <label>
                    <span className="mb-1 block text-sm font-medium text-ink-muted">Keyword</span>
                    <input value={manualSearch.query} onChange={(e) => setManualSearch((c) => ({ ...c, query: e.target.value }))}
                      className="glass-input min-h-10 w-full rounded-xl px-3 text-sm" />
                  </label>
                  <label>
                    <span className="mb-1 block text-sm font-medium text-ink-muted">Location</span>
                    <input value={manualSearch.location} onChange={(e) => setManualSearch((c) => ({ ...c, location: e.target.value }))}
                      className="glass-input min-h-10 w-full rounded-xl px-3 text-sm" placeholder="Optional" />
                  </label>
                  <div className="flex items-end gap-2">
                    <button className="btn-primary"><Search className="h-4 w-4" /> Search</button>
                    <button type="button" onClick={rankCurrentJobs} disabled={!result?.jobs?.length} className="btn-secondary">
                      <Sparkles className="h-4 w-4" /> Rank
                    </button>
                  </div>
                </div>

                <div className="grid gap-4 lg:grid-cols-[1fr_1.4fr]">
                  <fieldset>
                    <legend className="mb-2 text-sm font-medium text-ink-muted">Countries</legend>
                    <div className="flex flex-wrap gap-2">
                      <button type="button" onClick={toggleAllCountries}
                        className={`chip ${allCountriesSelected ? "chip-active" : "chip-inactive"} cursor-pointer`}>
                        {allCountriesSelected && <Check className="h-3.5 w-3.5" />} All
                      </button>
                      {COUNTRIES.map((c) => {
                        const checked = selectedCountries.includes(c.code);
                        return (
                          <button key={c.code} type="button" onClick={() => toggleCountry(c.code)}
                            className={`chip ${checked ? "chip-active" : "chip-inactive"} cursor-pointer`}>
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
                          <button key={p.key} type="button" onClick={() => toggleSource(p.key)}
                            className={`chip ${checked ? "chip-active" : "chip-inactive"} cursor-pointer`}>
                            {checked && <Check className="h-3.5 w-3.5" />} {p.label}
                          </button>
                        );
                      })}
                    </div>
                  </fieldset>
                </div>

                <label className="glass-light flex min-h-10 max-w-sm items-center justify-between gap-3 rounded-xl px-3 py-2 text-sm text-ink-muted">
                  <span className="font-medium">Include remote jobs</span>
                  <input type="checkbox" checked={manualSearch.includeRemote}
                    onChange={(e) => setManualSearch((c) => ({ ...c, includeRemote: e.target.checked }))}
                    className="h-4 w-4 rounded border-line accent-ocean" />
                </label>
              </form>

              {matches.length > 0 && (
                <div className="glass rounded-xl p-4">
                  <h2 className="text-lg font-semibold text-ink">Ranked matches</h2>
                  <div className="stagger mt-3 grid gap-3">
                    {matches.slice(0, 5).map((match) => (
                      <button key={`${match.job.title}-${match.job.apply_url || match.score}`} type="button"
                        onClick={() => setSelectedJob(match.job)}
                        className="glass-light glow-border rounded-xl p-3 text-left">
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
                <h2 className="text-lg font-semibold text-ink">{result ? `${result.count} jobs` : "Job dashboard"}</h2>
                <div className="flex gap-2">
                  <button type="button" onClick={() => draftCoverLetter()} disabled={!selectedJob} className="btn-secondary">
                    <FileText className="h-4 w-4" /> Cover letter
                  </button>
                  <button type="button" onClick={() => trackApplication()} disabled={!selectedJob} className="btn-primary">
                    <Navigation className="h-4 w-4" /> Track
                  </button>
                </div>
              </div>

              {!result && (
                <div className="glass rounded-xl border border-dashed border-line p-8 text-center text-sm text-ink-faint">
                  Ask the chat to find jobs or run a manual search.
                </div>
              )}
              <div className="stagger space-y-3">
                {result?.jobs?.map((job, index) => (
                  <div key={`${job.source}-${job.apply_url || job.source_url || index}`}
                    onClick={() => setSelectedJob(job)}
                    className={`cursor-pointer rounded-xl transition-all ${selectedJob === job ? "ring-2 ring-ocean/60" : ""}`}>
                    <JobCard job={job} />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ====== PROFILE VIEW ====== */}
          {activeView === "profile" && (
            <div className="space-y-4">
              <div className="glass rounded-xl p-4">
                <div className="mb-4 flex items-center justify-between gap-3">
                  <h2 className="text-lg font-semibold text-ink">Profile memory</h2>
                  <button type="button" onClick={saveProfile} className="btn-primary"><Save className="h-4 w-4" /> Save</button>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  {[["skills", "Skills"], ["preferred_locations", "Preferred locations"], ["languages", "Languages"], ["target_roles", "Target roles"]].map(([key, label]) => (
                    <label key={key}>
                      <span className="mb-1 block text-sm font-medium text-ink-muted">{label}</span>
                      <input value={profileDraft[key]} onChange={(e) => setProfileDraft((c) => ({ ...c, [key]: e.target.value }))}
                        className="glass-input min-h-10 w-full rounded-xl px-3 text-sm" placeholder="Comma separated" />
                    </label>
                  ))}
                </div>
                <label className="mt-3 block">
                  <span className="mb-1 block text-sm font-medium text-ink-muted">CV summary</span>
                  <textarea value={profileDraft.cv_summary} onChange={(e) => setProfileDraft((c) => ({ ...c, cv_summary: e.target.value }))}
                    className="glass-input min-h-44 w-full rounded-xl px-3 py-2 text-sm" />
                </label>
              </div>

              <form onSubmit={saveAiSettings} className="glass rounded-xl p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-semibold text-ink">AI providers</h2>
                    <p className="mt-1 text-sm text-ink-faint">{llmStatus?.available?.length ? `Connected: ${llmStatus.available.join(", ")}` : "No provider connected yet."}</p>
                  </div>
                  <button type="submit" className="btn-primary"><Save className="h-4 w-4" /> Save keys</button>
                </div>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <label>
                    <span className="mb-1 block text-sm font-medium text-ink-muted">Default provider</span>
                    <select value={llmDraft.LLM_PROVIDER} onChange={(e) => setLlmDraft((c) => ({ ...c, LLM_PROVIDER: e.target.value }))}
                      className="glass-input min-h-10 w-full rounded-xl px-3 text-sm">
                      <option value="gemini">Gemini</option>
                      <option value="grok">Grok</option>
                      <option value="openai">OpenAI</option>
                    </select>
                  </label>
                  {[["GEMINI_API_KEY", "Gemini API key"], ["GROK_API_KEY", "Grok API key"], ["OPENAI_API_KEY", "OpenAI API key"]].map(([key, label]) => (
                    <label key={key}>
                      <span className="mb-1 block text-sm font-medium text-ink-muted">{label}</span>
                      <input type="password" value={llmDraft[key]} onChange={(e) => setLlmDraft((c) => ({ ...c, [key]: e.target.value }))}
                        className="glass-input min-h-10 w-full rounded-xl px-3 text-sm"
                        placeholder={llmStatus?.available?.includes(key.split("_")[0].toLowerCase()) ? "Configured" : "Paste key"} />
                    </label>
                  ))}
                </div>
              </form>

              <div className="glass rounded-xl p-4">
                <h2 className="text-lg font-semibold text-ink">Career tools</h2>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button type="button" onClick={runCvImprove} className="btn-secondary">Improve CV</button>
                  <button type="button" onClick={runInterviewPrep} className="btn-secondary">Interview prep</button>
                  <button type="button" onClick={runRoadmap} className="btn-secondary">Skill roadmap</button>
                </div>
              </div>
            </div>
          )}

          {/* ====== DOCUMENTS VIEW ====== */}
          {activeView === "documents" && (
            <div className="space-y-4">
              {coverLetter && (
                <div className="glass rounded-xl p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <h2 className="text-lg font-semibold text-ink">Cover letter draft</h2>
                    <div className="flex flex-wrap gap-2">
                      {["pdf", "docx", "txt"].map((format) => (
                        <button key={format} type="button" onClick={() => exportLetter(format)} className="btn-secondary text-xs uppercase">{format}</button>
                      ))}
                      <button type="button" onClick={buildPackage} className="btn-primary">Build package</button>
                    </div>
                  </div>
                  <pre className="mt-3 whitespace-pre-wrap rounded-xl glass-light p-4 text-sm leading-6 text-ink-muted">{coverLetter.text}</pre>
                </div>
              )}
              {toolOutput && (
                <div className="glass rounded-xl p-4">
                  <h2 className="text-lg font-semibold text-ink">{toolOutput.title}</h2>
                  <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap rounded-xl glass-light p-4 text-sm leading-6 text-ink-muted">
                    {JSON.stringify(toolOutput.data, null, 2)}
                  </pre>
                </div>
              )}
              <div className="glass rounded-xl p-4">
                <h2 className="text-lg font-semibold text-ink">Documents</h2>
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  {documents.map((doc) => (
                    <button key={doc.id} type="button" onClick={() => openDocument(doc)}
                      className="glass-light glow-border rounded-xl p-3 text-left">
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
                    <div className="glass-light rounded-xl border border-dashed border-line p-8 text-center text-sm text-ink-faint">
                      Uploaded CVs, job descriptions, and certificates will appear here.
                    </div>
                  )}
                </div>
              </div>
              {selectedDocument && (
                <div className="glass rounded-xl p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <h2 className="text-lg font-semibold text-ink">File preview</h2>
                    <div className="flex flex-wrap gap-2">
                      <select value={selectedDocument.document_type}
                        onChange={(e) => setSelectedDocument((c) => ({ ...c, document_type: e.target.value }))}
                        className="glass-input min-h-9 rounded-xl px-2 text-sm">
                        {["cv", "job_description", "certificate", "other"].map((type) => (<option key={type} value={type}>{type}</option>))}
                      </select>
                      <button type="button" onClick={saveDocumentEdits} className="btn-primary text-sm">Save edits</button>
                      {selectedDocument.filename.toLowerCase().endsWith(".pdf") && (
                        <button type="button" onClick={organizeSelectedPdf} className="btn-secondary text-sm">Organize PDF</button>
                      )}
                    </div>
                  </div>
                  <textarea value={documentDraft} onChange={(e) => setDocumentDraft(e.target.value)}
                    className="glass-input mt-3 min-h-64 w-full rounded-xl px-3 py-2 text-sm leading-6" />
                </div>
              )}
              <div className="glass rounded-xl p-4">
                <h2 className="text-lg font-semibold text-ink">Generated files</h2>
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  {generatedFiles.map((file) => (
                    <a key={file.id} href={downloadUrl(file)} target="_blank" rel="noreferrer"
                      className="glass-light glow-border rounded-xl p-3 text-sm">
                      <span className="block font-semibold text-ink">{file.filename}</span>
                      <span className="text-ink-faint">{file.kind}</span>
                    </a>
                  ))}
                  {generatedFiles.length === 0 && (
                    <div className="glass-light rounded-xl border border-dashed border-line p-8 text-center text-sm text-ink-faint">
                      Exported cover letters, merged PDFs, and application packages will appear here.
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ====== APPLICATIONS VIEW ====== */}
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
                      <select value={app.status} onChange={(e) => changeApplicationStatus(app, e.target.value)}
                        className="glass-input min-h-9 rounded-xl px-2 text-sm">
                        {["saved", "prepared", "applied", "rejected", "interview"].map((s) => (<option key={s} value={s}>{s}</option>))}
                      </select>
                    </div>
                    {app.notes && <p className="mt-2 text-sm text-ink-faint">{app.notes}</p>}
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button type="button" onClick={() => runApplyAutomation(app)} className="btn-secondary text-sm">Prepare portal fields</button>
                      <button type="button" onClick={() => runRejectionAnalysis(app)} className="btn-secondary text-sm">Analyze rejection</button>
                    </div>
                  </div>
                ))}
                {applications.length === 0 && (
                  <div className="glass-light rounded-xl border border-dashed border-line p-8 text-center text-sm text-ink-faint">
                    Prepared and submitted applications will appear here.
                  </div>
                )}
              </div>
            </div>
          )}
        </section>
      </div>

      {/* Mobile bottom nav (when chat is hidden) */}
      {!mobileChat && (
        <nav className="glass fixed bottom-0 inset-x-0 z-30 border-t border-line lg:hidden">
          <div className="grid grid-cols-5">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const selected = activeView === tab.key;
              return (
                <button key={tab.key} type="button" onClick={() => setActiveView(tab.key)}
                  className={`flex flex-col items-center gap-0.5 py-2 text-[10px] font-medium transition ${
                    selected ? "text-ocean-light" : "text-ink-faint"
                  }`}>
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
