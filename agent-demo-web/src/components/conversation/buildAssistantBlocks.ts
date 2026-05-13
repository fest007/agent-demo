import type { Message } from "@/types";
import type { AssistantBlock } from "./types";

export function buildAssistantBlocks(
  message: Message,
  isThinking: boolean,
  isRegenerating: boolean,
): AssistantBlock[] {
  const blocks: AssistantBlock[] = [];

  if (message.thoughts?.length) {
    blocks.push({ type: "thoughts", thoughts: message.thoughts });
  }
  if (message.toolCalls?.length) {
    blocks.push({ type: "tools", toolCalls: message.toolCalls });
  }
  if (message.mediaTasks?.length) {
    blocks.push({ type: "media", tasks: message.mediaTasks });
  }

  blocks.push({
    type: "answer",
    content: message.content,
    isThinking,
    isRegenerating,
  });

  if (message.citations?.length) {
    blocks.push({ type: "citations", citations: message.citations });
  }

  return blocks;
}
