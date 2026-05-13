import React, { Suspense, lazy } from "react";
import { Layout, ConfigProvider, theme } from "antd";
import zhCN from "antd/locale/zh_CN";
import { Sidebar } from "@/components/Sidebar/Sidebar";
import { MediaNotifications } from "@/components/MediaNotifications";
import { useAppStore } from "@/stores/appStore";
import { useMediaTaskRecovery } from "@/hooks/useMediaTaskRecovery";
import styles from "./App.module.css";

const Home = lazy(() => import("@/pages/Home").then((module) => ({ default: module.Home })));
const Knowledge = lazy(() => import("@/pages/Knowledge/Knowledge").then((module) => ({ default: module.Knowledge })));
const Tools = lazy(() => import("@/pages/Tools/Tools").then((module) => ({ default: module.Tools })));
const Skills = lazy(() => import("@/pages/Skills/Skills").then((module) => ({ default: module.Skills })));
const Settings = lazy(() => import("@/pages/Settings/Settings").then((module) => ({ default: module.Settings })));

const pages: Record<string, React.FC> = {
  chat: Home,
  knowledge: Knowledge,
  tools: Tools,
  skills: Skills,
  settings: Settings,
};

const App: React.FC = () => {
  const currentPage = useAppStore((s) => s.currentPage);
  const Page = pages[currentPage] || Home;
  useMediaTaskRecovery();

  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          // Brand
          colorPrimary: "#6366f1",
          colorLink: "#6366f1",
          colorLinkHover: "#4338ca",

          // Surface
          colorBgContainer: "#ffffff",
          colorBgLayout: "#fafbfc",
          colorBgElevated: "#ffffff",

          // Border — hairline, not solid gray
          colorBorder: "rgba(0, 0, 0, 0.06)",
          colorBorderSecondary: "rgba(0, 0, 0, 0.04)",

          // Text
          colorText: "#0c0e16",
          colorTextSecondary: "#5c5f6e",
          colorTextTertiary: "#9ca0ab",
          colorTextQuaternary: "#c2c5ce",

          // Radius — Squircle
          borderRadius: 12,
          borderRadiusLG: 16,
          borderRadiusSM: 8,
          borderRadiusXS: 6,

          // Typography — Plus Jakarta Sans
          fontFamily:
            "'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
          fontSize: 14,
          fontSizeHeading1: 28,
          fontSizeHeading2: 22,
          fontSizeHeading3: 18,

          // Sizing
          controlHeight: 40,
          controlHeightLG: 48,
          controlHeightSM: 32,

          // Shadows — Ultra-soft ambient
          boxShadow:
            "0 0 0 1px rgba(0,0,0,0.04), 0 2px 8px rgba(0,0,0,0.04)",
          boxShadowSecondary:
            "0 0 0 1px rgba(0,0,0,0.05), 0 4px 16px rgba(0,0,0,0.05)",

          // Motion
          motionDurationFast: "0.2s",
          motionDurationMid: "0.35s",
          motionDurationSlow: "0.5s",
          motionEaseInOut: "cubic-bezier(0.32, 0.72, 0, 1)",
          motionEaseOut: "cubic-bezier(0.16, 1, 0.3, 1)",
        },
        algorithm: theme.defaultAlgorithm,
      }}
    >
      <Layout className={styles.layout}>
        <Sidebar />
        <MediaNotifications />
        <Layout>
          <Suspense fallback={<div className={styles.pageFallback} />}>
            <Page />
          </Suspense>
        </Layout>
      </Layout>
    </ConfigProvider>
  );
};

export default App;
