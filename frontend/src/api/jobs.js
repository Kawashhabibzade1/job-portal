import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "",
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
