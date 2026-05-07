"""
文本分割模块

将长文本分割成小块（chunk），以便进行向量化和检索。
使用递归字符分割器，按优先级尝试不同的分隔符。

为什么需要分割：
- 嵌入模型有 token 上限（通常 512 token）
- 小块的语义更集中，检索精度更高
- 但也太小会丢失上下文，需要平衡

参数说明：
- chunk_size=500: 每个块约 500 字符（中文约 250 字）
- chunk_overlap=50: 相邻块重叠 50 字符，避免在分隔处丢失语义
"""
from langchain_text_splitters import RecursiveCharacterTextSplitter


def get_splitter(chunk_size: int = 500, chunk_overlap: int = 50) -> RecursiveCharacterTextSplitter:
    """
    获取文本分割器

    分隔符优先级（从高到低）：
    1. \n\n: 段落分隔（最自然的分割点）
    2. \n: 换行
    3. 。！？: 中文句号
    4. .!?: 英文句号
    5. 空格: 单词边界
    6. "": 字符级（最后的兜底）

    Args:
        chunk_size: 每个块的最大字符数
        chunk_overlap: 相邻块的重叠字符数

    Returns:
        RecursiveCharacterTextSplitter 实例
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        # 中文友好的分隔符列表
        separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""],
    )
