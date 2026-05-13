import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

let _cachedXCache: string | null = null;

export function getLastCacheStatus(): string | null {
  return _cachedXCache;
}

const client = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("jwt");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  config.headers["X-Request-ID"] = crypto.randomUUID();
  return config;
});

client.interceptors.response.use(
  (response) => {
    _cachedXCache = (response.headers["x-cache"] as string | undefined) ?? null;
    return response;
  },
  (error) => {
    if (axios.isAxiosError(error)) {
      if (error.response?.status === 401) {
        localStorage.removeItem("jwt");
        window.location.href = "/login";
        return Promise.reject(error);
      }
      if (error.response?.status === 403) {
        const detail =
          typeof error.response.data?.detail === "string"
            ? error.response.data.detail
            : "Access denied";
        return Promise.reject(new Error(detail));
      }
    }
    return Promise.reject(error);
  },
);

export default client;
