import React from "react";
import type { Message } from "@/types";
import { ToolCallCard } from "../../ToolCallCard/ToolCallCard";
import { AnswerBlock } from "../AnswerBlock/AnswerBlock";
import { CitationBlock } from "../CitationBlock/CitationBlock";
import { ThoughtBlock } from "../ThoughtBlock/ThoughtBlock";
import { MediaBlock } from "../MediaBlock/MediaBlock";
import { buildAssistantBlocks } from "../buildAssistantBlocks";

export const AssistantContentRenderer: React.FC<{
  message: Message;
  isThinking: boolean;
  isRegenerating: boolean;
}> = ({ message, isThinking, isRegenerating }) => {
  const blocks = buildAssistantBlocks(message, isThinking, isRegenerating);

  return (
    <>
      {blocks.map((block) => {
        switch (block.type) {
          case "thoughts":
            return <ThoughtBlock key="thoughts" thoughts={block.thoughts} />;
          case "tools":
            return <ToolCallCard key="tools" toolCalls={block.toolCalls} />;
          case "media":
            return <MediaBlock key="media" tasks={block.tasks} />;
          case "answer":
            return (
              <AnswerBlock
                key="answer"
                content={block.content}
                isThinking={block.isThinking}
                isRegenerating={block.isRegenerating}
              />
            );
          case "citations":
            return <CitationBlock key="citations" citations={block.citations} />;
          default:
            return null;
        }
      })}
    </>
  );
};
