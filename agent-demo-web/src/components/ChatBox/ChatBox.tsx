import React, { useRef, useEffect } from "react";
import { Layout, Typography, Button } from "antd";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { PlusOutlined, RobotOutlined, MessageOutlined } from "@ant-design/icons";
import { useChat } from "@/hooks/useChat";
import { useSessionStore } from "@/stores/sessionStore";
import { useChatStore } from "@/stores/chatStore";
import { useAppStore } from "@/stores/appStore";
import { createSession } from "@/api/session";
import { MessageBubble } from "../MessageBubble/MessageBubble";
import { InputBar } from "../InputBar/InputBar";
import { EmotionBadge } from "../EmotionBadge/EmotionBadge";
import styles from "./ChatBox.module.css";
import type { Message } from "@/types";

const { Content } = Layout;
const { Text } = Typography;

export const ChatBox: React.FC = () => {
  const { messages, isLoading, streamingContent, currentEmotion, send, regenerate } = useChat();
  const bottomRef = useRef<HTMLDivElement>(null);
  const messagesRef = useRef<HTMLDivElement>(null);
  const messageNodeRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const scrollFrameRef = useRef<number | null>(null);
  const { currentSessionId } = useSessionStore();
  const sessions = useSessionStore((s) => s.sessions);
  const currentSession = sessions.find((s) => s.sessionId === currentSessionId);
  const displayName = currentSession?.name || "智能助手";
  const chatStore = useChatStore();
  const regeneratingMessageId = useChatStore((s) => s.regeneratingMessageId);
  const messageFocus = useAppStore((s) => s.messageFocus);
  const setMessageFocus = useAppStore((s) => s.setMessageFocus);

  const findActiveQuestionId = (items: Message[]) => {
    if (!isLoading) return null;
    if (regeneratingMessageId) {
      const assistantIndex = items.findIndex((msg) => msg.id === regeneratingMessageId);
      for (let i = assistantIndex - 1; i >= 0; i--) {
        if (items[i].role === "user") return items[i].id;
      }
      return null;
    }
    for (let i = items.length - 1; i >= 0; i--) {
      if (items[i].role === "user") return items[i].id;
    }
    return null;
  };

  const activeQuestionId = findActiveQuestionId(messages);

  const scrollUntilQuestionReachesTop = () => {
    const container = messagesRef.current;
    const question = activeQuestionId ? messageNodeRefs.current[activeQuestionId] : null;
    if (!container || !question) return;

    const containerRect = container.getBoundingClientRect();
    const questionRect = question.getBoundingClientRect();
    const distanceToTop = questionRect.top - containerRect.top;

    if (distanceToTop > 1) {
      container.scrollTop += distanceToTop;
    }
  };

  useEffect(() => {
    if (isLoading) {
      scrollUntilQuestionReachesTop();
      return;
    }
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, isLoading, activeQuestionId]);

  useEffect(() => {
    if (!isLoading) return;
    if (scrollFrameRef.current !== null) {
      cancelAnimationFrame(scrollFrameRef.current);
    }
    scrollFrameRef.current = requestAnimationFrame(() => {
      scrollUntilQuestionReachesTop();
    });
    return () => {
      if (scrollFrameRef.current !== null) {
        cancelAnimationFrame(scrollFrameRef.current);
        scrollFrameRef.current = null;
      }
    };
  }, [isLoading, streamingContent]);

  useEffect(() => {
    if (!messageFocus || messageFocus.sessionId !== currentSessionId) return;
    const targetId = messageFocus.messageId;
    if (!targetId) return;
    const node = messageNodeRefs.current[targetId];
    if (!node) return;
    node.scrollIntoView({ behavior: "smooth", block: "center" });
    node.classList.add(styles.focusedMessage);
    window.setTimeout(() => node.classList.remove(styles.focusedMessage), 1800);
    setMessageFocus(null);
  }, [messageFocus, currentSessionId, messages.length, setMessageFocus]);

  const displayMessages = messages.filter((msg) => {
    const hasProcessContext = !!msg.thoughts?.length || !!msg.toolCalls?.length || !!msg.mediaTasks?.length;
    if (
      msg.role === "assistant" &&
      msg.content === "" &&
      isLoading &&
      streamingContent &&
      !hasProcessContext &&
      msg.id !== regeneratingMessageId
    ) {
      return false;
    }
    return true;
  });

  const handleNewChat = async () => {
    try {
      const data = await createSession();
      const newSession = {
        sessionId: data.session_id,
        name: data.name,
        createdAt: new Date(data.created_at),
        updatedAt: new Date(data.updated_at),
      };
      useSessionStore.getState().addSession(newSession);
      useSessionStore.getState().setCurrentSessionId(data.session_id);
      chatStore.clearMessages();
      chatStore.setThreadId(data.session_id);
    } catch {}
  };

  return (
    <Layout className={styles.container}>
      {currentSessionId && (
        <div className={styles.header}>
          <Text className={styles.headerName}>{displayName}</Text>
          {currentEmotion && <EmotionBadge emotion={currentEmotion} />}
        </div>
      )}

      <Content className={styles.messages} ref={messagesRef}>
        {!currentSessionId && (
          <div className={styles.welcome}>
            <div className={styles.welcomeIcon}>
              <RobotOutlined />
            </div>
            <Text className={styles.welcomeTitle}>你好，有什么可以帮你的？</Text>
            <Text className={styles.welcomeSubtitle}>
              我是你的智能助手，可以回答问题、分析文档、执行任务
            </Text>
            <div className={styles.welcomeActions}>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleNewChat}
                className={styles.welcomeButton}
                size="large"
              >
                开始新对话
              </Button>
            </div>
            <div className={styles.hints}>
              {["帮我写一段代码", "解释一个概念", "分析这份文档"].map((hint) => (
                <div key={hint} className={styles.hint} onClick={handleNewChat}>
                  <MessageOutlined className={styles.hintIcon} />
                  {hint}
                </div>
              ))}
            </div>
          </div>
        )}

        {currentSessionId && messages.length === 0 && !isLoading && (
          <div className={styles.welcome}>
            <div className={`${styles.welcomeIcon} ${styles.emptyIcon}`}>
              <MessageOutlined />
            </div>
            <Text className={`${styles.welcomeTitle} ${styles.emptyTitle}`}>
              开始和助手对话吧
            </Text>
            <Text className={styles.welcomeSubtitle}>
              输入你的问题，按 Enter 发送
            </Text>
          </div>
        )}

        {displayMessages.map((msg, index) => {
          let isLatest = false;
          if (msg.role === "assistant") {
            for (let i = displayMessages.length - 1; i >= 0; i--) {
              if (displayMessages[i].role === "assistant") {
                isLatest = displayMessages[i].id === msg.id;
                break;
              }
            }
          }
          return (
            <div
              key={msg.id}
              ref={(node) => {
                messageNodeRefs.current[msg.id] = node;
              }}
              style={{ animationDelay: `${Math.min(index * 0.05, 0.3)}s` }}
            >
              <MessageBubble
                message={msg}
                onRegenerate={regenerate}
                isLatest={isLatest}
              />
            </div>
          );
        })}

        {isLoading && streamingContent && !regeneratingMessageId && (() => {
          const lastMsg = displayMessages[displayMessages.length - 1];
          if (lastMsg?.role === "assistant") return null;
          return (
            <div className={styles.streamingContainer}>
              <div className={styles.streamingAvatar}>
                <RobotOutlined />
              </div>
              <div className={styles.streamingBubble}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {streamingContent}
                </ReactMarkdown>
                <span className={styles.cursor} />
              </div>
            </div>
          );
        })()}

        <div ref={bottomRef} />
      </Content>

      {currentSessionId && <InputBar onSend={send} loading={isLoading} />}
    </Layout>
  );
};
