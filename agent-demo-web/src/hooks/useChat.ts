/**
 * useChat Hook
 *
 * 封装了对话的核心逻辑，包括：
 * 1. 发送消息
 * 2. 接收流式响应
 * 3. 管理消息列表状态
 * 4. 处理情绪、工具调用等事件
 *
 * 使用方式：
 *   const { messages, isLoading, send } = useChat();
 *   send("你好");
 */
import { useCallback } from "react";
import { useChatStore } from "@/stores/chatStore";
import { useSessionStore } from "@/stores/sessionStore";
import { sendMessage, streamMessage } from "@/api/chat";
import { summarizeSession } from "@/api/session";
import type { Message } from "@/types";

export function useChat() {
  // 从 Zustand store 获取状态和方法
  const store = useChatStore();

  /**
   * 发送消息并处理流式响应
   *
   * 流程：
   * 1. 创建用户消息，添加到消息列表
   * 2. 创建空的 Agent 消息（占位）
   * 3. 调用流式 API，逐 token 更新 Agent 消息
   * 4. 流结束后，将完整内容写入 Agent 消息
   */
  const send = useCallback(
    async (content: string) => {
      // 第一步：创建用户消息
      const userMsg: Message = {
        id: Date.now().toString(),
        role: "user",
        content,
        timestamp: new Date(),
      };
      store.addMessage(userMsg);
      store.setLoading(true);
      store.setStreamingContent("");

      // 第二步：创建空的 Agent 消息（占位，内容会逐步填充）
      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "",
        timestamp: new Date(),
      };
      store.addMessage(assistantMsg);

      try {
        // 第三步：处理流式事件
        // 用局部变量累积内容，避免 store 引用过期
        let fullContent = "";
        for await (const event of streamMessage(content, store.threadId)) {
          if (event.type === "emotion") {
            store.setCurrentEmotion(event.data as string);
          } else if (event.type === "token") {
            fullContent += event.data as string;
            store.appendStreamToken(event.data as string);
          } else if (event.type === "tool_start") {
            const toolData = event.data as any;
            // input 可能是对象或字符串，统一格式化为可读的 JSON
            const inputStr = typeof toolData.input === "object"
              ? JSON.stringify(toolData.input, null, 2)
              : String(toolData.input ?? "");
            store.addToolCall({
              name: toolData.name,
              input: inputStr,
            });
          }
        }

        // 第四步：流结束后，将完整内容写入 Agent 消息
        store.updateLastAssistant(fullContent);

        // 第五步：如果是新会话的第一轮对话，触发 LLM 总结命名
        const currentSessionId = useSessionStore.getState().currentSessionId;
        if (currentSessionId) {
          const session = useSessionStore.getState().sessions.find(
            (s) => s.sessionId === currentSessionId
          );
          if (session?.name === "新对话") {
            summarizeSession(currentSessionId)
              .then((updated) => {
                useSessionStore.getState().updateSessionName(
                  currentSessionId,
                  updated.name
                );
              })
              .catch(() => {});
          }
        }
      } catch (err) {
        store.updateLastAssistant(`错误: ${err}`);
      } finally {
        store.setLoading(false);
        store.setStreamingContent("");
      }
    },
    [store]
  );

  // 返回 store 的所有状态 + send 方法
  return { ...store, send };
}
