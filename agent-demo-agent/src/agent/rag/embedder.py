"""
嵌入模型封装模块

使用 BAAI/bge-base-zh-v1.5 作为嵌入模型。
这个模型是中文 MTEB 排行榜表现最好的轻量模型之一：
- 768 维向量
- 约 400MB
- CPU 可运行
- 首次使用自动从 HuggingFace 下载

使用双重检查锁（Double-Checked Locking）确保线程安全的单例初始化。
"""
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from agent.config import get_settings
import threading

# 全局单例，缓存嵌入模型实例
_model = None
# 线程锁，防止多线程同时初始化模型
_lock = threading.Lock()


def get_embedder() -> HuggingFaceBgeEmbeddings:
    """
    获取嵌入模型单例

    使用双重检查锁模式（Double-Checked Locking）：
    1. 第一次检查：如果已初始化，直接返回（无锁，高性能）
    2. 加锁
    3. 第二次检查：防止其他线程在等待锁期间已经初始化
    4. 初始化模型

    Returns:
        HuggingFaceBgeEmbeddings 实例
    """
    global _model
    if _model is None:  # 第一次检查（无锁）
        with _lock:  # 加锁
            if _model is None:  # 第二次检查（有锁）
                settings = get_settings()
                _model = HuggingFaceBgeEmbeddings(
                    model_name=settings.embedding_model,  # "BAAI/bge-base-zh-v1.5"
                    model_kwargs={"device": "cpu"},  # 使用 CPU 推理（无需 GPU）
                    encode_kwargs={"normalize_embeddings": True},  # 归一化向量，用于余弦相似度
                )
    return _model
