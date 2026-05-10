import React, { useState } from "react";
import { Tooltip } from "antd";
import { CopyOutlined, EditOutlined, CheckOutlined } from "@ant-design/icons";
import type { Message } from "@/types";

interface Props {
  message: Message;
  onEdit: () => void;
}

export const UserActions: React.FC<Props> = ({ message, onEdit }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="user-actions">
      <Tooltip title="复制" placement="bottom">
        <button className="action-btn" onClick={handleCopy}>
          {copied ? (
            <CheckOutlined style={{ color: "#10b981" }} />
          ) : (
            <CopyOutlined />
          )}
        </button>
      </Tooltip>
      <Tooltip title="编辑并重新发送" placement="bottom">
        <button className="action-btn" onClick={onEdit}>
          <EditOutlined />
        </button>
      </Tooltip>
    </div>
  );
};
