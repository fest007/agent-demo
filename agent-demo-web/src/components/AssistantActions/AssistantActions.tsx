import React, { useState } from "react";
import { Tooltip } from "antd";
import {
  CopyOutlined,
  FileTextOutlined,
  ReloadOutlined,
  LeftOutlined,
  RightOutlined,
  CheckOutlined,
} from "@ant-design/icons";
import { VoicePlayer } from "../VoicePlayer";
import { useChatStore } from "@/stores/chatStore";
import { stripMarkdown } from "@/utils/stripMarkdown";
import type { Message } from "@/types";
import styles from "./AssistantActions.module.css";

interface Props {
  message: Message;
  onRegenerate: () => void;
  isRegenerating: boolean;
  forceShow?: boolean;
  className?: string;
}

export const AssistantActions: React.FC<Props> = ({
  message,
  onRegenerate,
  isRegenerating,
  forceShow,
  className,
}) => {
  const [copiedText, setCopiedText] = useState(false);
  const [copiedMd, setCopiedMd] = useState(false);
  const switchVersion = useChatStore((s) => s.switchVersion);

  const versions = message.versions || [];
  const currentIndex = message.currentVersionIndex ?? 0;
  const hasVersions = versions.length > 1;

  const handleCopyText = async () => {
    const plain = stripMarkdown(message.content);
    await navigator.clipboard.writeText(plain);
    setCopiedText(true);
    setTimeout(() => setCopiedText(false), 1500);
  };

  const handleCopyMd = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopiedMd(true);
    setTimeout(() => setCopiedMd(false), 1500);
  };

  const buttonClass = styles.button;
  const versionButtonClass = `${styles.button} ${styles.versionButton}`;

  return (
    <div
      className={`${styles.actions} ${className ?? ""} ${forceShow ? styles.forceShow : ""}`}
    >
      <Tooltip title="复制纯文本" placement="bottom">
        <button className={buttonClass} onClick={handleCopyText}>
          {copiedText ? (
            <CheckOutlined style={{ color: "#10b981" }} />
          ) : (
            <CopyOutlined />
          )}
        </button>
      </Tooltip>

      <Tooltip title="复制 Markdown" placement="bottom">
        <button className={buttonClass} onClick={handleCopyMd}>
          {copiedMd ? (
            <CheckOutlined style={{ color: "#10b981" }} />
          ) : (
            <FileTextOutlined />
          )}
        </button>
      </Tooltip>

      <Tooltip title="语音播报" placement="bottom">
        <span>
          <VoicePlayer text={message.content} />
        </span>
      </Tooltip>

      <Tooltip title="重新生成" placement="bottom">
        <button
          className={buttonClass}
          onClick={onRegenerate}
          disabled={isRegenerating}
          style={{ opacity: isRegenerating ? 0.4 : 1 }}
        >
          <ReloadOutlined />
        </button>
      </Tooltip>

      {hasVersions && (
        <div className={styles.versionSwitcher}>
          <Tooltip title="上一个版本" placement="bottom">
            <button
              className={versionButtonClass}
              onClick={() => switchVersion(message.id, currentIndex - 1)}
              disabled={currentIndex === 0}
              style={{ opacity: currentIndex === 0 ? 0.3 : 1 }}
            >
              <LeftOutlined style={{ fontSize: 10 }} />
            </button>
          </Tooltip>
          <span>
            {currentIndex + 1}/{versions.length}
          </span>
          <Tooltip title="下一个版本" placement="bottom">
            <button
              className={versionButtonClass}
              onClick={() => switchVersion(message.id, currentIndex + 1)}
              disabled={currentIndex === versions.length - 1}
              style={{
                opacity: currentIndex === versions.length - 1 ? 0.3 : 1,
              }}
            >
              <RightOutlined style={{ fontSize: 10 }} />
            </button>
          </Tooltip>
        </div>
      )}
    </div>
  );
};
