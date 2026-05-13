export interface MessageVersion {
  content: string;
  toolCalls?: ToolCall[];
  thoughts?: ThoughtStep[];
  citations?: KnowledgeCitation[];
  mediaTasks?: MediaTask[];
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
  thoughts?: ThoughtStep[];
  citations?: KnowledgeCitation[];
  mediaTasks?: MediaTask[];
  images?: string[];
  versions?: MessageVersion[];
  currentVersionIndex?: number;
}

export interface ThoughtStep {
  text: string;
  timestamp: Date;
}

export interface ToolCall {
  name: string;
  input: string;
  output?: string;
}

export interface KnowledgeCitation {
  id: string;
  source: string;
  title: string;
  type: string;
  chunk_id: string;
  chunk_index: number;
  excerpt: string;
  score?: number;
}

export interface MediaTask {
  id: string;
  thread_id: string;
  conversation_id?: number | null;
  provider: string;
  model: string;
  task_type: "image" | "video" | string;
  mode: string;
  prompt: string;
  status: "pending" | "running" | "succeeded" | "failed" | string;
  progress: number;
  external_task_id?: string | null;
  input_images?: string[];
  result_urls?: string[];
  error?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  completed_at?: string | null;
}

export interface ChatResponse {
  content: string;
  emotion: string;
  thread_id: string;
  tools_used: string[];
}

export interface ChatHistoryItem {
  id?: string | null;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  emotion?: string | null;
  toolCalls?: ToolCall[];
  thoughts?: Array<{ text: string; timestamp: string }>;
  citations?: KnowledgeCitation[];
  mediaTasks?: MediaTask[];
}

export interface KnowledgeDocument {
  source: string;
  type: string;
  title?: string;
  content_length?: number;
  extraction_quality?: string;
  extraction_note?: string;
  chunks?: number;
}

export interface KnowledgeChunk {
  chunk_id: string;
  chunk_index: number;
  content: string;
  source: string;
  title: string;
  type: string;
  extraction_quality?: string;
  extraction_note?: string;
}

export interface SkillInfo {
  name: string;
  description: string;
  content: string;
  is_builtin: boolean;
  created_at: string;
}

export interface StreamEvent {
  type: "emotion" | "thought" | "citation" | "token" | "tool_start" | "tool_end" | "media_task" | "error" | "done";
  data: string | object;
}
