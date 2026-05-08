"""
SQLAdmin 管理面板视图

SQLAdmin 是 FastAPI 的数据库管理面板，类似 Django Admin。
提供可视化的数据库 CRUD 界面，适合开发调试和数据管理。

访问地址：http://localhost:8000/admin
"""
from sqladmin import Admin, ModelView
from server.db.models import Conversation, KnowledgeDoc, SkillRecord


class ConversationAdmin(ModelView, model=Conversation):
    """对话记录管理视图"""
    name = "对话记录"
    name_plural = "对话记录"
    column_list = [
        Conversation.id,
        Conversation.thread_id,
        Conversation.role,
        Conversation.emotion,
        Conversation.created_at,
    ]
    column_labels = {
        "id": "ID",
        "thread_id": "会话线程",
        "role": "角色",
        "emotion": "情绪",
        "content": "内容",
        "created_at": "创建时间",
    }
    column_searchable_list = [Conversation.thread_id, Conversation.content]
    column_sortable_list = [Conversation.created_at]
    page_size = 50


class KnowledgeDocAdmin(ModelView, model=KnowledgeDoc):
    """知识库文档管理视图"""
    name = "知识文档"
    name_plural = "知识文档"
    column_list = [
        KnowledgeDoc.id,
        KnowledgeDoc.source,
        KnowledgeDoc.doc_type,
        KnowledgeDoc.created_at,
    ]
    column_labels = {
        "id": "ID",
        "source": "来源",
        "doc_type": "文档类型",
        "content": "内容",
        "created_at": "创建时间",
    }
    column_searchable_list = [KnowledgeDoc.source]


class SkillRecordAdmin(ModelView, model=SkillRecord):
    """技能记录管理视图"""
    name = "技能记录"
    name_plural = "技能记录"
    column_list = [
        SkillRecord.id,
        SkillRecord.name,
        SkillRecord.is_builtin,
        SkillRecord.created_at,
    ]
    column_labels = {
        "id": "ID",
        "name": "技能名称",
        "is_builtin": "内置技能",
        "description": "描述",
        "created_at": "创建时间",
    }
    column_searchable_list = [SkillRecord.name]


def setup_admin(app, database_url: str):
    """
    初始化 SQLAdmin 管理面板

    SQLAdmin 需要同步引擎，因此这里单独创建一个 sync engine。
    异步引擎（aiosqlite）仅用于业务 API，管理面板用同步引擎即可。

    Args:
        app: FastAPI 应用实例
        database_url: 数据库 URL（同步格式，如 sqlite:///./data/server.db）
    """
    from sqlalchemy import create_engine

    # 将 aiosqlite URL 转为普通 sqlite URL
    sync_url = database_url.replace("+aiosqlite", "")
    sync_engine = create_engine(sync_url)

    admin = Admin(app, sync_engine, title="智能 Agent 管理面板")
    admin.add_view(ConversationAdmin)
    admin.add_view(KnowledgeDocAdmin)
    admin.add_view(SkillRecordAdmin)
    return admin
