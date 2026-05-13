"""
工具中心模块

统一注册和管理所有内置工具。
LangChain 的 @tool 装饰器会自动将函数转换为 BaseTool 对象，
LLM 可以通过 Function Calling 机制调用这些工具。

工具列表（共 14 个）：
- web_search: 多源网络搜索（默认 Baidu/Sogou/DuckDuckGo/Bing fallback）
- wikipedia_query: 维基百科查询
- web_scraper: 网页内容抓取
- calculator: 数学表达式计算
- get_datetime: 获取当前日期时间
- read_file / write_file / list_files: 文件操作
- run_shell: Shell 命令执行
- python_repl: Python 代码执行
- json_parse: JSON 解析与查询
- csv_query: CSV 数据查询
- http_request: HTTP 请求
- url_to_knowledge: URL 内容抓取并入库
"""
from agent.tools.registry import tool_registry
from agent.tools.search import web_search
from agent.tools.wikipedia import wikipedia_query
from agent.tools.web_scraper import web_scraper
from agent.tools.calculator import calculator
from agent.tools.datetime_tool import get_datetime
from agent.tools.file_ops import read_file, write_file, list_files
from agent.tools.shell import run_shell
from agent.tools.python_repl import python_repl
from agent.tools.json_tool import json_parse
from agent.tools.csv_tool import csv_query
from agent.tools.http_tool import http_request
from agent.tools.url_to_knowledge import url_to_knowledge
from agent.config import get_settings


DANGEROUS_TOOLS = {"write_file", "run_shell", "python_repl"}


def register_all_tools() -> list:
    """
    注册所有内置工具到全局工具注册中心

    Returns:
        list: 所有工具对象的列表，可直接传给 create_react_agent
    """
    tools = [
        web_search,         # 多源网络搜索
        wikipedia_query,    # 维基百科
        web_scraper,        # 网页抓取
        calculator,         # 计算器
        get_datetime,       # 日期时间
        read_file,          # 读文件
        write_file,         # 写文件
        list_files,         # 列目录
        run_shell,          # Shell 命令
        python_repl,        # Python 执行
        json_parse,         # JSON 解析
        csv_query,          # CSV 查询
        http_request,       # HTTP 请求
        url_to_knowledge,   # URL 入库
    ]

    # 将每个工具注册到全局注册中心（支持动态启用/禁用）
    for t in tools:
        tool_registry.register(t)

    settings = get_settings()
    if not settings.enable_dangerous_tools:
        tool_registry.apply_default_policy(DANGEROUS_TOOLS)

    return tool_registry.get_all()


__all__ = ["tool_registry", "register_all_tools"]
