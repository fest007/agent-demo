"""
数据库 ORM 模型定义

使用 SQLAlchemy 的声明式模型定义数据库表结构。
每个类对应一张数据库表，类属性对应表的列。

模型说明：
- Conversation: 对话记录表（存储每条消息）
- KnowledgeDoc: 知识库文档表（存储文档元信息）
- SkillRecord: 技能记录表（存储技能元信息）
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from server.db.database import Base


class Conversation(Base):
    """
    对话记录表

    存储每一轮对话的用户消息和 Agent 回复。
    按 thread_id 组织会话，按 user_id 隔离用户。
    """
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)  # 自增主键
    thread_id = Column(String(100), nullable=False, index=True)  # 会话线程 ID（索引）
    user_id = Column(String(100), default="default", index=True)  # 用户 ID（索引）
    role = Column(String(20), nullable=False)  # 角色："user" 或 "assistant"
    content = Column(Text, nullable=False)  # 消息内容
    emotion = Column(String(20))  # 情绪标签（仅 Agent 回复有）
    message_metadata = Column(Text)  # 结构化展示元数据（思考态、工具调用、引用等 JSON）
    created_at = Column(DateTime, server_default=func.now())  # 创建时间（数据库自动生成）


class MediaTask(Base):
    """
    媒体生成任务表

    图片/视频生成通常是异步任务。任务状态单独落库，消息历史只保存可展示摘要，
    刷新页面后前端可以继续轮询尚未完成的任务。
    """
    __tablename__ = "media_tasks"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(100), default="default", index=True)
    thread_id = Column(String(100), nullable=False, index=True)
    conversation_id = Column(Integer, index=True)
    provider = Column(String(80), nullable=False)
    model = Column(String(200), nullable=False)
    task_type = Column(String(20), nullable=False)  # image / video
    mode = Column(String(40), nullable=False)
    prompt = Column(Text, nullable=False)
    status = Column(String(20), default="pending", index=True)
    progress = Column(Integer, default=0)
    external_task_id = Column(String(200))
    input_images = Column(Text)
    result_urls = Column(Text)
    error = Column(Text)
    request_payload = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime)


class KnowledgeDoc(Base):
    """
    知识库文档表

    存储知识库文档的元信息（来源、类型等）。
    实际的文档内容存储在 ChromaDB 向量数据库中。
    """
    __tablename__ = "knowledge_docs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(500), nullable=False, unique=True)  # 文档来源（文件路径或 URL）
    doc_type = Column(String(50), nullable=False)  # 文档类型（file/url/text）
    filename = Column(String(200))  # 文件名（仅文件上传时有）
    user_id = Column(String(100), default="default")  # 上传用户
    created_at = Column(DateTime, server_default=func.now())


class SkillRecord(Base):
    """
    技能记录表

    存储技能的元信息。
    实际的技能代码存储在 skills/store/ 目录中。
    """
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)  # 技能名称（唯一）
    description = Column(Text)  # 技能描述
    is_builtin = Column(Boolean, default=False)  # 是否内置
    created_at = Column(DateTime, server_default=func.now())


class Session(Base):
    """
    对话会话表

    每个 Session 代表一个独立的对话，有自己的 thread_id（UUID）。
    用户可以创建多个 Session，在它们之间切换。
    """
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), nullable=False, unique=True, index=True)  # UUID
    user_id = Column(String(100), default="default", index=True)
    name = Column(String(100), default="新对话")  # 会话名称（LLM 总结，≤8字）
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
