import React from "react";
import { Alert, Image, Progress, Spin, Tag } from "antd";
import { FileImageOutlined } from "@ant-design/icons";
import type { MediaTask } from "@/types";
import { statusColor, statusText } from "./status";
import styles from "./MediaBlock.module.css";

export const ImageGenerationBlock: React.FC<{ task: MediaTask }> = ({ task }) => {
  const running = task.status === "pending" || task.status === "running";
  const failed = task.status === "failed";

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <div className={styles.title}>
          <FileImageOutlined />
          <span>图片生成</span>
        </div>
        <Tag color={statusColor(task.status)}>{statusText(task.status)}</Tag>
      </div>

      {running && (
        <div className={styles.placeholder}>
          <Spin />
          <div className={styles.loadingText}>
            <span>{task.prompt || "正在生成图片"}</span>
            <Progress percent={Math.max(1, task.progress || 1)} size="small" showInfo={false} />
          </div>
        </div>
      )}

      {failed && (
        <Alert
          type="error"
          showIcon
          message="生成失败"
          description={task.error || "图片服务返回异常，请检查模型、额度或 API Key。"}
          className={styles.alert}
        />
      )}

      {task.status === "succeeded" && (
        <div className={styles.imageGrid}>
          {(task.result_urls || []).map((url) => (
            <Image key={url} src={url} className={styles.image} preview={{ src: url }} />
          ))}
        </div>
      )}
    </div>
  );
};
