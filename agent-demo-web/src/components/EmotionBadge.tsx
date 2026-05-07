import React from "react";
import { Tag } from "antd";
import {
  SmileOutlined,
  FrownOutlined,
  ThunderboltOutlined,
  QuestionCircleOutlined,
  HeartOutlined,
  RocketOutlined,
  MehOutlined,
} from "@ant-design/icons";

const emotionMap: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  happy: { color: "green", icon: <SmileOutlined />, label: "开心" },
  sad: { color: "blue", icon: <FrownOutlined />, label: "难过" },
  angry: { color: "red", icon: <ThunderboltOutlined />, label: "生气" },
  anxious: { color: "orange", icon: <QuestionCircleOutlined />, label: "焦虑" },
  confused: { color: "purple", icon: <QuestionCircleOutlined />, label: "困惑" },
  neutral: { color: "default", icon: <MehOutlined />, label: "平静" },
  excited: { color: "magenta", icon: <RocketOutlined />, label: "兴奋" },
};

export const EmotionBadge: React.FC<{ emotion: string }> = ({ emotion }) => {
  const info = emotionMap[emotion] || emotionMap.neutral;
  return (
    <Tag color={info.color} icon={info.icon}>
      {info.label}
    </Tag>
  );
};
