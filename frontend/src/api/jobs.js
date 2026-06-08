import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000",
  timeout: 30000,
});

export async function searchJobs({ query, location, country, sources }) {
  const response = await api.get("/api/jobs/search", {
    params: {
      query,
      location,
      country,
      sources: sources.join(","),
    },
  });

  return response.data;
}

