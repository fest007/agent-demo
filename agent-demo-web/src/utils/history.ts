import type { ChatHistoryItem, Message } from "@/types";

export function historyToMessages(history: ChatHistoryItem[]): Message[] {
  return history.map((h, i) => ({
    id: h.id ? `hist_${h.id}` : `hist_${i}_${Date.now()}`,
    role: h.role,
    content: h.content,
    emotion: h.emotion ?? undefined,
    timestamp: new Date(h.timestamp),
    toolCalls: h.toolCalls,
    thoughts: h.thoughts?.map((thought) => ({
      text: thought.text,
      timestamp: new Date(thought.timestamp),
    })),
    citations: h.citations,
    mediaTasks: h.mediaTasks,
  }));
}
