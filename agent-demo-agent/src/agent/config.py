"""
全局配置模块

使用 pydantic-settings 管理配置，支持从 .env 文件和环境变量读取。
所有配置项都有默认值，只需在 .env 中覆盖需要修改的项。
"""
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

# 项目根目录（agent-demo-agent/）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """
    应用配置类

    pydantic-settings 会自动从环境变量和 .env 文件中读取配置。
    字段名自动转小写并与环境变量匹配，例如 mimo_api_key 对应环境变量 MIMO_API_KEY。
    """

    # ===== MiMo API 配置 =====
    # 小米 MiMo 大模型的 API Key，从 https://api.xiaomimimo.com 获取
    mimo_api_key: str = ""
    # MiMo API 的基础地址，兼容 OpenAI 格式
    mimo_base_url: str = "https://api.xiaomimimo.com/v1"
    # 主力模型，用于复杂推理、对话等场景
    mimo_model: str = "mimo-v2.5-pro"
    # 轻量快速模型，用于简单任务（如情绪分析、技能生成）
    mimo_model_fast: str = "mimo-v2-flash"
    # 多模态模型，支持图片输入
    mimo_model_omni: str = "mimo-v2-omni"

    # ===== TTS 语音合成配置 =====
    # 默认 TTS 引擎：mimo-tts（MiMo 自带 TTS）或 edge-tts（微软免费 TTS）
    tts_engine: str = "mimo-tts"
    # MiMo TTS 的模型名称
    tts_mimo_model: str = "mimo-v2.5-tts"
    # 备选 TTS 引擎，当主引擎不可用时自动降级
    tts_fallback_engine: str = "edge-tts"
    # TTS 语音角色，XiaoxiaoNeural 是微软的中文女声，音质很好
    tts_voice: str = "zh-CN-XiaoxiaoNeural"

    # ===== 向量数据库配置 =====
    # ChromaDB 的持久化目录，存储知识库的向量数据
    chroma_persist_dir: str = str(_PROJECT_ROOT / "data" / "chroma")

    # ===== 嵌入模型配置 =====
    # BAAI/bge-base-zh-v1.5 是中文效果最好的轻量嵌入模型之一
    # 768 维向量，约 400MB，CPU 可运行，首次使用自动从 HuggingFace 下载
    embedding_model: str = "BAAI/bge-base-zh-v1.5"

    # ===== 记忆系统配置 =====
    # 短期记忆数据库（SQLite），存储当前会话的对话历史
    short_term_db: str = str(_PROJECT_ROOT / "data" / "memory.db")
    # 长期记忆数据库（SQLite），存储跨会话的用户偏好和事实
    long_term_db: str = str(_PROJECT_ROOT / "data" / "long_term.db")

    # ===== MCP 协议配置 =====
    # MCP 服务器配置文件路径，定义要连接的外部 MCP 工具服务器
    mcp_config_path: str = str(_PROJECT_ROOT / "mcp_servers" / "config.json")

    # pydantic-settings 的模型配置
    model_config = {
        "env_file": str(_PROJECT_ROOT / ".env"),  # 从项目根目录的 .env 文件读取
        "env_file_encoding": "utf-8",
    }


# 使用 lru_cache 缓存配置实例，全局只创建一次
# 避免每次调用都重新读取 .env 文件
@lru_cache
def get_settings() -> Settings:
    return Settings()
