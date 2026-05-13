"""
网络搜索工具

使用多搜索源 fallback，无需 API Key，免费使用。
适合查找实时信息、新闻、未知知识等。
"""
from __future__ import annotations

from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup
from langchain_core.tools import tool
from duckduckgo_search import DDGS

from agent.config import get_settings


_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6",
}


def _clean_text(text: str | None) -> str:
    return " ".join((text or "").split())


def _dedupe_results(results: list[dict], max_results: int) -> list[dict]:
    seen: set[str] = set()
    deduped: list[dict] = []
    for item in results:
        title = _clean_text(item.get("title"))
        href = item.get("href") or ""
        key = href or title
        if not title or key in seen:
            continue
        seen.add(key)
        deduped.append({
            "source": item.get("source", ""),
            "title": title,
            "body": _clean_text(item.get("body")),
            "href": href,
        })
        if len(deduped) >= max_results:
            break
    return deduped


def _fetch_html(url: str, timeout: float) -> BeautifulSoup:
    response = requests.get(url, headers=_HEADERS, timeout=timeout)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def _search_baidu(query: str, max_results: int, timeout: float) -> list[dict]:
    soup = _fetch_html(f"https://www.baidu.com/s?wd={quote_plus(query)}", timeout)
    results: list[dict] = []
    for item in soup.select("div.result, div.c-container"):
        title_node = item.select_one("h3 a")
        if not title_node:
            continue
        title = _clean_text(title_node.get_text(" ", strip=True))
        href = title_node.get("href") or ""
        body = _clean_text(item.get_text(" ", strip=True).replace(title, "", 1))
        results.append({"source": "baidu", "title": title, "body": body, "href": href})
        if len(results) >= max_results:
            break
    return results


def _search_sogou(query: str, max_results: int, timeout: float) -> list[dict]:
    soup = _fetch_html(f"https://www.sogou.com/web?query={quote_plus(query)}", timeout)
    results: list[dict] = []
    for item in soup.select(".results .vrwrap, .results .rb, div.vrwrap"):
        title_node = item.select_one("h3 a, a[target='_blank']")
        if not title_node:
            continue
        title = _clean_text(title_node.get_text(" ", strip=True))
        href = title_node.get("href") or ""
        if href.startswith("/"):
            href = urljoin("https://www.sogou.com", href)
        body = _clean_text(item.get_text(" ", strip=True).replace(title, "", 1))
        results.append({"source": "sogou", "title": title, "body": body, "href": href})
        if len(results) >= max_results:
            break
    return results


def _search_bing(query: str, max_results: int, timeout: float) -> list[dict]:
    soup = _fetch_html(f"https://cn.bing.com/search?q={quote_plus(query)}", timeout)
    results: list[dict] = []
    for item in soup.select("li.b_algo"):
        title_node = item.select_one("h2 a")
        if not title_node:
            continue
        body_node = item.select_one("p")
        results.append({
            "source": "bing",
            "title": title_node.get_text(" ", strip=True),
            "body": body_node.get_text(" ", strip=True) if body_node else "",
            "href": title_node.get("href") or "",
        })
        if len(results) >= max_results:
            break
    return results


def _search_duckduckgo(query: str, max_results: int) -> list[dict]:
    results = DDGS().text(
        query,
        region="cn-zh",
        backend="auto",
        max_results=max_results,
    )
    return [
        {
            "source": "duckduckgo",
            "title": item.get("title", ""),
            "body": item.get("body", ""),
            "href": item.get("href", ""),
        }
        for item in (results or [])
    ]


def _search_with_engine(engine: str, query: str, max_results: int, timeout: float) -> list[dict]:
    if engine == "baidu":
        return _search_baidu(query, max_results, timeout)
    if engine == "sogou":
        return _search_sogou(query, max_results, timeout)
    if engine == "bing":
        return _search_bing(query, max_results, timeout)
    if engine == "duckduckgo":
        return _search_duckduckgo(query, max_results)
    raise ValueError(f"未知搜索源: {engine}")


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
    settings = get_settings()
    max_results = max(1, min(int(max_results or 5), 10))
    engines = [
        item.strip().lower()
        for item in settings.search_engines.split(",")
        if item.strip()
    ] or ["baidu", "sogou", "duckduckgo", "bing"]

    errors: list[str] = []
    collected: list[dict] = []
    for engine in engines:
        try:
            results = _search_with_engine(engine, query, max_results, settings.search_timeout_seconds)
            if results:
                collected.extend(results)
                collected = _dedupe_results(collected, max_results)
                if len(collected) >= max_results:
                    break
            else:
                errors.append(f"{engine}: 无结果")
        except Exception as exc:
            errors.append(f"{engine}: {str(exc)[:180]}")

    if not collected:
        return (
            "搜索失败：所有搜索源均未返回可用结果。"
            f"已尝试：{', '.join(engines)}。"
            f"失败原因：{'; '.join(errors) or '未知'}"
        )

    formatted = [f"搜索源：{', '.join(dict.fromkeys(item['source'] for item in collected if item['source']))}"]
    for i, item in enumerate(collected, 1):
        formatted.append(
            f"{i}. [{item['source']}] {item['title']}\n"
            f"   {item['body'][:240]}\n"
            f"   链接: {item['href']}"
        )
    if errors:
        formatted.append(f"部分搜索源不可用：{'; '.join(errors)}")
    return "\n\n".join(formatted)
