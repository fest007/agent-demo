import { create } from "zustand";
import type { KnowledgeCitation, MediaTask, Message, ToolCall, MessageVersion } from "@/types";

interface ChatState {
  messages: Message[];
  threadId: string;
  isLoading: boolean;
  streamingContent: string;
  currentEmotion: string;
  pendingEdit: string | null;
  regeneratingMessageId: string | null;
  abortController: AbortController | null;

  addMessage: (msg: Message) => void;
  updateLastAssistant: (content: string) => void;
  setThreadId: (id: string) => void;
  setLoading: (v: boolean) => void;
  setStreamingContent: (s: string) => void;
  setCurrentEmotion: (e: string) => void;
  clearMessages: () => void;
  appendStreamToken: (token: string) => void;
  addToolCall: (tc: ToolCall) => void;
  updateLastToolCall: (name: string | undefined, output: string) => void;
  addThought: (text: string) => void;
  addCitation: (citation: KnowledgeCitation) => void;
  addMediaTask: (task: MediaTask) => void;
  updateMediaTask: (task: MediaTask) => void;
  loadSession: (sessionId: string, messages: Message[]) => void;

  setPendingEdit: (text: string | null) => void;
  saveCurrentVersion: (messageId: string) => void;
  regenerateStart: (messageId: string) => void;
  regenerateStreamToken: (messageId: string, token: string) => void;
  regenerateAddToolCall: (messageId: string, tc: ToolCall) => void;
  regenerateUpdateToolCall: (messageId: string, name: string | undefined, output: string) => void;
  regenerateAddThought: (messageId: string, text: string) => void;
  regenerateAddCitation: (messageId: string, citation: KnowledgeCitation) => void;
  regenerateAddMediaTask: (messageId: string, task: MediaTask) => void;
  regenerateFinish: (messageId: string, fullContent: string, emotion?: string) => void;
  switchVersion: (messageId: string, versionIndex: number) => void;

