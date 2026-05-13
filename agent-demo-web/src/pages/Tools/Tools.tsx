import React, { useState, useEffect, useRef } from "react";
import { Typography, Card, List, Switch, message, Space, Input } from "antd";
import { ToolOutlined, SearchOutlined } from "@ant-design/icons";
import { listTools, toggleTool } from "@/api/tools";
import styles from "./Tools.module.css";

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
    <div className={styles.page}>
      <div className={styles.content}>
        <div className={styles.header}>
          <div>
            <div className={styles.titleRow}>
              <div className={styles.titleIcon}>
                <ToolOutlined />
              </div>
              <span className={styles.title}>工具管理</span>
            </div>
            <p className={styles.description}>启用或禁用助手可用的工具</p>
          </div>
          <Input
            prefix={<SearchOutlined className={styles.searchIcon} />}
            placeholder="搜索工具..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className={styles.search}
            allowClear
          />
        </div>

        <Card className={styles.card}>
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
                    <div className={`${styles.toolAvatar} ${item.enabled ? styles.toolAvatarEnabled : ""}`}>
                      <ToolOutlined className={`${styles.toolIcon} ${item.enabled ? styles.toolIconEnabled : ""}`} />
                    </div>
                  }
                  title={
                    <Space>
                      <Text strong className={styles.toolTitle}>
                        {toolNameMap[item.name] || item.name}
                      </Text>
                      <Text type="secondary" className={styles.toolName}>
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
