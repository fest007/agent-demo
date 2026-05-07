"""
MCP（Model Context Protocol）客户端模块

MCP 是一种开放协议，允许 AI 应用连接外部工具服务器。
通过 MCP，Agent 可以使用文件系统操作、数据库查询等外部能力。

支持的传输方式：
- stdio: 本地子进程（如 npx 启动的 MCP 服务器）
- streamable_http: 远程 HTTP 服务
- sse: Server-Sent Events（旧版兼容）

配置文件格式（mcp_servers/config.json）：
{
  "filesystem": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"],
    "transport": "stdio"
  }
}
"""
import json
from pathlib import Path
from agent.config import get_settings


async def load_mcp_tools() -> list:
    """
    加载 MCP 服务器配置并获取工具列表

    流程：
    1. 读取 mcp_servers/config.json 配置文件
    2. 使用 langchain-mcp-adapters 连接配置的 MCP 服务器
    3. 获取所有可用工具
    4. 返回工具列表（可直接传给 create_react_agent）

    Returns:
        MCP 工具列表，如果配置不存在或加载失败返回空列表
    """
    settings = get_settings()
    config_path = Path(settings.mcp_config_path)

    # 配置文件不存在，跳过
    if not config_path.exists():
        return []

    try:
        # 读取配置
        config = json.loads(config_path.read_text())
    except (json.JSONDecodeError, OSError):
        return []

    # 配置为空，跳过
    if not config:
        return []

    try:
        # 使用 langchain-mcp-adapters 的 MultiServerMCPClient
        # 它支持同时连接多个 MCP 服务器
        from langchain_mcp_adapters.client import MultiServerMCPClient
        client = MultiServerMCPClient(config)
        tools = await client.get_tools()
        return tools
    except Exception:
        # MCP 加载失败不影响核心功能
        return []
