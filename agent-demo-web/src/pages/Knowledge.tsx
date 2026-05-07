import React, { useState, useEffect, useRef } from "react";
import { Layout, Typography, Upload, Button, Input, List, Card, message, Space, Tag } from "antd";
import { UploadOutlined, LinkOutlined, DeleteOutlined } from "@ant-design/icons";
import { uploadFile, ingestUrl, listDocuments } from "@/api/knowledge";
import type { KnowledgeDocument } from "@/types";

const { Content } = Layout;
const { Title, Text } = Typography;

export const Knowledge: React.FC = () => {
  const [docs, setDocs] = useState<KnowledgeDocument[]>([]);
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const mountedRef = useRef(true);

  const loadDocs = async () => {
    try {
      const data = await listDocuments();
      if (mountedRef.current) setDocs(data);
    } catch {}
  };

  useEffect(() => {
    mountedRef.current = true;
    loadDocs();
    return () => { mountedRef.current = false; };
  }, []);

  const handleUpload = async (file: File) => {
    setLoading(true);
    try {
      const result = await uploadFile(file);
      message.success(result.message);
      loadDocs();
    } catch (e) {
      message.error("上传失败");
    } finally {
      setLoading(false);
    }
  };

  const handleIngestUrl = async () => {
    if (!url.trim()) return;
    setLoading(true);
    try {
      const result = await ingestUrl(url);
      message.success((result as any).message);
      setUrl("");
      loadDocs();
    } catch (e) {
      message.error("URL 入库失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Content style={{ padding: 24, maxWidth: 800, margin: "0 auto" }}>
      <Title level={2}>知识库管理</Title>
      <Card title="添加知识" style={{ marginBottom: 24 }}>
        <Space direction="vertical" style={{ width: "100%" }}>
          <Upload beforeUpload={(file) => { handleUpload(file); return false; }} showUploadList={false}>
            <Button icon={<UploadOutlined />} loading={loading}>
              上传文件 (PDF/Word/MD/TXT)
            </Button>
          </Upload>
          <Space.Compact style={{ width: "100%" }}>
            <Input
              prefix={<LinkOutlined />}
              placeholder="输入网址，抓取内容入库"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
            <Button type="primary" onClick={handleIngestUrl} loading={loading}>
              入库
            </Button>
          </Space.Compact>
        </Space>
      </Card>
      <Card title={`已入库文档 (${docs.length})`}>
        <List
          dataSource={docs}
          renderItem={(doc) => (
            <List.Item actions={[<Button type="text" danger icon={<DeleteOutlined />} size="small" />]}>
              <List.Item.Meta
                title={doc.source}
                description={<Tag>{doc.type}</Tag>}
              />
            </List.Item>
          )}
          locale={{ emptyText: "暂无文档" }}
        />
      </Card>
    </Content>
  );
};
