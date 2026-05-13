from langchain_core.tools import tool
import httpx
import json
from agent.tools.url_security import validate_public_http_url


@tool
def http_request(
    url: str,
    method: str = "GET",
    headers: str = "",
    body: str = "",
) -> str:
    """发送 HTTP 请求。method 支持 GET/POST/PUT/DELETE。headers 和 body 为 JSON 字符串。"""
    try:
        safe_url = validate_public_http_url(url)
        h = json.loads(headers) if headers else {}
        kwargs = {"url": safe_url, "headers": h, "timeout": 15, "follow_redirects": True}
        if method.upper() == "GET":
            resp = httpx.get(**kwargs)
        elif method.upper() == "POST":
            kwargs["content"] = body
            resp = httpx.post(**kwargs)
        elif method.upper() == "PUT":
            kwargs["content"] = body
            resp = httpx.put(**kwargs)
        elif method.upper() == "DELETE":
            resp = httpx.delete(**kwargs)
        else:
            return f"不支持的 HTTP 方法: {method}"
        validate_public_http_url(str(resp.url))
        return f"状态码: {resp.status_code}\n\n{resp.text[:5000]}"
    except Exception as e:
        return f"HTTP 请求失败: {str(e)}"
