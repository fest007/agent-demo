import React from "react";
import { Menu, Layout, Button, Typography } from "antd";
import {
  MessageOutlined,
  BookOutlined,
  ToolOutlined,
  ThunderboltOutlined,
  SettingOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from "@ant-design/icons";
import { useAppStore } from "@/stores/appStore";
import { SessionList } from "./SessionList";

const { Sider } = Layout;
const { Title } = Typography;

export const Sidebar: React.FC = () => {
  const { sidebarCollapsed, toggleSidebar, currentPage, setCurrentPage } = useAppStore();

  const items = [
    { key: "chat", icon: <MessageOutlined />, label: "对话" },
    { key: "knowledge", icon: <BookOutlined />, label: "知识库" },
    { key: "tools", icon: <ToolOutlined />, label: "工具" },
    { key: "skills", icon: <ThunderboltOutlined />, label: "技能" },
    { key: "settings", icon: <SettingOutlined />, label: "设置" },
  ];

  return (
    <Sider
      collapsible
      collapsed={sidebarCollapsed}
      onCollapse={toggleSidebar}
      trigger={null}
      style={{
        background: "#fff",
        borderRight: "1px solid #f0f0f0",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div style={{ padding: "16px", textAlign: "center" }}>
        <Title level={4} style={{ margin: 0, fontSize: sidebarCollapsed ? 16 : 20 }}>
          {sidebarCollapsed ? "AI" : "智能 Agent"}
        </Title>
      </div>
      <Menu
        mode="inline"
        selectedKeys={[currentPage]}
        items={items}
        onClick={({ key }) => setCurrentPage(key)}
      />
      {/* 对话页面显示会话列表 */}
      {!sidebarCollapsed && currentPage === "chat" && (
        <div style={{ flex: 1, overflow: "hidden" }}>
          <SessionList />
        </div>
      )}
      <div style={{ textAlign: "center", padding: "8px 0" }}>
        <Button
          type="text"
          icon={sidebarCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          onClick={toggleSidebar}
        />
      </div>
    </Sider>
  );
};
