"""
数据库连接模块

使用 SQLAlchemy 2.0 异步引擎 + aiosqlite 驱动。
SQLAlchemy 是 Python 最流行的 ORM 框架。

架构：
- Base: 所有 ORM 模型的基类
- engine: 数据库引擎（管理连接池）
- async_session: 异步会话工厂（创建数据库会话）
- init_db(): 初始化数据库（建表）
- get_session(): 依赖注入用的会话生成器
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    ORM 模型基类

    所有数据库模型（如 Conversation, KnowledgeDoc）都继承这个类。
    SQLAlchemy 会自动扫描继承自 Base 的所有模型来创建表。
    """
    pass


# 全局变量，由 init_db() 初始化
engine = None      # 数据库引擎
async_session = None  # 会话工厂


async def init_db():
    """
    初始化数据库

    在应用启动时调用：
    1. 创建异步数据库引擎
    2. 创建会话工厂
    3. 自动创建所有表（如果不存在）
    """
    global engine, async_session
    from server.config import get_settings
    settings = get_settings()

    # 创建异步引擎
    # echo=False: 不打印 SQL 语句（生产环境）
    engine = create_async_engine(settings.database_url, echo=False)

    # 创建会话工厂
    # expire_on_commit=False: 提交后不过期对象（避免惰性加载问题）
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # 自动建表
    async with engine.begin() as conn:
        from server.db.models import Base as ModelBase
        # run_sync: 在异步连接上执行同步操作
        # create_all: 创建所有继承自 Base 的表
        await conn.run_sync(ModelBase.metadata.create_all)


async def get_session() -> AsyncSession:
    """
    获取数据库会话（依赖注入用）

    使用 async with 管理会话生命周期：
    - 进入 with 时创建会话
    - 退出 with 时自动关闭会话

    Yields:
        AsyncSession 实例
    """
    async with async_session() as session:
        yield session
