import axios from "axios";

const LOCAL_BACKEND_URL = "http://127.0.0.1:8000";

function isLocalHost() {
  if (typeof window === "undefined") return false;
  return ["localhost", "127.0.0.1", "::1", "[::1]"].includes(window.location.hostname);
}

function defaultApiBaseUrl() {
  if (import.meta.env.VITE_API_BASE_URL) return import.meta.env.VITE_API_BASE_URL;
  return isLocalHost() ? LOCAL_BACKEND_URL : "";
}

const API_BASE_URL = defaultApiBaseUrl();

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

function apiUrl(path) {
  return `${API_BASE_URL.replace(/\/$/, "")}${path}`;
}

function localApiUrl(path) {
  return `${LOCAL_BACKEND_URL}${path}`;
}

function shouldRetryLocal(status) {
  return isLocalHost() && [404, 405, 502, 503, 504].includes(status);
}

async function postWithLocalFallback(path, payload) {
  try {
    const response = await api.post(path, payload);
    return response.data;
  } catch (error) {
    const status = error.response?.status;
    if (!shouldRetryLocal(status) || API_BASE_URL === LOCAL_BACKEND_URL) throw error;
    const response = await axios.post(localApiUrl(path), payload, { timeout: 30000 });
    return response.data;
  }
}

export async function searchJobs({
  query,
  location,
  country,
  sources,
  includeRemote,
  refresh = false,
}) {
  const response = await api.get("/api/jobs/search", {
    params: {
      query,
      location,
      country,
      sources: sources.join(","),
      include_remote: includeRemote,
      refresh,
    },
  });

  return response.data;
}

export async function sendChatMessage({ message, conversationId, attachments = [], context = {} }) {
  return postWithLocalFallback("/api/jobs/chat", {
    message,
    conversation_id: conversationId,
    attachments,
    context,
  });
}

export async function getLlmStatus() {
  const response = await api.get("/api/llm/status");
  return response.data;
}

export async function saveLlmSettings(payload) {
  const response = await api.put("/api/llm/settings", payload);
  return response.data;
}

export async function streamChatMessage({
  message,
  conversationId,
  attachments = [],
  context = {},
  onEvent,
}) {
  const payload = {
    message,
    conversation_id: conversationId,
    attachments,
    context,
  };
  let response = await fetch(apiUrl("/api/jobs/chat/stream"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok && shouldRetryLocal(response.status) && API_BASE_URL !== LOCAL_BACKEND_URL) {
    response = await fetch(localApiUrl("/api/jobs/chat/stream"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify(payload),
    });
  }

  if (!response.ok) {
    let detail = "";
    try {
      detail = await response.text();
    } catch {
      detail = "";
    }
    const error = new Error(detail || `Live chat failed with status ${response.status}`);
    error.fallbackable = response.status === 404 || response.status === 405;
    throw error;
  }

  if (!response.body) {
    const error = new Error("This browser did not expose a live response stream.");
    error.fallbackable = true;
    throw error;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalResponse = null;
  let streamedError = null;

  function processFrame(frame) {
    const data = frame
      .split("\n")
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trimStart())
      .join("\n");

    if (!data) return;
    const event = JSON.parse(data);
    onEvent?.(event);
    if (event.event === "response") finalResponse = event.response;
    if (event.event === "error") streamedError = new Error(event.message || "Live chat failed.");
  }

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });

    const frames = buffer.split("\n\n");
    buffer = frames.pop() || "";
    frames.forEach(processFrame);

    if (done) break;
  }

  if (buffer.trim()) processFrame(buffer);
  if (streamedError) throw streamedError;
  if (!finalResponse) throw new Error("Live chat ended before the final response arrived.");
  return finalResponse;
}

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await api.post("/api/documents/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function listDocuments() {
  const response = await api.get("/api/documents");
  return response.data;
}

export async function updateDocument(id, payload) {
  const response = await api.patch(`/api/documents/${id}`, payload);
  return response.data;
}

export async function getProfile() {
  const response = await api.get("/api/profile");
  return response.data;
}

export async function updateProfile(profile) {
  const response = await api.put("/api/profile", profile);
  return response.data;
}

export async function matchJobs(payload) {
  const response = await api.post("/api/jobs/match", payload);
  return response.data;
}

export async function debateJob(payload) {
  const response = await api.post("/api/agents/debate", payload);
  return response.data;
}

export async function createCoverLetter(payload) {
  const response = await api.post("/api/documents/cover-letter", payload);
  return response.data;
}

export async function exportCoverLetter(payload) {
  const response = await api.post("/api/documents/export-cover-letter", payload);
  return response.data;
}

export async function listGeneratedFiles() {
  const response = await api.get("/api/documents/generated");
  return response.data;
}

export async function createApplicationPackage(payload) {
  const response = await api.post("/api/documents/application-package", payload);
  return response.data;
}

export async function improveCv(payload) {
  const response = await api.post("/api/cv/improve", payload);
  return response.data;
}

export async function compareCv(payload) {
  const response = await api.post("/api/cv/compare", payload);
  return response.data;
}

export async function prepareInterview(payload) {
  const response = await api.post("/api/interview/prepare", payload);
  return response.data;
}

export async function analyzeRejection(payload) {
  const response = await api.post("/api/feedback/rejection", payload);
  return response.data;
}

export async function buildRoadmap(payload) {
  const response = await api.post("/api/roadmap/skills", payload);
  return response.data;
}

export async function mergePdfs(payload) {
  const response = await api.post("/api/pdf/merge", payload);
  return response.data;
}

export async function organizePdf(payload) {
  const response = await api.post("/api/pdf/organize", payload);
  return response.data;
}

export async function prepareApplyAutomation(payload) {
  const response = await api.post("/api/apply/automation", payload);
  return response.data;
}

export async function listApplications() {
  const response = await api.get("/api/applications");
  return response.data;
}

export async function createApplication(payload) {
  const response = await api.post("/api/applications", payload);
  return response.data;
}

export async function updateApplication(id, payload) {
  const response = await api.patch(`/api/applications/${id}`, payload);
  return response.data;
}
