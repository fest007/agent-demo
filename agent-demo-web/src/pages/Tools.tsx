import React, { useState, useEffect, useRef } from "react";
import { Typography, Card, List, Switch, Tag, message, Space, Input } from "antd";
import { ToolOutlined, SearchOutlined } from "@ant-design/icons";
import { listTools, toggleTool } from "@/api/tools";

const { Text } = Typography;

const toolNameMap: Record<string, string> = {
  web_search: "网络搜索",
  wikipedia_query: "维基百科",
  web_scraper: "网页抓取",
  calculator: "计算器",
  get_datetime: "日期时间",
  read_file: "读取文件",
  write_file: "写入文件",
  list_files: "列出目录",
  run_shell: "Shell 命令",
  python_repl: "Python 执行",
  json_parse: "JSON 解析",
  csv_query: "CSV 查询",
  http_request: "HTTP 请求",
  url_to_knowledge: "URL 入库",
};

interface ToolEntry {
  name: string;
  enabled: boolean;
}

const Tools: React.FC = () => {
  const [tools, setTools] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const mountedRef = useRef(true);

  const loadTools = async () => {
    try {
      const data = await listTools();
      if (mountedRef.current) setTools(data);
    } catch {}
  };

  useEffect(() => {
    mountedRef.current = true;
    loadTools();
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const handleToggle = async (name: string, enable: boolean) => {
    setLoading(true);
    try {
      await toggleTool(name, enable);
      setTools((prev) => ({ ...prev, [name]: enable }));
      message.success(`${toolNameMap[name] || name} 已${enable ? "启用" : "禁用"}`);
    } catch {
      message.error("操作失败");
    } finally {
      setLoading(false);
    }
  };

  const toolEntries: ToolEntry[] = Object.entries(tools)
    .map(([name, enabled]) => ({ name, enabled }))
    .filter(
      (t) =>
        !search ||
        t.name.includes(search.toLowerCase()) ||
        (toolNameMap[t.name] || "").includes(search)
    );

  return (
    <div className="page-container">
      <div className="page-content">
        <div
          className="page-header"
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
          }}
        >
          <div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 14,
                marginBottom: 6,
              }}
            >
              <div
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: 12,
                  background: "linear-gradient(135deg, #6366f1, #a78bfa)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "white",
                  fontSize: 18,
                  boxShadow:
                    "0 0 0 1px rgba(99,102,241,0.15), 0 4px 12px rgba(99,102,241,0.12)",
                }}
              >
                <ToolOutlined />
              </div>
              <span className="page-title" style={{ marginBottom: 0 }}>
                工具管理
              </span>
            </div>
            <p className="page-description">启用或禁用助手可用的工具</p>
          </div>
          <Input
            prefix={<SearchOutlined style={{ color: "#9ca0ab" }} />}
            placeholder="搜索工具..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ width: 240, borderRadius: 12 }}
            allowClear
          />
        </div>

        <Card
          style={{
            borderRadius: 16,
            border: "1px solid rgba(0,0,0,0.05)",
          }}
        >
          <List
            dataSource={toolEntries}
            renderItem={(item: ToolEntry) => (
              <List.Item
                actions={[
                  <Switch
                    key="switch"
                    checked={item.enabled}
                    onChange={(checked) => handleToggle(item.name, checked)}
                    loading={loading}
                  />,
                ]}
              >
                <List.Item.Meta
                  avatar={
                    <div
                      style={{
                        width: 42,
                        height: 42,
                        borderRadius: 12,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        background: item.enabled ? "#eef2ff" : "#f3f4f6",
                        transition:
                          "background 200ms cubic-bezier(0.16, 1, 0.3, 1)",
                      }}
                    >
                      <ToolOutlined
                        style={{
                          fontSize: 18,
                          color: item.enabled ? "#6366f1" : "#9ca0ab",
                          transition:
                            "color 200ms cubic-bezier(0.16, 1, 0.3, 1)",
                        }}
                      />
                    </div>
                  }
                  title={
                    <Space>
                      <Text strong style={{ fontSize: 14, letterSpacing: "-0.01em" }}>
                        {toolNameMap[item.name] || item.name}
                      </Text>
                      <Text
                        type="secondary"
                        style={{
                          fontSize: 12,
                          fontFamily: "'JetBrains Mono', monospace",
                        }}
                      >
                        {item.name}
                      </Text>
                    </Space>
                  }
                />
              </List.Item>
            )}
            locale={{ emptyText: "暂无工具" }}
          />
        </Card>
      </div>
    </div>
  );
};

export { Tools };
