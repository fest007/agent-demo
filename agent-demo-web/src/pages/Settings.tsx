import React from "react";
import { Typography, Card, Form, Select, Switch, Button, Divider } from "antd";
import { SettingOutlined } from "@ant-design/icons";

const Settings: React.FC = () => {
  return (
    <div className="page-container">
      <div className="page-content" style={{ maxWidth: 620 }}>
        <div className="page-header">
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
              <SettingOutlined />
            </div>
            <span className="page-title" style={{ marginBottom: 0 }}>
              设置
            </span>
          </div>
          <p className="page-description">配置模型、语音和界面选项</p>
        </div>

        <Card
          style={{
            borderRadius: 16,
            border: "1px solid rgba(0,0,0,0.05)",
          }}
        >
          <Form layout="vertical">
            <Form.Item label="模型">
              <Select
                defaultValue="mimo-v2.5-pro"
                options={[
                  { value: "mimo-v2.5-pro", label: "MiMo v2.5 Pro" },
                  { value: "mimo-v2-flash", label: "MiMo v2 Flash" },
                ]}
              />
            </Form.Item>
            <Form.Item label="TTS 引擎">
              <Select
                defaultValue="edge-tts"
                options={[
                  { value: "mimo-tts", label: "MiMo TTS" },
                  { value: "edge-tts", label: "Edge TTS" },
                ]}
              />
            </Form.Item>
            <Form.Item label="语音">
              <Select
                defaultValue="zh-CN-XiaoxiaoNeural"
                options={[
                  { value: "zh-CN-XiaoxiaoNeural", label: "晓晓 (女声)" },
                  { value: "zh-CN-YunxiNeural", label: "云希 (男声)" },
                ]}
              />
            </Form.Item>
            <Divider style={{ margin: "20px 0" }} />
            <Form.Item label="自动语音播放" style={{ marginBottom: 18 }}>
              <Switch />
            </Form.Item>
            <Form.Item label="显示情绪标识" style={{ marginBottom: 18 }}>
              <Switch defaultChecked />
            </Form.Item>
            <Form.Item label="显示工具调用" style={{ marginBottom: 28 }}>
              <Switch defaultChecked />
            </Form.Item>
            <Button type="primary" block size="large" style={{ borderRadius: 12 }}>
              保存设置
            </Button>
          </Form>
        </Card>
      </div>
    </div>
  );
};

export { Settings };
