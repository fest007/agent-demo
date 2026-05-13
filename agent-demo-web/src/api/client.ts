const DESKTOP_API_BASE = "http://127.0.0.1:18765/api";

function isTauriRuntime() {
  return typeof window !== "undefined" && Boolean((window as any).__TAURI_INTERNALS__);
}

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || (isTauriRuntime() ? DESKTOP_API_BASE : "/api");

export function apiUrl(path: string) {
  return `${API_BASE_URL}${path}`;
}

export async function apiFetch(path: string, options?: RequestInit) {
  return fetch(apiUrl(path), options);
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const resp = await apiFetch(path, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!resp.ok) {
    throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
  }
  return resp.json();
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
