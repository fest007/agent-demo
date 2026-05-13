import { useCallback } from "react";
import { useChatStore } from "@/stores/chatStore";
import { useSessionStore } from "@/stores/sessionStore";
import { useAppStore } from "@/stores/appStore";
import { streamMessage } from "@/api/chat";
import { summarizeSession } from "@/api/session";
import { mediaTaskPoller } from "@/utils/MediaTaskPoller";
import type { MediaTask, Message } from "@/types";

function wait(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function createMarkdownTokenFlusher(append: (text: string) => void, charsPerSecond: number) {
  let buffer = "";
  let timer: ReturnType<typeof window.setInterval> | null = null;
  const interval = 32;
  const charsPerTick = Math.max(1, Math.round((Math.max(20, charsPerSecond) * interval) / 1000));

  const flushOnce = () => {
    if (!buffer) {
      if (timer) {
        window.clearInterval(timer);
        timer = null;
      }
      return;
    }
    const chunk = buffer.slice(0, charsPerTick);
    buffer = buffer.slice(charsPerTick);
    append(chunk);
  };

  const start = () => {
    if (!timer) timer = window.setInterval(flushOnce, interval);
  };

  return {
    push(text: string) {
      if (!text) return;
      buffer += text;
      start();
    },
    async drain() {
      while (buffer) {
        flushOnce();
        await wait(interval);
      }
      if (timer) {
        window.clearInterval(timer);
        timer = null;
      }
    },
    stop() {
      buffer = "";
      if (timer) {
        window.clearInterval(timer);
        timer = null;
      }
    },
  };
}

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

      let flusher: ReturnType<typeof createMarkdownTokenFlusher> | null = null;
      try {
        let fullContent = "";
        const modelSelection = useAppStore.getState().modelSelection;
        flusher = createMarkdownTokenFlusher(
          (token) => store.appendStreamToken(token),
          useAppStore.getState().markdownTypingSpeed,
        );
        for await (const event of streamMessage(content, store.threadId, images, ac.signal, modelSelection)) {
          if (event.type === "emotion") {
            store.setCurrentEmotion(event.data as string);
          } else if (event.type === "thought") {
            store.addThought(event.data as string);
          } else if (event.type === "citation") {
            store.addCitation(event.data as any);
          } else if (event.type === "media_task") {
            const task = event.data as MediaTask;
            store.addMediaTask(task);
            mediaTaskPoller.watch(task, (latest) => store.updateMediaTask(latest));
          } else if (event.type === "token") {
            fullContent += event.data as string;
            flusher.push(event.data as string);
          } else if (event.type === "error") {
            store.addThought("模型调用失败，错误信息已展示在回答正文中。");
          } else if (event.type === "tool_start") {
            const toolData = event.data as any;
            const inputStr =
              typeof toolData.input === "object"
                ? JSON.stringify(toolData.input, null, 2)
                : String(toolData.input ?? "");
            store.addToolCall({ name: toolData.name, input: inputStr });
          } else if (event.type === "tool_end") {
            const toolData = event.data as any;
            store.updateLastToolCall(
              typeof toolData.name === "string" ? toolData.name : undefined,
              String(toolData.output ?? "")
            );
          }
        }
        await flusher.drain();

        store.updateLastAssistant(fullContent);

        const currentSessionId = useSessionStore.getState().currentSessionId;
        if (currentSessionId) {
          const session = useSessionStore
            .getState()
            .sessions.find((s) => s.sessionId === currentSessionId);
          if (session?.name === "新对话") {
            summarizeSession(currentSessionId, modelSelection)
              .then((updated) => {
                useSessionStore
                  .getState()
                  .updateSessionName(currentSessionId, updated.name);
              })
              .catch(() => {});
          }
        }
      } catch (err: any) {
        flusher?.stop();
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

      let flusher: ReturnType<typeof createMarkdownTokenFlusher> | null = null;
      try {
        let fullContent = "";
        let emotion = "";
        const modelSelection = useAppStore.getState().modelSelection;
        flusher = createMarkdownTokenFlusher(
          (token) => store.regenerateStreamToken(messageId, token),
          useAppStore.getState().markdownTypingSpeed,
        );
        for await (const event of streamMessage(
          userContent,
          store.threadId,
          userImages,
          ac.signal,
          modelSelection
        )) {
          if (event.type === "emotion") {
            emotion = event.data as string;
            store.setCurrentEmotion(emotion);
          } else if (event.type === "thought") {
            store.regenerateAddThought(messageId, event.data as string);
          } else if (event.type === "citation") {
            store.regenerateAddCitation(messageId, event.data as any);
          } else if (event.type === "media_task") {
            const task = event.data as MediaTask;
            store.regenerateAddMediaTask(messageId, task);
            mediaTaskPoller.watch(task, (latest) => store.updateMediaTask(latest));
          } else if (event.type === "token") {
            fullContent += event.data as string;
            flusher.push(event.data as string);
          } else if (event.type === "error") {
            store.regenerateAddThought(messageId, "模型调用失败，错误信息已展示在回答正文中。");
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
          } else if (event.type === "tool_end") {
            const toolData = event.data as any;
            store.regenerateUpdateToolCall(
              messageId,
              typeof toolData.name === "string" ? toolData.name : undefined,
              String(toolData.output ?? "")
            );
          }
        }
        await flusher.drain();

        store.regenerateFinish(messageId, fullContent, emotion);
      } catch (err: any) {
        flusher?.stop();
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
