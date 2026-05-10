import { useCallback } from "react";
import { useChatStore } from "@/stores/chatStore";
import { useSessionStore } from "@/stores/sessionStore";
import { streamMessage } from "@/api/chat";
import { summarizeSession } from "@/api/session";
import type { Message } from "@/types";

export function useChat() {
  const store = useChatStore();

  const send = useCallback(
    async (content: string, images?: string[]) => {
      const userMsg: Message = {
        id: Date.now().toString(),
        role: "user",
        content,
        timestamp: new Date(),
        images,
      };
      store.addMessage(userMsg);
      store.setLoading(true);
      store.setStreamingContent("");

      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "",
        timestamp: new Date(),
      };
      store.addMessage(assistantMsg);

      const ac = new AbortController();
      store.setAbortController(ac);

      try {
        let fullContent = "";
        for await (const event of streamMessage(content, store.threadId, images, ac.signal)) {
          if (event.type === "emotion") {
            store.setCurrentEmotion(event.data as string);
          } else if (event.type === "token") {
            fullContent += event.data as string;
            store.appendStreamToken(event.data as string);
          } else if (event.type === "tool_start") {
            const toolData = event.data as any;
            const inputStr =
              typeof toolData.input === "object"
                ? JSON.stringify(toolData.input, null, 2)
                : String(toolData.input ?? "");
            store.addToolCall({ name: toolData.name, input: inputStr });
          }
        }

        store.updateLastAssistant(fullContent);

        const currentSessionId = useSessionStore.getState().currentSessionId;
        if (currentSessionId) {
          const session = useSessionStore
            .getState()
            .sessions.find((s) => s.sessionId === currentSessionId);
          if (session?.name === "新对话") {
            summarizeSession(currentSessionId)
              .then((updated) => {
                useSessionStore
                  .getState()
                  .updateSessionName(currentSessionId, updated.name);
              })
              .catch(() => {});
          }
        }
      } catch (err: any) {
        if (err?.name === "AbortError") {
          // User stopped — keep whatever content was generated so far
          const msgs = store.messages;
          const last = msgs[msgs.length - 1];
          if (last?.role === "assistant" && last.content) {
            // Keep the partial content
          } else {
            // No content generated yet — remove the empty assistant message
            store.updateLastAssistant("(已停止)");
          }
        } else {
          store.updateLastAssistant(`错误: ${err}`);
        }
      } finally {
        store.setLoading(false);
        store.setStreamingContent("");
        store.setAbortController(null);
      }
    },
    [store]
  );

  const regenerate = useCallback(
    async (messageId: string) => {
      const messages = store.messages;
      const msgIndex = messages.findIndex((m) => m.id === messageId);
      if (msgIndex < 0) return;

      const assistantMsg = messages[msgIndex];
      if (assistantMsg.role !== "assistant") return;

      let userContent = "";
      let userImages: string[] | undefined;
      for (let i = msgIndex - 1; i >= 0; i--) {
        if (messages[i].role === "user") {
          userContent = messages[i].content;
          userImages = messages[i].images;
          break;
        }
      }
      if (!userContent) return;

      store.saveCurrentVersion(messageId);
      store.regenerateStart(messageId);

      const ac = new AbortController();
      store.setAbortController(ac);

      try {
        let fullContent = "";
        let emotion = "";
        for await (const event of streamMessage(
          userContent,
          store.threadId,
          userImages,
          ac.signal
        )) {
          if (event.type === "emotion") {
            emotion = event.data as string;
            store.setCurrentEmotion(emotion);
          } else if (event.type === "token") {
            fullContent += event.data as string;
            store.regenerateStreamToken(messageId, event.data as string);
          } else if (event.type === "tool_start") {
            const toolData = event.data as any;
            const inputStr =
              typeof toolData.input === "object"
                ? JSON.stringify(toolData.input, null, 2)
                : String(toolData.input ?? "");
            store.regenerateAddToolCall(messageId, {
              name: toolData.name,
              input: inputStr,
            });
          }
        }

        store.regenerateFinish(messageId, fullContent, emotion);
      } catch (err: any) {
        if (err?.name === "AbortError") {
          // Keep partial content on abort
          store.regenerateFinish(messageId, store.messages.find(m => m.id === messageId)?.content || "(已停止)", "");
        } else {
          store.regenerateFinish(messageId, `错误: ${err}`);
        }
      }
    },
    [store]
  );

  return { ...store, send, regenerate };
}
