import React, { useState } from "react";
import { Input, Button, Space, Upload } from "antd";
import { SendOutlined, UploadOutlined } from "@ant-design/icons";

const { TextArea } = Input;

interface Props {
  onSend: (message: string) => void;
  loading: boolean;
}

export const InputBar: React.FC<Props> = ({ onSend, loading }) => {
  const [text, setText] = useState("");

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;
    onSend(trimmed);
    setText("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // IME 组合输入（如中文拼音）时，Enter 用于确认选词，不触发发送
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div style={{ padding: "16px", borderTop: "1px solid #f0f0f0", background: "#fff" }}>
      <Space.Compact style={{ width: "100%" }}>
        <TextArea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入消息... (Enter 发送, Shift+Enter 换行)"
          autoSize={{ minRows: 1, maxRows: 4 }}
          style={{ flex: 1 }}
        />
        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={handleSend}
          loading={loading}
          style={{ height: "auto" }}
        >
          发送
        </Button>
      </Space.Compact>
    </div>
  );
};
