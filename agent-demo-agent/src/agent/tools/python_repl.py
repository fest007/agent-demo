"""
Python REPL 工具

REPL = Read-Eval-Print Loop（读取-求值-输出 循环）
允许 Agent 执行 Python 代码并获取输出。

实现原理：
- 使用 exec() 执行代码
- 通过重定向 sys.stdout 捕获 print() 输出
- 代码在一个受限的全局命名空间中执行
"""
from langchain_core.tools import tool
from io import StringIO
import sys


@tool
def python_repl(code: str) -> str:
    """
    执行 Python 代码并返回输出。

    适合数据处理、数学计算、调试等任务。
    Agent 会自动编写 Python 代码来解决问题。

    Args:
        code: 要执行的 Python 代码

    Returns:
        代码的 print() 输出，或错误信息
    """
    # 保存原始的 stdout，执行完后恢复
    old_stdout = sys.stdout

    # 创建一个 StringIO 对象来捕获输出
    redirected_output = StringIO()
    sys.stdout = redirected_output  # 将 stdout 重定向到 StringIO

    try:
        # exec() 执行 Python 代码
        # 第二个参数是全局命名空间，只暴露 __builtins__
        exec(code, {"__builtins__": __builtins__})

        # 获取捕获到的输出
        output = redirected_output.getvalue()
        return output if output else "代码执行完成，无输出"
    except Exception as e:
        return f"代码执行失败: {type(e).__name__}: {str(e)}"
    finally:
        # 无论成功失败，都恢复原始 stdout
        sys.stdout = old_stdout
