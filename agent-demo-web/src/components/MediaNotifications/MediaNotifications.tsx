import React from "react";
import { CheckCircleFilled, CloseOutlined, WarningFilled } from "@ant-design/icons";
import { useAppStore } from "@/stores/appStore";
import { jumpToMediaTask } from "@/utils/MediaTaskPoller";
import type { MediaTask } from "@/types";
import styles from "./MediaNotifications.module.css";

export const MediaNotifications: React.FC = () => {
  const notices = useAppStore((s) => s.mediaNotifications);
  const remove = useAppStore((s) => s.removeMediaNotification);

  if (!notices.length) return null;

  return (
    <div className={styles.stack} aria-live="polite">
      {notices.map((notice) => (
        <button
          key={notice.id}
          className={`${styles.notice} ${notice.status === "success" ? styles.success : styles.error}`}
          onClick={() => {
            remove(notice.id);
            void jumpToMediaTask({
              id: notice.id,
              thread_id: notice.sessionId,
              conversation_id: notice.conversationId,
            } as MediaTask);
          }}
          type="button"
        >
          <span className={styles.icon}>
            {notice.status === "success" ? <CheckCircleFilled /> : <WarningFilled />}
          </span>
          <span className={styles.body}>
            <span className={styles.title}>{notice.title}</span>
            <span className={styles.description}>{notice.description}</span>
          </span>
          <span
            className={styles.close}
            onClick={(event) => {
              event.stopPropagation();
              remove(notice.id);
            }}
          >
            <CloseOutlined />
          </span>
        </button>
      ))}
    </div>
  );
};
