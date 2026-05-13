import React, { useState } from "react";
import { Tooltip } from "antd";
import { CopyOutlined, EditOutlined, CheckOutlined } from "@ant-design/icons";
import type { Message } from "@/types";
import styles from "./UserActions.module.css";

interface Props {
  message: Message;
  onEdit: () => void;
  className?: string;
}

export const UserActions: React.FC<Props> = ({ message, onEdit, className }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className={`${styles.actions} ${className ?? ""}`}>
      <Tooltip title="复制" placement="bottom">
        <button className={styles.button} onClick={handleCopy}>
          {copied ? (
            <CheckOutlined style={{ color: "#10b981" }} />
          ) : (
            <CopyOutlined />
          )}
        </button>
      </Tooltip>
      <Tooltip title="编辑并重新发送" placement="bottom">
        <button className={styles.button} onClick={onEdit}>
          <EditOutlined />
        </button>
      </Tooltip>
    </div>
  );
};
