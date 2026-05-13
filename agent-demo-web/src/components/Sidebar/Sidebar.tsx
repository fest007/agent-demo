import React from "react";
import { Menu, Layout, Button } from "antd";
import {
  MessageOutlined,
  BookOutlined,
  ToolOutlined,
  ThunderboltOutlined,
  SettingOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  RobotOutlined,
} from "@ant-design/icons";
import { useAppStore } from "@/stores/appStore";
import { SessionList } from "../SessionList/SessionList";
import styles from "./Sidebar.module.css";

const { Sider } = Layout;

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
      width={280}
      collapsedWidth={72}
      className={styles.sidebar}
    >
      <div className={styles.header}>
        <div className={styles.logo}>
          <RobotOutlined />
        </div>
        {!sidebarCollapsed && (
          <span className={styles.title}>智能 Agent</span>
        )}
      </div>

      <Menu
        mode="inline"
        selectedKeys={[currentPage]}
        items={items}
        onClick={({ key }) => setCurrentPage(key)}
        className={styles.menu}
      />

      {!sidebarCollapsed && currentPage === "chat" && (
        <div className={styles.sessionWrap}>
          <SessionList />
        </div>
      )}

      <Button
        type="text"
        icon={sidebarCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
        onClick={toggleSidebar}
        className={styles.collapseButton}
      />
    </Sider>
  );
};
