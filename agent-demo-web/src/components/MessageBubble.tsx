/**
 * MessageBubble 消息气泡组件
 *
 * 渲染单条消息，支持：
 * - 用户消息：右对齐，蓝色背景
 * - Agent 消息：左对齐，灰色背景，Markdown 渲染
 * - 情绪标识（仅 Agent 消息）
 * - 工具调用展示（仅 Agent 消息）
 *
 * 布局：
 *   用户消息：                    Agent 消息：
 *   ┌──────────┐ 🟢              🔵 ┌──────────┐
 *   │ 消息内容  │                  │ [情绪标签] │
 *   └──────────┘                  │ 消息内容   │
 *                                  │ [工具调用] │
 *                                  └──────────┘
 */
import React from "react";
import { Avatar, Space } from "antd";
import { UserOutlined, RobotOutlined } from "@ant-design/icons";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { EmotionBadge } from "./EmotionBadge";
import { ToolCallCard } from "./ToolCallCard";
import { VoicePlayer } from "./VoicePlayer";
import { formatTime } from "@/utils/formatTime";
import type { Message } from "@/types";

export const MessageBubble: React.FC<{ message: Message }> = ({ message }) => {
  const isUser = message.role === "user";

  return (
    <div style={{
      display: "flex",
      justifyContent: isUser ? "flex-end" : "flex-start",  // 用户消息右对齐，Agent 消息左对齐
      marginBottom: 16,
    }}>
      {/* Agent 头像（左侧） */}
      {!isUser && (
        <Avatar icon={<RobotOutlined />} style={{ backgroundColor: "#1677ff", marginRight: 8 }} />
      )}

      {/* 消息内容区 */}
      <div style={{ maxWidth: "75%" }}>
        {/* 情绪标识（仅 Agent 消息显示） */}
        {!isUser && message.emotion && (
          <div style={{ marginBottom: 4 }}>
            <EmotionBadge emotion={message.emotion} />
          </div>
        )}

        {/* 消息气泡 */}
        <div style={{
          padding: "12px 16px",
          borderRadius: 12,
          backgroundColor: isUser ? "#1677ff" : "#f5f5f5",  // 用户蓝色，Agent 灰色
          color: isUser ? "#fff" : "#333",
        }}>
          {isUser ? (
            // 用户消息：纯文本
            message.content
          ) : (
            // Agent 消息：Markdown 渲染
            // remarkGfm 支持 GitHub 风格的 Markdown（表格、任务列表等）
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
          )}
        </div>

        {/* 时间戳 */}
        <div style={{
          fontSize: 12,
          color: "#999",
          marginTop: 4,
          textAlign: isUser ? "right" : "left",
        }}>
          {formatTime(message.timestamp)}
        </div>

        {/* 工具调用展示（仅 Agent 消息） */}
        {!isUser && message.toolCalls && <ToolCallCard toolCalls={message.toolCalls} />}

        {/* 语音播放按钮（仅 Agent 消息） */}
        {!isUser && message.content && (
          <div style={{ marginTop: 4 }}>
            <VoicePlayer text={message.content} />
          </div>
        )}
      </div>

      {/* 用户头像（右侧） */}
      {isUser && (
        <Avatar icon={<UserOutlined />} style={{ backgroundColor: "#87d068", marginLeft: 8 }} />
      )}
    </div>
  );
};
