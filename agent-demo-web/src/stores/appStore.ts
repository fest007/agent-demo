import { create } from "zustand";

export interface ModelSelection {
  providerId?: string;
  modelId?: string;
  imageModelId?: string;
  videoModelId?: string;
  apiKeyId?: string;
  customBaseUrl?: string;
  customApiKey?: string;
}

export interface MediaNotification {
  id: string;
  title: string;
  description: string;
  status: "success" | "error";
  sessionId: string;
  messageId?: string;
  conversationId?: number | null;
}

interface AppState {
  sidebarCollapsed: boolean;
  currentPage: string;
  knowledgeFocus: { source: string; chunkId?: string } | null;
  messageFocus: { sessionId: string; messageId?: string; conversationId?: number | null } | null;
  mediaNotifications: MediaNotification[];
  modelSelection: ModelSelection;
  markdownTypingSpeed: number;
  toggleSidebar: () => void;
  setCurrentPage: (page: string) => void;
  setKnowledgeFocus: (focus: { source: string; chunkId?: string } | null) => void;
  setMessageFocus: (focus: { sessionId: string; messageId?: string; conversationId?: number | null } | null) => void;
  pushMediaNotification: (notice: MediaNotification) => void;
  removeMediaNotification: (id: string) => void;
  setModelSelection: (selection: ModelSelection) => void;
  setMarkdownTypingSpeed: (speed: number) => void;
}

const MODEL_SELECTION_KEY = "agent-demo-model-selection";
const MARKDOWN_TYPING_SPEED_KEY = "agent-demo-markdown-typing-speed";

function loadModelSelection(): ModelSelection {
  try {
    const raw = localStorage.getItem(MODEL_SELECTION_KEY);
    const selection = raw ? JSON.parse(raw) : {};
    if (selection.videoModelId === "doubao-seedance-2-0-260128") {
      selection.videoModelId = "doubao-seedance-1-5-pro-251215";
      saveModelSelection(selection);
    }
    return selection;
  } catch {
    return {};
  }
}

function saveModelSelection(selection: ModelSelection) {
  try {
    localStorage.setItem(MODEL_SELECTION_KEY, JSON.stringify(selection));
  } catch {}
}

function loadMarkdownTypingSpeed(): number {
  try {
    const value = Number(localStorage.getItem(MARKDOWN_TYPING_SPEED_KEY));
    return Number.isFinite(value) && value > 0 ? value : 120;
  } catch {
    return 120;
  }
}

function saveMarkdownTypingSpeed(speed: number) {
  try {
    localStorage.setItem(MARKDOWN_TYPING_SPEED_KEY, String(speed));
  } catch {}
}

export const useAppStore = create<AppState>((set) => ({
  sidebarCollapsed: false,
  currentPage: "chat",
  knowledgeFocus: null,
  messageFocus: null,
  mediaNotifications: [],
  modelSelection: loadModelSelection(),
  markdownTypingSpeed: loadMarkdownTypingSpeed(),
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  setCurrentPage: (page) => set({ currentPage: page }),
  setKnowledgeFocus: (focus) => set({ knowledgeFocus: focus }),
  setMessageFocus: (focus) => set({ messageFocus: focus, currentPage: "chat" }),
  pushMediaNotification: (notice) =>
    set((s) => ({
      mediaNotifications: [
        notice,
        ...s.mediaNotifications.filter((item) => item.id !== notice.id),
      ].slice(0, 4),
    })),
  removeMediaNotification: (id) =>
    set((s) => ({
      mediaNotifications: s.mediaNotifications.filter((item) => item.id !== id),
    })),
  setModelSelection: (selection) => {
    saveModelSelection(selection);
    set({ modelSelection: selection });
  },
  setMarkdownTypingSpeed: (speed) => {
    const next = Math.max(20, Math.min(400, Math.round(speed)));
    saveMarkdownTypingSpeed(next);
    set({ markdownTypingSpeed: next });
  },
}));
