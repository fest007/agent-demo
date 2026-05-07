import { create } from "zustand";

interface Session {
  sessionId: string;
  name: string;
  createdAt: Date;
  updatedAt: Date;
}

interface SessionState {
  sessions: Session[];
  currentSessionId: string | null;

  setSessions: (sessions: Session[]) => void;
  addSession: (session: Session) => void;
  updateSessionName: (sessionId: string, name: string) => void;
  removeSession: (sessionId: string) => void;
  setCurrentSessionId: (id: string | null) => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  sessions: [],
  currentSessionId: null,

  setSessions: (sessions) => set({ sessions }),
  addSession: (session) =>
    set((s) => ({ sessions: [session, ...s.sessions] })),
  updateSessionName: (sessionId, name) =>
    set((s) => ({
      sessions: s.sessions.map((sess) =>
        sess.sessionId === sessionId ? { ...sess, name } : sess
      ),
    })),
  removeSession: (sessionId) =>
    set((s) => ({
      sessions: s.sessions.filter((sess) => sess.sessionId !== sessionId),
      currentSessionId:
        s.currentSessionId === sessionId ? null : s.currentSessionId,
    })),
  setCurrentSessionId: (id) => set({ currentSessionId: id }),
}));
