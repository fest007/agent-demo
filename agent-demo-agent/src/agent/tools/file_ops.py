"""
文件操作工具

提供三个文件操作工具：
- read_file: 读取文件内容
- write_file: 写入文件（自动创建目录）
- list_files: 列出目录内容

安全限制：
- 读取文件大小限制为 100KB，避免内存溢出
- 使用 Path.resolve() 解析绝对路径
"""
from langchain_core.tools import tool
from pathlib import Path


@tool
def read_file(file_path: str) -> str:
    """
    读取指定路径的文件内容。

    Args:
        file_path: 文件路径（相对或绝对路径）

    Returns:
        文件内容文本，或错误信息
    """
    try:
        # resolve() 将相对路径转为绝对路径，避免路径歧义
        path = Path(file_path).resolve()

        if not path.exists():
            return f"文件不存在: {file_path}"

        # 安全限制：超过 100KB 的文件拒绝读取
        if path.stat().st_size > 100_000:
            return f"文件过大 ({path.stat().st_size} bytes)，请指定读取范围"

        return path.read_text(encoding="utf-8")
    except Exception as e:
        return f"读取文件失败: {str(e)}"


@tool
def write_file(file_path: str, content: str) -> str:
    """
    将内容写入指定路径的文件。如果文件不存在会自动创建。

    Args:
        file_path: 目标文件路径
        content: 要写入的内容

    Returns:
        成功或失败信息
    """
    try:
        path = Path(file_path).resolve()
        # parents=True: 递归创建父目录
        # exist_ok=True: 目录已存在时不报错
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"已写入文件: {path}"
    except Exception as e:
        return f"写入文件失败: {str(e)}"


@tool
def list_files(directory: str = ".") -> str:
    """
    列出指定目录下的文件和文件夹。

    Args:
        directory: 目录路径，默认为当前目录

    Returns:
        文件和目录列表（最多 50 项）
    """
    try:
        path = Path(directory).resolve()
        if not path.is_dir():
            return f"目录不存在: {directory}"

        items = []
        # iterdir() 返回目录下的所有条目
        for item in sorted(path.iterdir()):
            prefix = "📁" if item.is_dir() else "📄"
            items.append(f"{prefix} {item.name}")

        # 最多显示 50 项，避免输出过长
        return "\n".join(items[:50]) if items else "目录为空"
    except Exception as e:
        return f"列出文件失败: {str(e)}"
