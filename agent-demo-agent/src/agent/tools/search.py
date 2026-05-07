"""
网络搜索工具

使用 DuckDuckGo 搜索引擎，无需 API Key，免费使用。
适合查找实时信息、新闻、未知知识等。
"""
from langchain_core.tools import tool
from duckduckgo_search import DDGS


@tool  # @tool 装饰器将函数转换为 LangChain 工具，LLM 可以通过 Function Calling 调用
def web_search(query: str, max_results: int = 5) -> str:
    """
    搜索互联网获取信息。当需要查找实时信息、新闻或未知知识时使用。

    Args:
        query: 搜索关键词
        max_results: 最大返回结果数，默认 5

    Returns:
        格式化的搜索结果，包含标题、摘要和链接
    """
    try:
        # DDGS (DuckDuckGo Search) 是一个免费的搜索引擎 API
        results = DDGS().text(query, max_results=max_results)
        if not results:
            return "未找到相关搜索结果"

        # 将搜索结果格式化为易读的文本
        formatted = []
        for i, r in enumerate(results, 1):
            formatted.append(f"{i}. {r['title']}\n   {r['body']}\n   链接: {r['href']}")
        return "\n\n".join(formatted)
    except Exception as e:
        return f"搜索失败: {str(e)}"
