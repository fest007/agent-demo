"""
网页抓取工具

使用 httpx 发送 HTTP 请求，BeautifulSoup 解析 HTML，提取网页正文。
自动去除 script/style/nav/footer 等非内容标签。
"""
from langchain_core.tools import tool
import httpx
from bs4 import BeautifulSoup
from agent.tools.url_security import validate_public_http_url


@tool
def web_scraper(url: str) -> str:
    """
    抓取指定 URL 的网页内容，提取正文文本。

    工作流程：
    1. 使用 httpx 发送 GET 请求（模拟浏览器 User-Agent）
    2. BeautifulSoup 解析 HTML
    3. 移除 script/style/nav/footer 等非内容元素
    4. 提取纯文本并截断到 8000 字符

    Args:
        url: 要抓取的网页 URL

    Returns:
        网页正文文本（最多 8000 字符）
    """
    try:
        safe_url = validate_public_http_url(url)
        # 模拟浏览器 User-Agent，避免被网站拒绝
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        # follow_redirects=True 自动跟随 301/302 重定向
        resp = httpx.get(safe_url, headers=headers, follow_redirects=True, timeout=15)
        validate_public_http_url(str(resp.url))
        resp.raise_for_status()  # 如果状态码不是 2xx，抛出异常

        # 解析 HTML
        soup = BeautifulSoup(resp.text, "html.parser")

        # 移除非内容标签，只保留正文
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()  # 从 DOM 树中移除

        # 提取纯文本，用换行符分隔
        text = soup.get_text(separator="\n", strip=True)

        # 截断过长内容，避免占用过多 token
        if len(text) > 8000:
            text = text[:8000] + "\n...(内容已截断)"

        return text if text else "网页内容为空"
    except Exception as e:
        return f"网页抓取失败: {str(e)}"
