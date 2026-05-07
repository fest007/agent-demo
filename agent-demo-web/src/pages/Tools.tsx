import React, { useState, useEffect, useRef } from "react";
import { Layout, Typography, Card, List, Switch, Tag, message, Space, Input } from "antd";
import { ToolOutlined, SearchOutlined } from "@ant-design/icons";
import { listTools, toggleTool } from "@/api/tools";

const { Content } = Layout;
const { Title, Text } = Typography;

/** 工具中文名称映射 */
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

export const Tools: React.FC = () => {
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
    return () => { mountedRef.current = false; };
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
    .filter((t) => !search || t.name.includes(search.toLowerCase()) || (toolNameMap[t.name] || "").includes(search));

  return (
    <Content style={{ padding: 24, maxWidth: 800, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0 }}>工具管理</Title>
        <Input
          prefix={<SearchOutlined />}
          placeholder="搜索工具..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ width: 220 }}
          allowClear
        />
      </div>
      <Card>
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
                avatar={<ToolOutlined style={{ fontSize: 20, color: item.enabled ? "#1677ff" : "#d9d9d9" }} />}
                title={
                  <Space>
                    <Text strong>{toolNameMap[item.name] || item.name}</Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>{item.name}</Text>
                    {item.enabled ? <Tag color="green">启用</Tag> : <Tag color="default">禁用</Tag>}
                  </Space>
                }
              />
            </List.Item>
          )}
          locale={{ emptyText: "暂无工具" }}
        />
      </Card>
    </Content>
  );
};
