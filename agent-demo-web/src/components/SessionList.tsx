/**
 * SessionList 会话列表组件
 *
 * 显示在侧边栏中（仅对话页面可见），提供：
 * - 新建对话按钮
 * - 会话列表（点击切换，hover 显示删除）
 * - 当前会话高亮
 */
import React, { useEffect, useState } from "react";
import { Button, List, Popconfirm, Typography, Checkbox } from "antd";
import {
  PlusOutlined,
  DeleteOutlined,
  MessageOutlined,
  CheckSquareOutlined,
} from "@ant-design/icons";
import { useSessionStore } from "@/stores/sessionStore";
import { useChatStore } from "@/stores/chatStore";
import {
  createSession,
  listSessions,
  deleteSession as deleteSessionApi,
} from "@/api/session";
import { getHistory } from "@/api/chat";
import type { Message } from "@/types";

const { Text } = Typography;

export const SessionList: React.FC = () => {
  const { sessions, currentSessionId } = useSessionStore();
  const chatStore = useChatStore();
  const [batchMode, setBatchMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // 加载会话列表
  useEffect(() => {
    listSessions()
      .then((data) => {
        useSessionStore.getState().setSessions(
          data.map((d) => ({
            sessionId: d.session_id,
            name: d.name,
            createdAt: new Date(d.created_at),
            updatedAt: new Date(d.updated_at),
          }))
        );
      })
      .catch(() => {});
  }, []);

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

  const handleSwitchSession = async (sessionId: string) => {
    if (sessionId === currentSessionId) return;
    useSessionStore.getState().setCurrentSessionId(sessionId);
    try {
      const history = (await getHistory(sessionId)) as any[];
      const messages: Message[] = history.map((h: any, i: number) => ({
        id: `hist_${i}_${Date.now()}`,
        role: h.role,
        content: h.content,
        emotion: h.emotion,
        timestamp: new Date(h.timestamp),
      }));
      chatStore.loadSession(sessionId, messages);
    } catch {
      chatStore.loadSession(sessionId, []);
    }
  };

  const handleDeleteSession = async (sessionId: string) => {
    try {
      await deleteSessionApi(sessionId);
      useSessionStore.getState().removeSession(sessionId);
      if (currentSessionId === sessionId) {
        chatStore.clearMessages();
      }
    } catch {}
  };

  const handleBatchDelete = async () => {
    const ids = Array.from(selectedIds);
    for (const id of ids) {
      try {
        await deleteSessionApi(id);
        useSessionStore.getState().removeSession(id);
      } catch {}
    }
    if (selectedIds.has(currentSessionId || "")) {
      chatStore.clearMessages();
    }
    setSelectedIds(new Set());
    setBatchMode(false);
  };

  const toggleSelect = (sessionId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(sessionId)) {
        next.delete(sessionId);
      } else {
        next.add(sessionId);
      }
      return next;
    });
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ margin: "12px 12px 8px", display: "flex", gap: 8 }}>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={handleNewChat}
          style={{ flex: 1 }}
        >
          新对话
        </Button>
        <Button
          icon={<CheckSquareOutlined />}
          onClick={() => {
            setBatchMode(!batchMode);
            setSelectedIds(new Set());
          }}
          danger={batchMode}
        >
          {batchMode ? "取消" : "批量"}
        </Button>
      </div>

      {batchMode && selectedIds.size > 0 && (
        <div style={{ margin: "0 12px 8px" }}>
          <Popconfirm
            title={`确定删除选中的 ${selectedIds.size} 个对话？`}
            onConfirm={handleBatchDelete}
          >
            <Button
              type="primary"
              danger
              icon={<DeleteOutlined />}
              block
            >
              删除选中 ({selectedIds.size})
            </Button>
          </Popconfirm>
        </div>
      )}

      <div style={{ flex: 1, overflowY: "auto", padding: "0 4px" }}>
        <List
          dataSource={sessions}
          renderItem={(session) => (
            <List.Item
              onClick={() =>
                batchMode
                  ? toggleSelect(session.sessionId)
                  : handleSwitchSession(session.sessionId)
              }
              style={{
                padding: "8px 12px",
                cursor: "pointer",
                borderRadius: 8,
                backgroundColor:
                  currentSessionId === session.sessionId && !batchMode
                    ? "#e6f4ff"
                    : "transparent",
                marginBottom: 2,
              }}
              actions={
                batchMode
                  ? [
                      <Checkbox
                        key="check"
                        checked={selectedIds.has(session.sessionId)}
                        onClick={(e) => e.stopPropagation()}
                        onChange={() => toggleSelect(session.sessionId)}
                      />,
                    ]
                  : [
                      <Popconfirm
                        key="delete"
                        title="确定删除此对话？"
                        onConfirm={(e) => {
                          e?.stopPropagation();
                          handleDeleteSession(session.sessionId);
                        }}
                        onCancel={(e) => e?.stopPropagation()}
                      >
                        <DeleteOutlined
                          style={{ color: "#999", fontSize: 14 }}
                          onClick={(e) => e.stopPropagation()}
                        />
                      </Popconfirm>,
                    ]
              }
            >
              <List.Item.Meta
                avatar={
                  batchMode ? (
                    <Checkbox
                      checked={selectedIds.has(session.sessionId)}
                      onClick={(e) => e.stopPropagation()}
                      onChange={() => toggleSelect(session.sessionId)}
                    />
                  ) : (
                    <MessageOutlined
                      style={{ color: "#1677ff", fontSize: 16 }}
                    />
                  )
                }
                title={
                  <Text
                    ellipsis
                    style={{
                      fontSize: 14,
                      fontWeight:
                        currentSessionId === session.sessionId && !batchMode
                          ? 600
                          : 400,
                    }}
                  >
                    {session.name}
                  </Text>
                }
              />
            </List.Item>
          )}
          locale={{ emptyText: "暂无对话" }}
          size="small"
        />
      </div>
    </div>
  );
};
