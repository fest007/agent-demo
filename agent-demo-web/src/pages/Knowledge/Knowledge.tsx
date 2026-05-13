import React, { useState, useEffect, useRef } from "react";
import { Upload, Button, Input, List, Card, message, Space, Tag, Progress, Collapse, Skeleton } from "antd";
import { UploadOutlined, LinkOutlined, DeleteOutlined, BookOutlined, EyeOutlined } from "@ant-design/icons";
import { uploadFile, ingestUrl, listDocuments, deleteDocument, previewDocument } from "@/api/knowledge";
import { useAppStore } from "@/stores/appStore";
import type { KnowledgeChunk, KnowledgeDocument } from "@/types";
import styles from "./Knowledge.module.css";

const Knowledge: React.FC = () => {
  const [docs, setDocs] = useState<KnowledgeDocument[]>([]);
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [docsLoading, setDocsLoading] = useState(true);
  const [previewLoading, setPreviewLoading] = useState<string | null>(null);
  const [activeSources, setActiveSources] = useState<string[]>([]);
  const [chunksBySource, setChunksBySource] = useState<Record<string, KnowledgeChunk[]>>({});
  const [progress, setProgress] = useState(0);
  const [progressText, setProgressText] = useState("");
  const mountedRef = useRef(true);
  const progressTimerRef = useRef<number | null>(null);
  const chunkRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const knowledgeFocus = useAppStore((s) => s.knowledgeFocus);
  const setKnowledgeFocus = useAppStore((s) => s.setKnowledgeFocus);

  const loadDocs = async () => {
    setDocsLoading(true);
    try {
      const data = await listDocuments();
      if (mountedRef.current) setDocs(data);
    } catch {
      message.error("知识库列表加载失败");
    } finally {
      if (mountedRef.current) setDocsLoading(false);
    }
  };

  const ensurePreview = async (source: string) => {
    if (chunksBySource[source]) return chunksBySource[source];
    setPreviewLoading(source);
    try {
      const chunks = await previewDocument(source);
      if (mountedRef.current) {
        setChunksBySource((prev) => ({ ...prev, [source]: chunks }));
      }
      return chunks;
    } catch {
      message.error("预览加载失败");
      return [];
    } finally {
      if (mountedRef.current) setPreviewLoading(null);
    }
  };

  const openPreview = async (source: string) => {
    setActiveSources((prev) => (prev.includes(source) ? prev : [...prev, source]));
    await ensurePreview(source);
  };

  const togglePreview = async (source: string) => {
    if (activeSources.includes(source)) {
      setActiveSources((prev) => prev.filter((item) => item !== source));
      return;
    }
    await openPreview(source);
  };

  const startProgress = (label: string) => {
    if (progressTimerRef.current) {
      window.clearInterval(progressTimerRef.current);
    }
    setProgress(8);
    setProgressText(label);
    progressTimerRef.current = window.setInterval(() => {
      setProgress((value) => {
        if (value < 38) return value + 7;
        if (value < 68) return value + 4;
        if (value < 88) return value + 2;
        return value;
      });
    }, 420);
  };

  const finishProgress = (label: string) => {
    if (progressTimerRef.current) {
      window.clearInterval(progressTimerRef.current);
      progressTimerRef.current = null;
    }
    setProgress(100);
    setProgressText(label);
    window.setTimeout(() => {
      if (!mountedRef.current) return;
      setProgress(0);
      setProgressText("");
    }, 900);
  };

  const failProgress = (label: string) => {
    if (progressTimerRef.current) {
      window.clearInterval(progressTimerRef.current);
      progressTimerRef.current = null;
    }
    setProgressText(label);
    window.setTimeout(() => {
      if (!mountedRef.current) return;
      setProgress(0);
      setProgressText("");
    }, 1400);
  };

  useEffect(() => {
    mountedRef.current = true;
    loadDocs();
    return () => {
      mountedRef.current = false;
      if (progressTimerRef.current) window.clearInterval(progressTimerRef.current);
    };
  }, []);

  useEffect(() => {
    if (!knowledgeFocus) return;
    openPreview(knowledgeFocus.source).then(() => {
      window.setTimeout(() => {
        const target = knowledgeFocus.chunkId
          ? chunkRefs.current[knowledgeFocus.chunkId]
          : undefined;
        target?.scrollIntoView({ behavior: "smooth", block: "center" });
        if (knowledgeFocus.chunkId) {
          target?.classList.add(styles.chunkFocused);
          window.setTimeout(() => target?.classList.remove(styles.chunkFocused), 1800);
        }
        setKnowledgeFocus(null);
      }, 120);
    });
  }, [knowledgeFocus]);

  const handleUpload = async (file: File) => {
    setLoading(true);
    startProgress("上传文件并解析内容");
    try {
      const result = await uploadFile(file);
      message.success(result.message);
      finishProgress("文件内容已分块并写入知识库");
      loadDocs();
    } catch {
      failProgress("文件入库失败");
      message.error("上传失败");
    } finally {
      setLoading(false);
    }
  };

  const handleIngestUrl = async () => {
    if (!url.trim()) return;
    setLoading(true);
    startProgress("抓取网页并提取正文内容");
    try {
      const result = await ingestUrl(url);
      message.success((result as any).message);
      setUrl("");
      finishProgress("网页正文已分块并写入知识库");
      loadDocs();
    } catch {
      failProgress("URL 入库失败");
      message.error("URL 入库失败");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (source: string) => {
    setLoading(true);
    startProgress("删除知识库文档片段");
    try {
      const result = await deleteDocument(source);
      message.success((result as any).message);
      finishProgress("文档已从知识库移除");
      loadDocs();
    } catch {
      failProgress("删除失败");
      message.error("删除失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.content}>
        <div className={styles.header}>
          <div className={styles.titleRow}>
            <div className={styles.titleIcon}>
              <BookOutlined />
            </div>
            <span className={styles.title}>知识库管理</span>
          </div>
          <p className={styles.description}>上传文档或添加网址，让助手拥有专属知识</p>
        </div>

        <Card className={styles.addCard}>
          <div className={styles.sectionTitle}>添加知识</div>
          <Space direction="vertical" className={styles.fullWidth} size="middle">
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
                className={styles.uploadButton}
              >
                上传文件 (PDF / Word / MD / TXT)
              </Button>
            </Upload>
            <Space.Compact className={styles.fullWidth}>
              <Input
                prefix={<LinkOutlined className={styles.urlIcon} />}
                placeholder="输入网址，抓取内容入库"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                size="large"
                className={styles.urlInput}
              />
              <Button
                type="primary"
                onClick={handleIngestUrl}
                loading={loading}
                size="large"
                className={styles.ingestButton}
              >
                入库
              </Button>
            </Space.Compact>
            {progress > 0 && (
              <div className={styles.progress}>
                <div className={styles.progressLabel}>{progressText}</div>
                <Progress
                  percent={progress}
                  size="small"
                  status={progress >= 100 ? "success" : "active"}
                  showInfo={false}
                />
              </div>
            )}
          </Space>
        </Card>

        <Card className={styles.docCard}>
          <div className={`${styles.sectionTitle} ${styles.docTitle}`}>
            已入库文档 ({docs.length})
          </div>
          <List
            loading={false}
            dataSource={docs}
            renderItem={(doc) => (
              <List.Item
                className={styles.listItem}
                actions={[
                  <Button
                    type="text"
                    icon={<EyeOutlined />}
                    size="small"
                    loading={previewLoading === doc.source}
                    onClick={() => togglePreview(doc.source)}
                    className={styles.actionButton}
                  />,
                  <Button
                    type="text"
                    danger
                    icon={<DeleteOutlined />}
                    size="small"
                    loading={loading}
                    onClick={() => handleDelete(doc.source)}
                    className={styles.actionButton}
                  />,
                ]}
              >
                <List.Item.Meta
                  title={
                    <span className={styles.documentName}>
                      {doc.title || doc.source}
                    </span>
                  }
                  description={
                    <Space size={6} wrap>
                      <Tag color="blue">{doc.type}</Tag>
                      {typeof doc.chunks === "number" && <Tag>{doc.chunks} 片段</Tag>}
                      {typeof doc.content_length === "number" && (
                        <Tag>{doc.content_length} 字符</Tag>
                      )}
                      {doc.extraction_quality === "sparse" && (
                        <Tag color="orange">静态内容较少</Tag>
                      )}
                      <span className={styles.docSource}>{doc.source}</span>
                    </Space>
                  }
                />
                {doc.extraction_note && (
                  <div className={styles.docNote}>{doc.extraction_note}</div>
                )}
                {activeSources.includes(doc.source) && (
                  <div className={styles.preview}>
                    <Collapse
                      size="small"
                      ghost
                      activeKey={["preview"]}
                      onChange={(keys) => {
                        if ((Array.isArray(keys) ? keys : [keys]).length === 0) {
                          setActiveSources((prev) => prev.filter((item) => item !== doc.source));
                        }
                      }}
                      items={[
                        {
                          key: "preview",
                          label: `内容预览 (${chunksBySource[doc.source]?.length || 0} 个片段)`,
                          children: (
                            <div className={styles.chunkList}>
                              {(chunksBySource[doc.source] || []).map((chunk) => (
                                <div
                                  key={chunk.chunk_id}
                                  ref={(node) => {
                                    chunkRefs.current[chunk.chunk_id] = node;
                                  }}
                                  className={styles.chunk}
                                >
                                  <div className={styles.chunkHeader}>
                                    片段 {chunk.chunk_index}
                                  </div>
                                  <div className={styles.chunkContent}>{chunk.content}</div>
                                </div>
                              ))}
                            </div>
                          ),
                        },
                      ]}
                    />
                  </div>
                )}
              </List.Item>
            )}
            locale={{
              emptyText: docsLoading ? (
                <div className={styles.skeleton}>
                  {[0, 1, 2].map((item) => (
                    <Skeleton key={item} active title paragraph={{ rows: 2 }} />
                  ))}
                </div>
              ) : (
                "暂无文档，上传文件或添加网址开始"
              ),
            }}
          />
        </Card>
      </div>
    </div>
  );
};

export { Knowledge };
