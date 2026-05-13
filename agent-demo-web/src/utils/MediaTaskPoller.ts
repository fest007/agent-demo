import { getHistory } from "@/api/chat";
import { getMediaTask } from "@/api/media";
import { useAppStore } from "@/stores/appStore";
import { useChatStore } from "@/stores/chatStore";
import { useSessionStore } from "@/stores/sessionStore";
import type { MediaTask } from "@/types";
import { historyToMessages } from "./history";

type MediaTaskListener = (task: MediaTask) => void;
const NOTIFIED_TASKS_KEY = "agent-demo-media-notified-tasks";

function readNotifiedTaskIds(): Set<string> {
  try {
    return new Set(JSON.parse(localStorage.getItem(NOTIFIED_TASKS_KEY) || "[]"));
  } catch {
    return new Set();
  }
}

function markTaskNotified(taskId: string) {
  const ids = readNotifiedTaskIds();
  ids.add(taskId);
  try {
    localStorage.setItem(NOTIFIED_TASKS_KEY, JSON.stringify(Array.from(ids).slice(-300)));
  } catch {}
}

export class MediaTaskPoller {
  private timers = new Map<string, number>();
  private listeners = new Map<string, Set<MediaTaskListener>>();

  watch(task: MediaTask, listener?: MediaTaskListener) {
    if (listener) {
      const set = this.listeners.get(task.id) || new Set<MediaTaskListener>();
      set.add(listener);
      this.listeners.set(task.id, set);
    }

    useChatStore.getState().updateMediaTask(task);

    if (this.isTerminal(task.status)) {
      this.notify(task);
      return;
    }
    if (this.timers.has(task.id)) return;

    const tick = async () => {
      try {
        const latest = await getMediaTask(task.id);
        useChatStore.getState().updateMediaTask(latest);
        this.emit(latest);
        if (this.isTerminal(latest.status)) {
          this.stop(latest.id);
          this.notify(latest);
        }
      } catch {
        // Keep the timer alive; transient network errors should not orphan tasks.
      }
    };

    void tick();
    this.timers.set(task.id, window.setInterval(tick, 3000));
  }

  stop(taskId: string) {
    const timer = this.timers.get(taskId);
    if (timer) window.clearInterval(timer);
    this.timers.delete(taskId);
    this.listeners.delete(taskId);
  }

  stopAll() {
    for (const id of this.timers.keys()) this.stop(id);
  }

  private emit(task: MediaTask) {
    for (const listener of this.listeners.get(task.id) || []) {
      listener(task);
    }
  }

  private isTerminal(status: string) {
    return status === "succeeded" || status === "failed";
  }

  private notify(task: MediaTask) {
    if (readNotifiedTaskIds().has(task.id)) return;
    markTaskNotified(task.id);
    const ok = task.status === "succeeded";
    useAppStore.getState().pushMediaNotification({
      id: task.id,
      title: ok ? "媒体生成完成" : "媒体生成失败",
      description: ok ? "点击查看生成结果。" : task.error || "点击查看任务详情。",
      status: ok ? "success" : "error",
      sessionId: task.thread_id,
      conversationId: task.conversation_id,
      messageId: task.conversation_id ? `hist_${task.conversation_id}` : undefined,
    });
  }
}

export const mediaTaskPoller = new MediaTaskPoller();

export async function jumpToMediaTask(task: MediaTask) {
  const sessionId = task.thread_id;
  useSessionStore.getState().setCurrentSessionId(sessionId);
  useAppStore.getState().setCurrentPage("chat");
  try {
    const history = await getHistory(sessionId);
    useChatStore.getState().loadSession(sessionId, historyToMessages(history));
  } catch {}
  useAppStore.getState().setMessageFocus({
    sessionId,
    conversationId: task.conversation_id,
    messageId: task.conversation_id ? `hist_${task.conversation_id}` : undefined,
  });
}
