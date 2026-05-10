import React from "react";
import { Typography, Collapse } from "antd";
import { ToolOutlined } from "@ant-design/icons";
import type { ToolCall } from "@/types";

const { Text } = Typography;

export const ToolCallCard: React.FC<{ toolCalls: ToolCall[] }> = ({ toolCalls }) => {
  if (!toolCalls?.length) return null;
  return (
    <div className="tool-call-container">
      <Collapse
        size="small"
        className="tool-call-collapse"
        items={toolCalls.map((tc, i) => ({
          key: i,
          label: (
            <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <ToolOutlined style={{ color: "#6366f1", fontSize: 13 }} />
              <span>{tc.name}</span>
            </span>
          ),
          children: (
            <>
              <Text type="secondary" style={{ fontSize: 12 }}>输入:</Text>
              <pre style={{ fontSize: 12, margin: "4px 0 10px" }}>{tc.input}</pre>
              {tc.output && (
                <>
                  <Text type="secondary" style={{ fontSize: 12 }}>输出:</Text>
                  <pre style={{ fontSize: 12, margin: "4px 0 0" }}>{tc.output}</pre>
                </>
              )}
            </>
          ),
        }))}
      />
    </div>
  );
};
