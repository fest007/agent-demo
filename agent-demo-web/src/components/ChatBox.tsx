import React, { useRef, useEffect } from "react";
import { Layout, Typography, Button } from "antd";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { PlusOutlined, RobotOutlined, MessageOutlined } from "@ant-design/icons";
import { useChat } from "@/hooks/useChat";
import { useSessionStore } from "@/stores/sessionStore";
import { useChatStore } from "@/stores/chatStore";
import { createSession } from "@/api/session";
import { MessageBubble } from "./MessageBubble";
import { InputBar } from "./InputBar";
import { EmotionBadge } from "./EmotionBadge";

const { Content } = Layout;
const { Text } = Typography;

export const ChatBox: React.FC = () => {
  const { messages, isLoading, streamingContent, currentEmotion, send, regenerate } = useChat();
  const bottomRef = useRef<HTMLDivElement>(null);
  const { currentSessionId } = useSessionStore();
  const sessions = useSessionStore((s) => s.sessions);
  const currentSession = sessions.find((s) => s.sessionId === currentSessionId);
  const displayName = currentSession?.name || "智能助手";
  const chatStore = useChatStore();
  const regeneratingMessageId = useChatStore((s) => s.regeneratingMessageId);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  // Filter: hide empty assistant placeholder during normal streaming (not regeneration)
  const displayMessages = messages.filter((msg) => {
    if (msg.role === "assistant" && msg.content === "" && isLoading && streamingContent && msg.id !== regeneratingMessageId) {
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
    <Layout className="chat-container">
      {/* Header */}
      {currentSessionId && (
        <div className="chat-header">
          <Text className="chat-header-name">{displayName}</Text>
          {currentEmotion && <EmotionBadge emotion={currentEmotion} />}
        </div>
      )}

      {/* Messages */}
      <Content className="chat-messages">
        {/* Welcome */}
        {!currentSessionId && (
          <div className="welcome-container">
            <div className="welcome-icon">
              <RobotOutlined />
            </div>
            <Text className="welcome-title">你好，有什么可以帮你的？</Text>
            <Text className="welcome-subtitle">
              我是你的智能助手，可以回答问题、分析文档、执行任务
            </Text>
            <div className="welcome-actions">
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleNewChat}
                className="welcome-action-btn welcome-action-btn-primary"
                size="large"
              >
                开始新对话
              </Button>
            </div>
            <div className="welcome-hints">
              {["帮我写一段代码", "解释一个概念", "分析这份文档"].map((hint) => (
                <div key={hint} className="welcome-hint" onClick={handleNewChat}>
                  <MessageOutlined style={{ fontSize: 13 }} />
                  {hint}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Empty state */}
        {currentSessionId && messages.length === 0 && !isLoading && (
          <div className="welcome-container">
            <div className="welcome-icon" style={{ width: 64, height: 64, fontSize: 26 }}>
              <MessageOutlined />
            </div>
            <Text className="welcome-title" style={{ fontSize: 20 }}>
              开始和助手对话吧
            </Text>
            <Text className="welcome-subtitle">
              输入你的问题，按 Enter 发送
            </Text>
          </div>
        )}

        {/* Messages */}
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

        {/* Streaming content — only for normal send when no assistant message is displayed yet */}
        {isLoading && streamingContent && !regeneratingMessageId && (() => {
          // Check if there's already an assistant message with this content being rendered
          const lastMsg = displayMessages[displayMessages.length - 1];
          if (lastMsg?.role === "assistant") return null;
          return (
            <div className="streaming-container">
              <div className="message-avatar message-avatar-assistant">
                <RobotOutlined />
              </div>
              <div className="streaming-bubble">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {streamingContent}
                </ReactMarkdown>
                <span className="streaming-cursor" />
              </div>
            </div>
          );
        })()}

        {/* Loading — no separate indicator; thinking shows inside the assistant bubble via MessageBubble */}

        <div ref={bottomRef} />
      </Content>

      {/* Input */}
      {currentSessionId && <InputBar onSend={send} loading={isLoading} />}
    </Layout>
  );
};
