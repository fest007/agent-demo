/**
 * App 根组件
 *
 * 应用的顶层组件，负责：
 * 1. 配置 Ant Design 中文语言包
 * 2. 渲染侧边栏 + 当前页面
 * 3. 根据 currentPage 状态切换页面
 *
 * 页面路由（简单实现，未使用 react-router）：
 * - chat: 对话主页
 * - knowledge: 知识库管理
 * - skills: 技能管理
 * - settings: 设置页面
 */
import React from "react";
import { Layout, ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import { Sidebar } from "@/components/Sidebar";
import { Home } from "@/pages/Home";
import { Knowledge } from "@/pages/Knowledge";
import { Tools } from "@/pages/Tools";
import { Skills } from "@/pages/Skills";
import { Settings } from "@/pages/Settings";
import { useAppStore } from "@/stores/appStore";

// 页面映射表：key → 组件
const pages: Record<string, React.FC> = {
  chat: Home,
  knowledge: Knowledge,
  tools: Tools,
  skills: Skills,
  settings: Settings,
};

const App: React.FC = () => {
  // 从全局状态获取当前页面
  const currentPage = useAppStore((s) => s.currentPage);
  // 根据 currentPage 选择要渲染的页面组件
  const Page = pages[currentPage] || Home;

  return (
    // ConfigProvider: Ant Design 全局配置（语言、主题等）
    <ConfigProvider locale={zhCN}>
      {/* Layout: Ant Design 布局组件 */}
      <Layout style={{ minHeight: "100vh" }}>
        {/* 侧边栏 */}
        <Sidebar />
        {/* 主内容区：根据 currentPage 动态渲染 */}
        <Layout>
          <Page />
        </Layout>
      </Layout>
    </ConfigProvider>
  );
};

export default App;
