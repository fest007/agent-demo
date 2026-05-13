import React from "react";
import { Image } from "antd";
import { UserOutlined, RobotOutlined } from "@ant-design/icons";
import { EmotionBadge } from "../EmotionBadge/EmotionBadge";
import { AssistantActions } from "../AssistantActions/AssistantActions";
import { UserActions } from "../UserActions/UserActions";
import { AssistantContentRenderer } from "../conversation/AssistantContentRenderer/AssistantContentRenderer";
import { formatTime } from "@/utils/formatTime";
import { useChatStore } from "@/stores/chatStore";
import type { Message } from "@/types";
import styles from "./MessageBubble.module.css";

interface Props {
  message: Message;
  onRegenerate: (messageId: string) => void;
  isLatest: boolean;
}

export const MessageBubble: React.FC<Props> = ({ message, onRegenerate, isLatest }) => {
  const isUser = message.role === "user";
  const regeneratingMessageId = useChatStore((s) => s.regeneratingMessageId);
  const isLoading = useChatStore((s) => s.isLoading);
  const setPendingEdit = useChatStore((s) => s.setPendingEdit);
  const isRegenerating = regeneratingMessageId === message.id;

  const isThinking = !isUser && !message.content && isLoading && !isRegenerating;

  const handleEdit = () => {
    setPendingEdit(message.content);
  };

  const forceShowActions = !isUser && isLatest && !isLoading && !!message.content && !isRegenerating;

  return (
    <div className={`${styles.row} ${isUser ? styles.rowUser : styles.rowAssistant}`}>
      {!isUser && (
        <div className={`${styles.avatar} ${styles.avatarAssistant}`}>
          <RobotOutlined />
        </div>
      )}

      <div className={styles.contentWrapper}>
        {!isUser && message.emotion && (
          <div className={styles.emotion}>
            <EmotionBadge emotion={message.emotion} />
          </div>
        )}

        {isUser ? (
          <div className={`${styles.bubble} ${styles.userBubble}`}>
            {message.images && message.images.length > 0 && (
              <div className={styles.images}>
                <Image.PreviewGroup>
                  {message.images.map((src, i) => (
                    <Image key={i} src={src} width={80} height={80} className={styles.image} />
                  ))}
                </Image.PreviewGroup>
              </div>
            )}
            {message.content}
          </div>
        ) : (
          <AssistantContentRenderer
            message={message}
            isThinking={isThinking}
            isRegenerating={isRegenerating}
          />
        )}

        {!isThinking && (
          <div className={`${styles.time} ${isUser ? styles.timeUser : styles.timeAssistant}`}>
            {formatTime(message.timestamp)}
          </div>
        )}

        {isUser && (
          <UserActions
            message={message}
            onEdit={handleEdit}
            className={styles.userActions}
          />
        )}

        {!isUser && message.content && !isRegenerating && (
          <AssistantActions
            message={message}
            onRegenerate={() => onRegenerate(message.id)}
            isRegenerating={!!regeneratingMessageId}
            forceShow={forceShowActions}
            className={styles.assistantActions}
          />
        )}
      </div>

      {isUser && (
        <div className={`${styles.avatar} ${styles.avatarUser}`}>
          <UserOutlined />
        </div>
      )}
    </div>
  );
};
