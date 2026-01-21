import { useAuthStore } from "@/stores/authStore"

// Ensure API_URL has a protocol - handles case where env var is missing https://
function normalizeApiUrl(url: string | undefined): string {
  if (!url) return "http://localhost:8000"
  // If URL doesn't start with http:// or https://, add https://
  if (!url.startsWith("http://") && !url.startsWith("https://")) {
    return `https://${url}`
  }
  return url
}

const API_URL = normalizeApiUrl(import.meta.env.VITE_API_URL)

/**
 * Authenticated fetch wrapper that automatically includes the auth token
 * in API requests.
 */
export async function apiFetch(
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = useAuthStore.getState().token

  const headers: HeadersInit = {
    ...options.headers,
  }

  // Add Authorization header if token exists
  if (token) {
    const h = headers as Record<string, string>
    h["Authorization"] = `Bearer ${token}`
  }

  // Add Content-Type for JSON bodies (but not for FormData)
  if (options.body && !(options.body instanceof FormData)) {
    const h = headers as Record<string, string>
    h["Content-Type"] = "application/json"
  }

  const url = endpoint.startsWith("http") ? endpoint : `${API_URL}${endpoint}`

  return fetch(url, {
    ...options,
    headers,
  })
}

/**
 * Convenience methods for common HTTP operations
 */
export const api = {
  get: (endpoint: string, options?: RequestInit) =>
    apiFetch(endpoint, { ...options, method: "GET" }),

  post: (endpoint: string, body?: unknown, options?: RequestInit) =>
    apiFetch(endpoint, {
      ...options,
      method: "POST",
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),

  patch: (endpoint: string, body?: unknown, options?: RequestInit) =>
    apiFetch(endpoint, {
      ...options,
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  delete: (endpoint: string, options?: RequestInit) =>
    apiFetch(endpoint, { ...options, method: "DELETE" }),
}

export { API_URL }
