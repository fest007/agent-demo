import { api } from "./client";
import type { ModelSelection } from "@/stores/appStore";

interface SessionData {
  session_id: string;
  name: string;
  created_at: string;
  updated_at: string;
}

export async function createSession(): Promise<SessionData> {
  return api.post("/sessions");
}

export async function listSessions(): Promise<SessionData[]> {
  return api.get("/sessions");
}

export async function updateSession(
  sessionId: string,
  name: string
): Promise<SessionData> {
  return api.put(`/sessions/${sessionId}`, { name });
}

export async function deleteSession(sessionId: string): Promise<void> {
  return api.delete(`/sessions/${sessionId}`);
}

function modelPayload(selection?: ModelSelection) {
  const customBaseUrl = selection?.customBaseUrl?.trim();
  const customApiKey = selection?.customApiKey?.trim();
  return {
    model_provider: selection?.providerId,
    model: selection?.modelId,
    api_key_id: selection?.apiKeyId,
    custom_base_url: customBaseUrl || undefined,
    custom_api_key: customApiKey || undefined,
  };
}

export async function summarizeSession(
  sessionId: string,
  selection?: ModelSelection
): Promise<SessionData> {
  return api.post(`/sessions/${sessionId}/summarize`, modelPayload(selection));
}
