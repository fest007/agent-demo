import React from "react";
import {
  SmileOutlined,
  FrownOutlined,
  ThunderboltOutlined,
  QuestionCircleOutlined,
  RocketOutlined,
  MehOutlined,
} from "@ant-design/icons";

const emotionMap: Record<
  string,
  { color: string; bg: string; icon: React.ReactNode; label: string }
> = {
  happy:    { color: "#059669", bg: "#ecfdf5", icon: <SmileOutlined />, label: "开心" },
  sad:      { color: "#2563eb", bg: "#eff6ff", icon: <FrownOutlined />, label: "难过" },
  angry:    { color: "#dc2626", bg: "#fef2f2", icon: <ThunderboltOutlined />, label: "生气" },
  anxious:  { color: "#d97706", bg: "#fffbeb", icon: <QuestionCircleOutlined />, label: "焦虑" },
  confused: { color: "#7c3aed", bg: "#f5f3ff", icon: <QuestionCircleOutlined />, label: "困惑" },
  neutral:  { color: "#6b7280", bg: "#f3f4f6", icon: <MehOutlined />, label: "平静" },
  excited:  { color: "#db2777", bg: "#fdf2f8", icon: <RocketOutlined />, label: "兴奋" },
};

export const EmotionBadge: React.FC<{ emotion: string }> = ({ emotion }) => {
  const info = emotionMap[emotion] || emotionMap.neutral;
  return (
    <span className="emotion-badge" style={{ color: info.color, background: info.bg }}>
      {info.icon}
      {info.label}
    </span>
  );
};