  setAbortController: (ac: AbortController | null) => void;
  abortStream: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  threadId: "",
  isLoading: false,
  streamingContent: "",
  currentEmotion: "neutral",
  pendingEdit: null,
  regeneratingMessageId: null,
  abortController: null,

  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),

  updateLastAssistant: (content) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, content };
      }
      return { messages: msgs };
    }),

  setThreadId: (id) => set({ threadId: id }),
  setLoading: (v) => set({ isLoading: v }),
  setStreamingContent: (s) => set({ streamingContent: s }),
  setCurrentEmotion: (e) => set({ currentEmotion: e }),
  clearMessages: () => set({ messages: [], threadId: "" }),

  appendStreamToken: (token) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, content: last.content + token };
      }
      return { messages: msgs, streamingContent: s.streamingContent + token };
    }),

  addToolCall: (tc) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant") {
        const toolCalls = [...(last.toolCalls || []), tc];
        msgs[msgs.length - 1] = { ...last, toolCalls };
      }
      return { messages: msgs };
    }),

  updateLastToolCall: (name, output) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant" && last.toolCalls?.length) {
        const toolCalls = [...last.toolCalls];
        const targetIndex = name
          ? [...toolCalls].reverse().findIndex((tc) => tc.name === name)
          : 0;
        const index = name && targetIndex >= 0 ? toolCalls.length - 1 - targetIndex : toolCalls.length - 1;
        toolCalls[index] = { ...toolCalls[index], output };
        msgs[msgs.length - 1] = { ...last, toolCalls };
      }
      return { messages: msgs };
    }),

  addThought: (text) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant") {
        const thoughts = [...(last.thoughts || []), { text, timestamp: new Date() }];
        msgs[msgs.length - 1] = { ...last, thoughts };
      }
      return { messages: msgs };
    }),

  addCitation: (citation) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant") {
        const exists = last.citations?.some((item) => item.chunk_id === citation.chunk_id);
        if (!exists) {
          const citations = [...(last.citations || []), citation];
          msgs[msgs.length - 1] = { ...last, citations };
        }
      }
      return { messages: msgs };
    }),

  addMediaTask: (task) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant") {
        const existing = last.mediaTasks || [];
        const mediaTasks = existing.some((item) => item.id === task.id)
          ? existing.map((item) => (item.id === task.id ? task : item))
          : [...existing, task];
        msgs[msgs.length - 1] = { ...last, mediaTasks };
      }
      return { messages: msgs };
    }),

  updateMediaTask: (task) =>
    set((s) => ({
      messages: s.messages.map((msg) => {
        if (!msg.mediaTasks?.some((item) => item.id === task.id)) return msg;
        return {
          ...msg,
          mediaTasks: msg.mediaTasks.map((item) => (item.id === task.id ? task : item)),
        };
      }),
    })),

  loadSession: (sessionId, messages) =>
    set({
      threadId: sessionId,
      messages,
      streamingContent: "",
      currentEmotion: "neutral",
      isLoading: false,
      pendingEdit: null,
      regeneratingMessageId: null,
      abortController: null,
    }),

  setPendingEdit: (text) => set({ pendingEdit: text }),

  saveCurrentVersion: (messageId) =>
    set((s) => {
      const msgs = s.messages.map((msg) => {
        if (msg.id !== messageId || msg.role !== "assistant") return msg;
        const currentVersion: MessageVersion = {
          content: msg.content,
          toolCalls: msg.toolCalls,
          thoughts: msg.thoughts,
          citations: msg.citations,
          mediaTasks: msg.mediaTasks,
          emotion: msg.emotion,
          timestamp: msg.timestamp,
        };
        const existingVersions = msg.versions || [];
        return {
          ...msg,
          versions: [...existingVersions, currentVersion],
          currentVersionIndex: existingVersions.length,
        };
      });
      return { messages: msgs };
    }),

  regenerateStart: (messageId) =>
    set((s) => {
      const msgs = s.messages.map((msg) => {
        if (msg.id !== messageId || msg.role !== "assistant") return msg;
        return {
          ...msg,
          content: "",
          toolCalls: [],
          thoughts: [],
          citations: [],
          mediaTasks: [],
          emotion: undefined,
          timestamp: new Date(),
        };
      });
      return {
        messages: msgs,
        streamingContent: "",
        isLoading: true,
        regeneratingMessageId: messageId,
      };
    }),

  regenerateStreamToken: (messageId, token) =>
    set((s) => {
      const msgs = s.messages.map((msg) => {
        if (msg.id !== messageId || msg.role !== "assistant") return msg;
        return { ...msg, content: msg.content + token };
      });
      return { messages: msgs, streamingContent: s.streamingContent + token };
    }),

  regenerateAddToolCall: (messageId, tc) =>
    set((s) => {
      const msgs = s.messages.map((msg) => {
        if (msg.id !== messageId || msg.role !== "assistant") return msg;
        const toolCalls = [...(msg.toolCalls || []), tc];
        return { ...msg, toolCalls };
      });
      return { messages: msgs };
    }),

  regenerateUpdateToolCall: (messageId, name, output) =>
    set((s) => {
      const msgs = s.messages.map((msg) => {
        if (msg.id !== messageId || msg.role !== "assistant" || !msg.toolCalls?.length) return msg;
        const toolCalls = [...msg.toolCalls];
        const targetIndex = name
          ? [...toolCalls].reverse().findIndex((tc) => tc.name === name)
          : 0;
        const index = name && targetIndex >= 0 ? toolCalls.length - 1 - targetIndex : toolCalls.length - 1;
        toolCalls[index] = { ...toolCalls[index], output };
        return { ...msg, toolCalls };
      });
      return { messages: msgs };
    }),

  regenerateAddThought: (messageId, text) =>
    set((s) => {
      const msgs = s.messages.map((msg) => {
        if (msg.id !== messageId || msg.role !== "assistant") return msg;
        const thoughts = [...(msg.thoughts || []), { text, timestamp: new Date() }];
        return { ...msg, thoughts };
      });
      return { messages: msgs };
    }),

  regenerateAddCitation: (messageId, citation) =>
    set((s) => {
      const msgs = s.messages.map((msg) => {
        if (msg.id !== messageId || msg.role !== "assistant") return msg;
        const exists = msg.citations?.some((item) => item.chunk_id === citation.chunk_id);
        if (exists) return msg;
        const citations = [...(msg.citations || []), citation];
        return { ...msg, citations };
      });
      return { messages: msgs };
    }),

  regenerateAddMediaTask: (messageId, task) =>
    set((s) => ({
      messages: s.messages.map((msg) => {
        if (msg.id !== messageId || msg.role !== "assistant") return msg;
        const existing = msg.mediaTasks || [];
        const mediaTasks = existing.some((item) => item.id === task.id)
          ? existing.map((item) => (item.id === task.id ? task : item))
          : [...existing, task];
        return { ...msg, mediaTasks };
      }),
    })),

  regenerateFinish: (messageId, fullContent, emotion) =>
    set((s) => {
      const msgs = s.messages.map((msg) => {
        if (msg.id !== messageId || msg.role !== "assistant") return msg;
        const newVersion: MessageVersion = {
          content: fullContent,
          toolCalls: msg.toolCalls,
          thoughts: msg.thoughts,
          citations: msg.citations,
          mediaTasks: msg.mediaTasks,
          emotion: emotion || msg.emotion,
          timestamp: new Date(),
        };
        const versions = msg.versions || [];
        return {
          ...msg,
          content: fullContent,
          versions: [...versions, newVersion],
          currentVersionIndex: versions.length,
          emotion: emotion || msg.emotion,
        };
      });
      return {
        messages: msgs,
        streamingContent: "",
        isLoading: false,
        regeneratingMessageId: null,
        abortController: null,
      };
    }),

  switchVersion: (messageId, versionIndex) =>
    set((s) => {
      const msgs = s.messages.map((msg) => {
        if (msg.id !== messageId || msg.role !== "assistant") return msg;
        if (!msg.versions || !msg.versions[versionIndex]) return msg;
        const version = msg.versions[versionIndex];
        return {
          ...msg,
          content: version.content,
          toolCalls: version.toolCalls,
          thoughts: version.thoughts,
          citations: version.citations,
          mediaTasks: version.mediaTasks,
          emotion: version.emotion,
          timestamp: version.timestamp,
          currentVersionIndex: versionIndex,
        };
      });
      return { messages: msgs };
    }),

  setAbortController: (ac) => set({ abortController: ac }),

  abortStream: () => {
    const ac = get().abortController;
    if (ac) {
      ac.abort();
    }
    set({ abortController: null, isLoading: false, streamingContent: "", regeneratingMessageId: null });
  },
}));
