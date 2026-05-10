import React from "react";
import { Image } from "antd";
import { UserOutlined, RobotOutlined } from "@ant-design/icons";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { EmotionBadge } from "./EmotionBadge";
import { ToolCallCard } from "./ToolCallCard";
import { AssistantActions } from "./AssistantActions";
import { UserActions } from "./UserActions";
import { formatTime } from "@/utils/formatTime";
import { useChatStore } from "@/stores/chatStore";
import type { Message } from "@/types";

interface Props {
  message: Message;
  onRegenerate: (messageId: string) => void;
  isLatest: boolean;
}

export const MessageBubble: React.FC<Props> = ({ message, onRegenerate, isLatest }) => {
  const isUser = message.role === "user";
  const regeneratingMessageId = useChatStore((s) => s.regeneratingMessageId);
  const isLoading = useChatStore((s) => s.isLoading);
  const streamingContent = useChatStore((s) => s.streamingContent);
  const setPendingEdit = useChatStore((s) => s.setPendingEdit);
  const isRegenerating = regeneratingMessageId === message.id;

  // This is an empty assistant message waiting for first token
  const isThinking = !isUser && !message.content && isLoading && !isRegenerating;

  const handleEdit = () => {
    setPendingEdit(message.content);
  };

  // Latest assistant message's actions are always visible
  const forceShowActions = !isUser && isLatest && !isLoading && !!message.content && !isRegenerating;

  return (
    <div className={`message-row message-row-${isUser ? "user" : "assistant"}`}>
      {/* Assistant avatar */}
      {!isUser && (
        <div className="message-avatar message-avatar-assistant">
          <RobotOutlined />
        </div>
      )}

      {/* Content */}
      <div className="message-content-wrapper">
        {/* Emotion badge */}
        {!isUser && message.emotion && (
          <div className="message-emotion">
            <EmotionBadge emotion={message.emotion} />
          </div>
        )}

        {/* Bubble */}
        <div className={`message-bubble message-bubble-${isUser ? "user" : "assistant"}`}>
          {isUser && message.images && message.images.length > 0 && (
            <div className="message-images">
              <Image.PreviewGroup>
                {message.images.map((src, i) => (
                  <Image key={i} src={src} width={80} height={80} className="message-image" />
                ))}
              </Image.PreviewGroup>
            </div>
          )}

          {isUser ? (
            message.content
          ) : isThinking ? (
            /* Thinking indicator inside the bubble */
            <div className="loading-dots" style={{ padding: "4px 0" }}>
              <div className="loading-dot" />
              <div className="loading-dot" />
              <div className="loading-dot" />
            </div>
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          )}

          {isRegenerating && <span className="streaming-cursor" />}
        </div>

        {/* Timestamp — hide during thinking */}
        {!isThinking && (
          <div className={`message-time message-time-${isUser ? "user" : "assistant"}`}>
            {formatTime(message.timestamp)}
          </div>
        )}

        {/* Tool calls */}
        {!isUser && message.toolCalls && message.toolCalls.length > 0 && (
          <ToolCallCard toolCalls={message.toolCalls} />
        )}

        {/* User actions — below bubble, visible on hover */}
        {isUser && <UserActions message={message} onEdit={handleEdit} />}

        {/* Assistant actions — below bubble */}
        {!isUser && message.content && !isRegenerating && (
          <AssistantActions
            message={message}
            onRegenerate={() => onRegenerate(message.id)}
            isRegenerating={!!regeneratingMessageId}
            forceShow={forceShowActions}
          />
        )}
      </div>

      {/* User avatar */}
      {isUser && (
        <div className="message-avatar message-avatar-user">
          <UserOutlined />
        </div>
      )}
    </div>
  );
};
