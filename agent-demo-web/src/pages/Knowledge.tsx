import React, { useState, useEffect, useRef } from "react";
import { Typography, Upload, Button, Input, List, Card, message, Space, Tag } from "antd";
import { UploadOutlined, LinkOutlined, DeleteOutlined, BookOutlined } from "@ant-design/icons";
import { uploadFile, ingestUrl, listDocuments, deleteDocument } from "@/api/knowledge";
import type { KnowledgeDocument } from "@/types";

const Knowledge: React.FC = () => {
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
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const handleUpload = async (file: File) => {
    setLoading(true);
    try {
      const result = await uploadFile(file);
      message.success(result.message);
      loadDocs();
    } catch {
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
    } catch {
      message.error("URL 入库失败");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (source: string) => {
    setLoading(true);
    try {
      const result = await deleteDocument(source);
      message.success((result as any).message);
      loadDocs();
    } catch {
      message.error("删除失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-container">
      <div className="page-content">
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
              <BookOutlined />
            </div>
            <span className="page-title" style={{ marginBottom: 0 }}>
              知识库管理
            </span>
          </div>
          <p className="page-description">
            上传文档或添加网址，让助手拥有专属知识
          </p>
        </div>

        <Card
          style={{
            marginBottom: 24,
            borderRadius: 16,
            border: "1px solid rgba(0,0,0,0.05)",
          }}
        >
          <div
            style={{
              fontSize: 15,
              fontWeight: 600,
              marginBottom: 20,
              letterSpacing: "-0.02em",
            }}
          >
            添加知识
          </div>
          <Space direction="vertical" style={{ width: "100%" }} size="middle">
            <Upload
              beforeUpload={(file) => {
                handleUpload(file);
                return false;
              }}
              showUploadList={false}
            >
              <Button
                icon={<UploadOutlined />}
                loading={loading}
                size="large"
                style={{ borderRadius: 12 }}
              >
                上传文件 (PDF / Word / MD / TXT)
              </Button>
            </Upload>
            <Space.Compact style={{ width: "100%" }}>
              <Input
                prefix={<LinkOutlined style={{ color: "#9ca0ab" }} />}
                placeholder="输入网址，抓取内容入库"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                size="large"
                style={{ borderRadius: "12px 0 0 12px" }}
              />
              <Button
                type="primary"
                onClick={handleIngestUrl}
                loading={loading}
                size="large"
                style={{ borderRadius: "0 12px 12px 0" }}
              >
                入库
              </Button>
            </Space.Compact>
          </Space>
        </Card>

        <Card
          style={{
            borderRadius: 16,
            border: "1px solid rgba(0,0,0,0.05)",
          }}
        >
          <div
            style={{
              fontSize: 15,
              fontWeight: 600,
              marginBottom: 16,
              letterSpacing: "-0.02em",
            }}
          >
            已入库文档 ({docs.length})
          </div>
          <List
            dataSource={docs}
            renderItem={(doc) => (
              <List.Item
                actions={[
                  <Button
                    type="text"
                    danger
                    icon={<DeleteOutlined />}
                    size="small"
                    loading={loading}
                    onClick={() => handleDelete(doc.source)}
                    style={{ borderRadius: 8 }}
                  />,
                ]}
              >
                <List.Item.Meta
                  title={
                    <span style={{ fontSize: 14, fontWeight: 500 }}>
                      {doc.source}
                    </span>
                  }
                  description={<Tag color="blue">{doc.type}</Tag>}
                />
              </List.Item>
            )}
            locale={{ emptyText: "暂无文档，上传文件或添加网址开始" }}
          />
        </Card>
      </div>
    </div>
  );
};

export { Knowledge };
