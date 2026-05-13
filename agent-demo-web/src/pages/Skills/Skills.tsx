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
import styles from "./Skills.module.css";

const { Paragraph } = Typography;
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

  if (selectedSkill) {
    return (
      <div className={styles.page}>
        <div className={styles.content}>
          <div className={styles.detailHeader}>
            <Button
              icon={<ArrowLeftOutlined />}
              onClick={() => setSelectedSkill(null)}
              className={styles.button}
            >
              返回列表
            </Button>
            <span className={styles.title}>{selectedSkill.name}</span>
            {selectedSkill.is_builtin ? (
              <Tag color="blue">内置</Tag>
            ) : (
              <Tag color="green">自定义</Tag>
            )}
          </div>

          <Card
            className={styles.card}
            title={<span className={styles.cardTitle}>技能规范</span>}
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
                  className={styles.button}
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
                className={styles.editor}
              />
            ) : (
              <div className={styles.markdown}>
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

  return (
    <div className={styles.page}>
      <div className={styles.content}>
        <div className={styles.header}>
          <div>
            <div className={styles.titleRow}>
              <div className={styles.titleIcon}>
                <ThunderboltOutlined />
              </div>
              <span className={styles.title}>技能管理</span>
            </div>
            <p className={styles.description}>管理和生成助手的技能规范</p>
          </div>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setGenModalOpen(true)}
            className={styles.button}
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
                className={styles.card}
                classNames={{ body: styles.cardBody }}
                title={
                  <Space>
                    <ThunderboltOutlined className={styles.skillIcon} />
                    <span className={styles.skillName}>{skill.name}</span>
                    {skill.is_builtin ? (
                      <Tag color="blue">内置</Tag>
                    ) : (
                      <Tag color="green">自定义</Tag>
                    )}
                  </Space>
                }
              >
                <Paragraph ellipsis={{ rows: 2 }} className={styles.skillDesc}>
                  {skill.description}
                </Paragraph>
              </Card>
            </List.Item>
          )}
          locale={{ emptyText: "暂无技能" }}
        />

        <Modal
          title={<span className={styles.modalTitle}>AI 生成技能</span>}
          open={genModalOpen}
          onOk={handleGenerate}
          onCancel={() => setGenModalOpen(false)}
          confirmLoading={loading}
          okText="生成"
        >
          <Paragraph className={styles.modalDesc}>
            描述你需要的技能，AI 将自动生成 Markdown 规范文档
          </Paragraph>
          <TextArea
            rows={4}
            value={genDesc}
            onChange={(e) => setGenDesc(e.target.value)}
            placeholder="例如：帮我做一个汇率转换技能，输入金额和货币类型，自动查询汇率并转换"
            className={styles.modalInput}
          />
        </Modal>
      </div>
    </div>
  );
};

export { Skills };
