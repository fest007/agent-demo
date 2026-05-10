export interface MessageVersion {
  content: string;
  toolCalls?: ToolCall[];
  emotion?: string;
  timestamp: Date;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  emotion?: string;
  timestamp: Date;
  toolCalls?: ToolCall[];
  images?: string[];
  versions?: MessageVersion[];
  currentVersionIndex?: number;
}

export interface ToolCall {
  name: string;
  input: string;
  output?: string;
}

export interface ChatResponse {
  content: string;
  emotion: string;
  thread_id: string;
  tools_used: string[];
}

export interface KnowledgeDocument {
  source: string;
  type: string;
}

export interface SkillInfo {
  name: string;
  description: string;
  content: string;
  is_builtin: boolean;
  created_at: string;
}

export interface StreamEvent {
  type: "emotion" | "token" | "tool_start" | "tool_end" | "done";
  data: string | object;
}
