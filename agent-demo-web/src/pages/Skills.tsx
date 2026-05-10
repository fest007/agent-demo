import React, { useState, useEffect, useRef } from "react";
import {
  Typography,
  Card,
  List,
  Tag,
  Button,
  Input,
  message,
  Space,
  Modal,
} from "antd";
import {
  ThunderboltOutlined,
  PlusOutlined,
  ArrowLeftOutlined,
  EditOutlined,
  SaveOutlined,
} from "@ant-design/icons";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  listSkills,
  getSkillDetail,
  updateSkill,
  generateSkill,
} from "@/api/skills";
import type { SkillInfo } from "@/types";

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

const Skills: React.FC = () => {
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [genModalOpen, setGenModalOpen] = useState(false);
  const [genDesc, setGenDesc] = useState("");
  const [selectedSkill, setSelectedSkill] = useState<SkillInfo | null>(null);
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState("");
  const mountedRef = useRef(true);

  const loadSkills = async () => {
    try {
      const data = await listSkills();
      if (mountedRef.current) setSkills(data);
    } catch {}
  };

  useEffect(() => {
    mountedRef.current = true;
    loadSkills();
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const handleGenerate = async () => {
    if (!genDesc.trim()) return;
    setLoading(true);
    try {
      const result = await generateSkill(genDesc);
      if ((result as any).status === "success") {
        message.success(`技能 "${(result as any).name}" 生成成功`);
        setGenModalOpen(false);
        setGenDesc("");
        loadSkills();
      } else {
        message.error((result as any).message);
      }
    } catch {
      message.error("生成失败");
    } finally {
      setLoading(false);
    }
  };

  const handleSelectSkill = async (name: string) => {
    setLoading(true);
    try {
      const detail = await getSkillDetail(name);
      if (mountedRef.current) {
        setSelectedSkill(detail);
        setEditContent(detail.content);
        setEditing(false);
      }
    } catch {
      message.error("获取技能详情失败");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!selectedSkill) return;
    setLoading(true);
    try {
      await updateSkill(selectedSkill.name, { content: editContent });
      message.success("保存成功");
      setSelectedSkill({ ...selectedSkill, content: editContent });
      setEditing(false);
      loadSkills();
    } catch {
      message.error("保存失败");
    } finally {
      setLoading(false);
    }
  };

  const cardStyle = {
    borderRadius: 16,
    border: "1px solid rgba(0,0,0,0.05)",
    transition: "all 200ms cubic-bezier(0.16, 1, 0.3, 1)",
  };

  // Detail view
  if (selectedSkill) {
    return (
      <div className="page-container">
        <div className="page-content">
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 14,
              marginBottom: 28,
            }}
          >
            <Button
              icon={<ArrowLeftOutlined />}
              onClick={() => setSelectedSkill(null)}
              style={{ borderRadius: 10 }}
            >
              返回列表
            </Button>
            <span className="page-title" style={{ marginBottom: 0 }}>
              {selectedSkill.name}
            </span>
            {selectedSkill.is_builtin ? (
              <Tag color="blue">内置</Tag>
            ) : (
              <Tag color="green">自定义</Tag>
            )}
          </div>

          <Card
            style={cardStyle}
            title={
              <span style={{ fontWeight: 600, letterSpacing: "-0.02em" }}>
                技能规范
              </span>
            }
            extra={
              editing ? (
                <Space>
                  <Button onClick={() => setEditing(false)}>取消</Button>
                  <Button
                    type="primary"
                    icon={<SaveOutlined />}
                    onClick={handleSave}
                    loading={loading}
                  >
                    保存
                  </Button>
                </Space>
              ) : (
                <Button
                  icon={<EditOutlined />}
                  onClick={() => setEditing(true)}
                  style={{ borderRadius: 10 }}
                >
                  编辑
                </Button>
              )
            }
          >
            {editing ? (
              <TextArea
                rows={20}
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 13,
                  borderRadius: 12,
                }}
              />
            ) : (
              <div style={{ lineHeight: 1.8 }}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {selectedSkill.content}
                </ReactMarkdown>
              </div>
            )}
          </Card>
        </div>
      </div>
    );
  }

  // List view
  return (
    <div className="page-container">
      <div className="page-content">
        <div
          className="page-header"
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
          }}
        >
          <div>
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
                <ThunderboltOutlined />
              </div>
              <span className="page-title" style={{ marginBottom: 0 }}>
                技能管理
              </span>
            </div>
            <p className="page-description">管理和生成助手的技能规范</p>
          </div>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setGenModalOpen(true)}
            style={{ borderRadius: 10 }}
          >
            AI 生成技能
          </Button>
        </div>

        <List
          grid={{ gutter: 16, column: 2 }}
          dataSource={skills}
          renderItem={(skill) => (
            <List.Item>
              <Card
                hoverable
                onClick={() => handleSelectSkill(skill.name)}
                style={cardStyle}
                styles={{
                  body: { padding: "20px 24px" },
                }}
                title={
                  <Space>
                    <ThunderboltOutlined style={{ color: "#6366f1" }} />
                    <span style={{ fontWeight: 600, letterSpacing: "-0.01em" }}>
                      {skill.name}
                    </span>
                    {skill.is_builtin ? (
                      <Tag color="blue">内置</Tag>
                    ) : (
                      <Tag color="green">自定义</Tag>
                    )}
                  </Space>
                }
              >
                <Paragraph
                  ellipsis={{ rows: 2 }}
                  style={{ margin: 0, color: "#5c5f6e", lineHeight: 1.7 }}
                >
                  {skill.description}
                </Paragraph>
              </Card>
            </List.Item>
          )}
          locale={{ emptyText: "暂无技能" }}
        />

        <Modal
          title={
            <span style={{ fontWeight: 600, letterSpacing: "-0.02em" }}>
              AI 生成技能
            </span>
          }
          open={genModalOpen}
          onOk={handleGenerate}
          onCancel={() => setGenModalOpen(false)}
          confirmLoading={loading}
          okText="生成"
        >
          <Paragraph style={{ color: "#5c5f6e" }}>
            描述你需要的技能，AI 将自动生成 Markdown 规范文档
          </Paragraph>
          <TextArea
            rows={4}
            value={genDesc}
            onChange={(e) => setGenDesc(e.target.value)}
            placeholder="例如：帮我做一个汇率转换技能，输入金额和货币类型，自动查询汇率并转换"
            style={{ borderRadius: 12 }}
          />
        </Modal>
      </div>
    </div>
  );
};

export { Skills };
