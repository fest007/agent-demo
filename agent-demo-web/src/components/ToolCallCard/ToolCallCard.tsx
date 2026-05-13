import React from "react";
import { Typography, Collapse } from "antd";
import { ToolOutlined } from "@ant-design/icons";
import type { ToolCall } from "@/types";
import styles from "./ToolCallCard.module.css";

const { Text } = Typography;

export const ToolCallCard: React.FC<{ toolCalls: ToolCall[] }> = ({ toolCalls }) => {
  if (!toolCalls?.length) return null;
  return (
    <div className={styles.container}>
      <Collapse
        size="small"
        className={styles.collapse}
        items={toolCalls.map((tc, i) => ({
          key: i,
          label: (
            <span className={styles.label}>
              <ToolOutlined className={styles.labelIcon} />
              <span>{tc.name}</span>
            </span>
          ),
          children: (
            <>
              <Text type="secondary" className={styles.caption}>输入:</Text>
              <pre className={styles.pre}>{tc.input}</pre>
              {tc.output && (
                <>
                  <Text type="secondary" className={styles.caption}>输出:</Text>
                  <pre className={`${styles.pre} ${styles.preLast}`}>{tc.output}</pre>
                </>
              )}
            </>
          ),
        }))}
      />
    </div>
  );
};
