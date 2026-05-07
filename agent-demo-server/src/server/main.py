"""
FastAPI 后端服务主入口

启动方式：
- python -m server.main
- 或 uvicorn server.main:app --reload

访问地址：
- API 文档：http://localhost:8000/docs（Swagger UI）
- 管理面板：http://localhost:8000/admin
"""
from fastapi import FastAPI
from contextlib import asynccontextmanager
from server.middleware.cors import setup_cors
from server.api import chat, knowledge, skills, memory, tools, tts, health, session
from server.db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    FastAPI 的 lifespan 机制：
    - yield 之前的代码在应用启动时执行（初始化数据库）
    - yield 之后的代码在应用关闭时执行（清理资源）
    """
    await init_db()  # 启动时初始化数据库（建表）
    yield


# 创建 FastAPI 应用实例
app = FastAPI(
    title="智能 Agent API",
    description="基于 LangGraph 的智能代理系统后端服务",
    version="0.1.0",
    lifespan=lifespan,
)

# 配置 CORS 中间件（允许前端跨域访问）
setup_cors(app)

# 注册所有 API 路由
app.include_router(chat.router)        # 对话 API
app.include_router(knowledge.router)   # 知识库管理 API
app.include_router(skills.router)      # 技能管理 API
app.include_router(memory.router)      # 记忆查询 API
app.include_router(tools.router)       # 工具管理 API
app.include_router(tts.router)         # TTS 语音合成 API
app.include_router(health.router)      # 健康检查 API
app.include_router(session.router)    # 会话管理 API


@app.get("/")
async def root():
    """根路由，返回 API 基本信息"""
    return {"message": "智能 Agent API", "docs": "/docs"}


def run():
    """
    启动服务

    使用 uvicorn 运行 FastAPI 应用。
    reload=True 表示代码修改后自动重启（开发模式）。
    """
    import uvicorn
    from server.config import get_settings
    settings = get_settings()
    uvicorn.run("server.main:app", host=settings.server_host, port=settings.server_port, reload=True)


if __name__ == "__main__":
    run()
