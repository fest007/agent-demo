/**
 * ChatBox 对话主组件
 *
 * 整合了消息列表、流式输出展示、输入栏的完整对话界面。
 * 使用 useChat hook 管理对话逻辑。
 */
import React, { useRef, useEffect } from "react";
import { Layout, Spin, Typography, Button } from "antd";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { PlusOutlined } from "@ant-design/icons";
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
  const { messages, isLoading, streamingContent, currentEmotion, send } = useChat();
  const bottomRef = useRef<HTMLDivElement>(null);
  const { currentSessionId } = useSessionStore();
  const sessions = useSessionStore((s) => s.sessions);
  const currentSession = sessions.find((s) => s.sessionId === currentSessionId);
  const displayName = currentSession?.name || "智能助手";
  const chatStore = useChatStore();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  // 过滤掉正在流式输出中的空 Agent 占位消息（避免显示空气泡）
  const displayMessages = messages.filter((msg) => {
    if (msg.role === "assistant" && msg.content === "" && isLoading && streamingContent) {
      return false; // 流式输出中，跳过空的占位消息
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
    <Layout style={{ height: "100vh", background: "#fff" }}>
      {/* 标题栏 */}
      <div style={{
        padding: "12px 24px",
        borderBottom: "1px solid #f0f0f0",
        display: "flex",
        alignItems: "center",
        gap: 12,
      }}>
        <Text strong style={{ fontSize: 16 }}>{displayName}</Text>
        {currentEmotion && <EmotionBadge emotion={currentEmotion} />}
      </div>

      {/* 消息列表 */}
      <Content style={{ padding: "24px", overflowY: "auto", flex: 1 }}>
        {/* 无会话选中时显示欢迎页 */}
        {!currentSessionId && (
          <div style={{ textAlign: "center", marginTop: "20vh", color: "#999" }}>
            <Text type="secondary" style={{ fontSize: 18, display: "block", marginBottom: 16 }}>
              欢迎使用智能助手
            </Text>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleNewChat} size="large">
              开始新对话
            </Button>
          </div>
        )}

        {/* 有会话但消息为空 */}
        {currentSessionId && messages.length === 0 && (
          <div style={{ textAlign: "center", marginTop: "20vh", color: "#999" }}>
            <Text type="secondary" style={{ fontSize: 18 }}>开始和智能助手对话吧</Text>
          </div>
        )}

        {displayMessages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {/* 流式输出中的临时内容（使用 Markdown 渲染，避免完成后格式跳变） */}
        {isLoading && streamingContent && (
          <div style={{ display: "flex", justifyContent: "flex-start", marginBottom: 16 }}>
            <div style={{ maxWidth: "75%" }}>
              <div style={{ padding: "12px 16px", borderRadius: 12, backgroundColor: "#f5f5f5" }}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{streamingContent}</ReactMarkdown>
                <Spin size="small" style={{ marginLeft: 8 }} />
              </div>
            </div>
          </div>
        )}

        {/* 刚开始加载时的等待提示 */}
        {isLoading && !streamingContent && (
          <div style={{ textAlign: "center", padding: 24 }}>
            <Spin>
              <div style={{ padding: 24 }}>思考中...</div>
            </Spin>
          </div>
        )}

        <div ref={bottomRef} />
      </Content>

      {currentSessionId && <InputBar onSend={send} loading={isLoading} />}
    </Layout>
  );
};
