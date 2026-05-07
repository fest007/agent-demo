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
    # 显示的列
    column_list = [
        Conversation.id,
        Conversation.thread_id,
        Conversation.role,
        Conversation.emotion,
        Conversation.created_at,
    ]
    # 可搜索的列
    column_searchable_list = [Conversation.thread_id, Conversation.content]
    # 可排序的列
    column_sortable_list = [Conversation.created_at]
    # 每页显示条数
    page_size = 50


class KnowledgeDocAdmin(ModelView, model=KnowledgeDoc):
    """知识库文档管理视图"""
    column_list = [
        KnowledgeDoc.id,
        KnowledgeDoc.source,
        KnowledgeDoc.doc_type,
        KnowledgeDoc.created_at,
    ]
    column_searchable_list = [KnowledgeDoc.source]


class SkillRecordAdmin(ModelView, model=SkillRecord):
    """技能记录管理视图"""
    column_list = [
        SkillRecord.id,
        SkillRecord.name,
        SkillRecord.is_builtin,
        SkillRecord.created_at,
    ]
    column_searchable_list = [SkillRecord.name]


def setup_admin(app, engine):
    """
    初始化 SQLAdmin 管理面板

    Args:
        app: FastAPI 应用实例
        engine: SQLAlchemy 引擎

    Returns:
        Admin 实例
    """
    admin = Admin(app, engine)
    admin.add_view(ConversationAdmin)
    admin.add_view(KnowledgeDocAdmin)
    admin.add_view(SkillRecordAdmin)
    return admin
