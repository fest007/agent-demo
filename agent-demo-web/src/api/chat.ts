/**
 * 对话 API 封装
 *
 * 提供三个函数：
 * - sendMessage(): 同步对话（等待完整回复）
 * - streamMessage(): 流式对话（AsyncGenerator，逐事件返回）
 * - getHistory(): 获取会话历史
 *
 * 流式对话使用 Server-Sent Events (SSE) 协议。
 * SSE 格式：每条消息由 "event:" 和 "data:" 两行组成，以空行分隔。
 */
import { api } from "./client";
import type { ChatResponse, ChatHistoryItem } from "@/types";
import type { ModelSelection } from "@/stores/appStore";

function modelPayload(selection?: ModelSelection) {
  const customBaseUrl = selection?.customBaseUrl?.trim();
  const customApiKey = selection?.customApiKey?.trim();
  return {
    model_provider: selection?.providerId,
    model: selection?.modelId,
    image_model: selection?.imageModelId,
    video_model: selection?.videoModelId,
    api_key_id: selection?.apiKeyId,
    custom_base_url: customBaseUrl || undefined,
    custom_api_key: customApiKey || undefined,
  };
}

/**
 * 同步发送消息（等待完整回复）
 */
export async function sendMessage(
  message: string,
  threadId: string = "default",
  enableTts: boolean = false,
  images: string[] = [],
  selection?: ModelSelection
): Promise<ChatResponse> {
  return api.post("/chat", {
    message,
    thread_id: threadId,
    enable_tts: enableTts,
    images,
    ...modelPayload(selection),
  });
}

/**
 * 获取会话历史
 */
export async function getHistory(threadId: string): Promise<ChatHistoryItem[]> {
  return api.get(`/chat/history/${threadId}`);
}

/**
 * 流式发送消息（AsyncGenerator）
 *
 * 使用 fetch API 手动解析 SSE 流。
 * 返回一个 AsyncGenerator，可以用 for await...of 遍历。
 *
 * SSE 协议格式：
 * ```
 * event: token
 * data: "你"
 *
 * event: token
 * data: "好"
 *
 * event: done
 * data: ""
 * ```
 *
 * @yields { type: string, data: string | object } - 解析后的事件
 */
export async function* streamMessage(
  message: string,
  threadId: string = "default",
  images: string[] = [],
  signal?: AbortSignal,
  selection?: ModelSelection
): AsyncGenerator<{ type: string; data: string | object }> {
  // 发送 POST 请求到流式端点
  const resp = await fetch("/api/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, thread_id: threadId, images, ...modelPayload(selection) }),
    signal,
  });

  if (!resp.body) throw new Error("No response body");

  // 获取 ReadableStream 的 reader
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // 统一换行符（服务器可能返回 \r\n 或 \n）
    buffer = buffer.replace(/\r\n/g, "\n");

    // SSE 事件以空行（\n\n）分隔
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";  // 最后一段可能不完整，保留到下次

    for (const part of parts) {
      let eventType = "";
      let dataLine = "";

      for (const line of part.split("\n")) {
        if (line.startsWith("event:")) {
          eventType = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          dataLine = line.slice(5).trim();
        }
      }

      if (eventType && dataLine) {
        try {
          const data = JSON.parse(dataLine);
          yield { type: eventType, data };
        } catch {
          // JSON 解析失败，跳过
        }
      }
    }
  }

  // 流结束时，处理缓冲区中剩余的数据
  if (buffer.trim()) {
    buffer = buffer.replace(/\r\n/g, "\n");
    const parts = buffer.split("\n\n");
    for (const part of parts) {
      let eventType = "";
      let dataLine = "";
      for (const line of part.split("\n")) {
        if (line.startsWith("event:")) {
          eventType = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          dataLine = line.slice(5).trim();
        }
      }
      if (eventType && dataLine) {
        try {
          const data = JSON.parse(dataLine);
          yield { type: eventType, data };
        } catch {}
      }
    }
  }
}
