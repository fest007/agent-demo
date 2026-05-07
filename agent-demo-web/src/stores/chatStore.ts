/**
 * 对话状态管理（Zustand）
 *
 * Zustand 是一个轻量级的 React 状态管理库，
 * 比 Redux 更简单，不需要 Provider、Action、Reducer。
 *
 * 核心概念：
 * - State: 状态数据（messages, isLoading 等）
 * - Action: 修改状态的方法（addMessage, setLoading 等）
 * - useChatStore: 自定义 Hook，用于在组件中访问状态
 *
 * 使用方式：
 *   const messages = useChatStore((s) => s.messages);
 *   const addMessage = useChatStore((s) => s.addMessage);
 */
import { create } from "zustand";
import type { Message, ToolCall } from "@/types";

/**
 * 对话状态接口定义
 */
interface ChatState {
  // ===== 状态数据 =====
  messages: Message[];       // 消息列表
  threadId: string;          // 当前会话 ID
  isLoading: boolean;        // 是否正在等待 Agent 回复
  streamingContent: string;  // 流式输出的临时内容（正在生成中的文本）
  currentEmotion: string;    // 当前用户情绪

  // ===== 修改状态的方法 =====
  addMessage: (msg: Message) => void;           // 添加新消息
  updateLastAssistant: (content: string) => void; // 更新最后一条 Agent 消息的内容
  setThreadId: (id: string) => void;            // 设置会话 ID
  setLoading: (v: boolean) => void;             // 设置加载状态
  setStreamingContent: (s: string) => void;     // 设置流式内容
  setCurrentEmotion: (e: string) => void;       // 设置当前情绪
  clearMessages: () => void;                    // 清空消息列表
  appendStreamToken: (token: string) => void;   // 追加一个 token 到流式内容
  addToolCall: (tc: ToolCall) => void;          // 添加工具调用记录
  loadSession: (sessionId: string, messages: Message[]) => void; // 加载会话
}

/**
 * 创建 Zustand store
 *
 * create() 接收一个函数，返回初始状态和所有 action。
 * set() 用于更新状态，接收一个函数，参数是当前状态，返回新状态。
 */
export const useChatStore = create<ChatState>((set) => ({
  // 初始状态
  messages: [],
  threadId: "",
  isLoading: false,
  streamingContent: "",
  currentEmotion: "neutral",

  // 添加消息：展开现有消息数组，追加新消息
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),

  // 更新最后一条 Agent 消息的内容
  // 流式输出结束后调用，将 streamingContent 写入消息
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

  // 追加 token：将新 token 拼接到 streamingContent 末尾
  appendStreamToken: (token) =>
    set((s) => ({ streamingContent: s.streamingContent + token })),

  // 添加工具调用：追加到最后一条 Agent 消息的 toolCalls 数组
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

  // 加载会话：切换 threadId 并加载历史消息
  loadSession: (sessionId, messages) =>
    set({
      threadId: sessionId,
      messages,
      streamingContent: "",
      currentEmotion: "neutral",
      isLoading: false,
    }),
}));
