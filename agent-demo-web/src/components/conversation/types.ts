import type { KnowledgeCitation, MediaTask, ThoughtStep, ToolCall } from "@/types";

export type AssistantBlock =
  | { type: "thoughts"; thoughts: ThoughtStep[] }
  | { type: "tools"; toolCalls: ToolCall[] }
  | { type: "media"; tasks: MediaTask[] }
  | { type: "answer"; content: string; isThinking: boolean; isRegenerating: boolean }
  | { type: "citations"; citations: KnowledgeCitation[] };
