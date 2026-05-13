import React, { useState, useRef, useEffect } from "react";
import { Input, Button, Image, Modal } from "antd";
import {
  SendOutlined,
  PictureOutlined,
  CloseCircleFilled,
  StopOutlined,
} from "@ant-design/icons";
import { useChatStore } from "@/stores/chatStore";
import type { RcFile } from "antd/es/upload";
import styles from "./InputBar.module.css";

const { TextArea } = Input;

interface Props {
  onSend: (message: string, images?: string[]) => void;
  loading: boolean;
}

function fileToBase64(file: RcFile): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

export const InputBar: React.FC<Props> = ({ onSend, loading }) => {
  const [text, setText] = useState("");
  const [images, setImages] = useState<string[]>([]);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pendingText, setPendingText] = useState<string | null>(null);
  const textareaRef = useRef<any>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pendingEdit = useChatStore((s) => s.pendingEdit);
  const setPendingEdit = useChatStore((s) => s.setPendingEdit);
  const abortStream = useChatStore((s) => s.abortStream);

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  useEffect(() => {
    if (pendingEdit === null) return;

    if (text.trim()) {
      setPendingText(pendingEdit);
      setConfirmOpen(true);
      setPendingEdit(null);
    } else {
      setText(pendingEdit);
      setPendingEdit(null);
      setTimeout(() => textareaRef.current?.focus(), 50);
    }
  }, [pendingEdit]);

  const handleConfirmOverwrite = () => {
    if (pendingText !== null) {
      setText(pendingText);
    }
    setConfirmOpen(false);
    setPendingText(null);
    setTimeout(() => textareaRef.current?.focus(), 50);
  };

  const handleCancelOverwrite = () => {
    setConfirmOpen(false);
    setPendingText(null);
  };

  const handleSend = () => {
    const trimmed = text.trim();
    if ((!trimmed && images.length === 0) || loading) return;
    onSend(trimmed, images.length > 0 ? images : undefined);
    setText("");
    setImages([]);
  };

  const handleStop = () => {
    abortStream();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      if (loading) {
        handleStop();
      } else {
        handleSend();
      }
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    for (const file of Array.from(files)) {
      const base64 = await fileToBase64(file as RcFile);
      setImages((prev) => [...prev, base64]);
    }
    e.target.value = "";
  };

  const removeImage = (index: number) => {
    setImages((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <div className={styles.container}>
      <div className={styles.wrapper}>
        {images.length > 0 && (
          <div className={styles.images}>
            {images.map((src, i) => (
              <div key={i} className={styles.imageItem}>
                <Image
                  src={src}
                  width={64}
                  height={64}
                  className={styles.image}
                  preview={{ src }}
                />
                <CloseCircleFilled
                  className={styles.imageRemove}
                  onClick={() => removeImage(i)}
                />
              </div>
            ))}
          </div>
        )}

        <div className={styles.main}>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept="image/*"
            multiple
            hidden
          />
          <TextArea
            ref={textareaRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入消息... (Enter 发送, Shift+Enter 换行)"
            autoSize={{ minRows: 1, maxRows: 5 }}
            className={styles.textarea}
            bordered={false}
          />
          <div className={styles.actions}>
            <Button
              type="text"
              icon={<PictureOutlined />}
              onClick={() => fileInputRef.current?.click()}
              className={styles.actionButton}
              disabled={loading}
            />
            {loading ? (
              <Button
                type="primary"
                icon={<StopOutlined />}
                onClick={handleStop}
                className={`${styles.sendButton} ${styles.stopButton}`}
              />
            ) : (
              <Button
                type="primary"
                icon={<SendOutlined />}
                onClick={handleSend}
                disabled={!text.trim() && images.length === 0}
                className={styles.sendButton}
              />
            )}
          </div>
        </div>
      </div>

      <Modal
        title="覆盖当前输入？"
        open={confirmOpen}
        onOk={handleConfirmOverwrite}
        onCancel={handleCancelOverwrite}
        okText="覆盖"
        cancelText="取消"
        destroyOnClose
      >
        <p>输入框中已有内容，编辑会将其覆盖。</p>
      </Modal>
    </div>
  );
};
