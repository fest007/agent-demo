import React, { useEffect, useState } from "react";
import { Button, List, Popconfirm, Checkbox } from "antd";
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
import { formatTime } from "@/utils/formatTime";

export const SessionList: React.FC = () => {
  const { sessions, currentSessionId } = useSessionStore();
  const chatStore = useChatStore();
  const [batchMode, setBatchMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

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
    <div className="session-list-container">
      <div className="session-list-header">
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={handleNewChat}
          className="session-new-btn"
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
          className="session-batch-btn"
        >
          {batchMode ? "取消" : "批量"}
        </Button>
      </div>

      {batchMode && selectedIds.size > 0 && (
        <div style={{ padding: "0 14px 8px" }}>
          <Popconfirm
            title={`确定删除选中的 ${selectedIds.size} 个对话？`}
            onConfirm={handleBatchDelete}
          >
            <Button type="primary" danger icon={<DeleteOutlined />} block size="small">
              删除选中 ({selectedIds.size})
            </Button>
          </Popconfirm>
        </div>
      )}

      <div className="session-list-scroll">
        <List
          dataSource={sessions}
          renderItem={(session, index) => {
            const isActive = currentSessionId === session.sessionId && !batchMode;
            return (
              <div
                className={`session-item ${isActive ? "session-item-active" : ""}`}
                onClick={() =>
                  batchMode
                    ? toggleSelect(session.sessionId)
                    : handleSwitchSession(session.sessionId)
                }
                style={{
                  display: "flex",
                  alignItems: "center",
                  animationDelay: `${index * 0.03}s`,
                }}
              >
                {batchMode ? (
                  <Checkbox
                    checked={selectedIds.has(session.sessionId)}
                    onClick={(e) => e.stopPropagation()}
                    onChange={() => toggleSelect(session.sessionId)}
                    style={{ marginRight: 10 }}
                  />
                ) : (
                  <MessageOutlined
                    style={{
                      color: isActive ? "#6366f1" : "#9ca0ab",
                      fontSize: 14,
                      marginRight: 12,
                      flexShrink: 0,
                      transition: "color 200ms cubic-bezier(0.16, 1, 0.3, 1)",
                    }}
                  />
                )}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div
                    className="session-item-title"
                    style={{
                      fontWeight: isActive ? 600 : 500,
                      color: isActive ? "#6366f1" : undefined,
                    }}
                  >
                    {session.name}
                  </div>
                  <div className="session-item-time">
                    {formatTime(session.updatedAt)}
                  </div>
                </div>
                {!batchMode && (
                  <Popconfirm
                    title="确定删除此对话？"
                    onConfirm={(e) => {
                      e?.stopPropagation();
                      handleDeleteSession(session.sessionId);
                    }}
                    onCancel={(e) => e?.stopPropagation()}
                  >
                    <DeleteOutlined
                      className="session-delete-btn"
                      onClick={(e) => e.stopPropagation()}
                    />
                  </Popconfirm>
                )}
              </div>
            );
          }}
          locale={{ emptyText: "暂无对话" }}
          size="small"
        />
      </div>
    </div>
  );
};
