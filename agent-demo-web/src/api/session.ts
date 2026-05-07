import { api } from "./client";

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

export async function summarizeSession(
  sessionId: string
): Promise<SessionData> {
  return api.post(`/sessions/${sessionId}/summarize`);
}
