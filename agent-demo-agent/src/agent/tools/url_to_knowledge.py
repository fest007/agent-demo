"""
URL 知识库入库工具

将网页内容抓取后存入 RAG 知识库（ChromaDB）。
这是 web_scraper + RAG ingest 的组合工具。

使用场景：用户说"把这个网址的内容加到知识库"
"""
from langchain_core.tools import tool


@tool
def url_to_knowledge(url: str) -> str:
    """
    抓取 URL 内容并存入知识库。

    工作流程：
    1. 使用 web_scraper 抓取网页正文
    2. 调用 ingest_text 将正文存入 ChromaDB 向量数据库
    3. 后续对话中，knowledge_search 工具可以检索到这些内容

    Args:
        url: 要入库的网页 URL

    Returns:
        入库结果信息
    """
    # 延迟导入，避免循环依赖
    from agent.tools.web_scraper import web_scraper

    try:
        # 第一步：抓取网页内容
        content = web_scraper.invoke({"url": url})

        # 如果抓取失败，直接返回错误
        if "失败" in content or "为空" in content:
            return content

        # 第二步：将内容存入知识库
        from agent.rag.ingest import ingest_text
        result = ingest_text(content, metadata={"source": url, "type": "url"})
        return f"已将网页内容存入知识库: {result}"
    except Exception as e:
        return f"URL 入库失败: {str(e)}"
