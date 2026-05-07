"""
Shell 命令执行工具

允许 Agent 执行系统 Shell 命令。
注意：这个工具会实际执行命令，存在安全风险，仅用于本地开发测试。
"""
from langchain_core.tools import tool
import subprocess


@tool
def run_shell(command: str, timeout: int = 30) -> str:
    """
    执行 Shell 命令并返回输出。

    Args:
        command: 要执行的 Shell 命令（如 "ls -la", "pip install xxx"）
        timeout: 超时时间（秒），默认 30 秒

    Returns:
        命令的标准输出 + 标准错误输出
    """
    try:
        # subprocess.run 执行命令并捕获输出
        # shell=True: 通过 shell 执行（支持管道、重定向等）
        # capture_output=True: 捕获 stdout 和 stderr
        # text=True: 输出为字符串而非 bytes
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        # 拼接标准输出和标准错误
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"
        if result.returncode != 0:
            output += f"\n[退出码: {result.returncode}]"

        return output.strip() if output.strip() else "命令执行完成，无输出"
    except subprocess.TimeoutExpired:
        return f"命令执行超时 ({timeout}秒)"
    except Exception as e:
        return f"命令执行失败: {str(e)}"
