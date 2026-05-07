import React from "react";
import { Layout, Typography, Card, Form, Input, Select, Switch, Button, Divider } from "antd";

const { Content } = Layout;
const { Title } = Typography;

export const Settings: React.FC = () => {
  return (
    <Content style={{ padding: 24, maxWidth: 600, margin: "0 auto" }}>
      <Title level={2}>设置</Title>
      <Card>
        <Form layout="vertical">
          <Form.Item label="模型">
            <Select defaultValue="mimo-v2.5-pro" options={[
              { value: "mimo-v2.5-pro", label: "MiMo v2.5 Pro" },
              { value: "mimo-v2-flash", label: "MiMo v2 Flash" },
            ]} />
          </Form.Item>
          <Form.Item label="TTS 引擎">
            <Select defaultValue="edge-tts" options={[
              { value: "mimo-tts", label: "MiMo TTS" },
              { value: "edge-tts", label: "Edge TTS" },
            ]} />
          </Form.Item>
          <Form.Item label="语音">
            <Select defaultValue="zh-CN-XiaoxiaoNeural" options={[
              { value: "zh-CN-XiaoxiaoNeural", label: "晓晓 (女声)" },
              { value: "zh-CN-YunxiNeural", label: "云希 (男声)" },
            ]} />
          </Form.Item>
          <Divider />
          <Form.Item label="自动语音播放">
            <Switch />
          </Form.Item>
          <Form.Item label="显示情绪标识">
            <Switch defaultChecked />
          </Form.Item>
          <Form.Item label="显示工具调用">
            <Switch defaultChecked />
          </Form.Item>
          <Button type="primary" block>保存设置</Button>
        </Form>
      </Card>
    </Content>
  );
};
