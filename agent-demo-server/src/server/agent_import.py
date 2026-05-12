"""
Agent 包导入辅助。

server 当前以库调用方式复用 agent-demo-agent，而不是通过 HTTP 调用独立服务。
这里集中处理 agent-demo-agent/src 的路径注入，避免各路由重复修改 sys.path。
"""
from pathlib import Path
import sys

from server.config import get_settings


def ensure_agent_on_path() -> None:
    """将 agent-demo-agent/src 加入 sys.path，保证 server 可导入 agent 包。"""
    settings = get_settings()
    server_root = Path(__file__).resolve().parent.parent.parent
    agent_root = (server_root / settings.agent_module_path).resolve()
    agent_src = agent_root / "src"

    agent_src_str = str(agent_src)
    if agent_src_str not in sys.path:
        sys.path.insert(0, agent_src_str)
