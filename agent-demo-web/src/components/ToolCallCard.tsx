import React from "react";
import { Card, Typography, Collapse } from "antd";
import { ToolOutlined } from "@ant-design/icons";
import type { ToolCall } from "@/types";

const { Text } = Typography;

export const ToolCallCard: React.FC<{ toolCalls: ToolCall[] }> = ({ toolCalls }) => {
  if (!toolCalls?.length) return null;
  return (
    <Collapse
      size="small"
      items={toolCalls.map((tc, i) => ({
        key: i,
        label: (
          <span>
            <ToolOutlined /> {tc.name}
          </span>
        ),
        children: (
          <>
            <Text type="secondary">输入:</Text>
            <pre style={{ fontSize: 12, margin: "4px 0" }}>{tc.input}</pre>
            {tc.output && (
              <>
                <Text type="secondary">输出:</Text>
                <pre style={{ fontSize: 12, margin: "4px 0" }}>{tc.output}</pre>
              </>
            )}
          </>
        ),
      }))}
      style={{ marginTop: 8 }}
    />
  );
};
