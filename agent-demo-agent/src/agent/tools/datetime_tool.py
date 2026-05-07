from langchain_core.tools import tool
from datetime import datetime


@tool
def get_datetime(format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """获取当前日期和时间。默认格式为 YYYY-MM-DD HH:MM:SS。"""
    return datetime.now().strftime(format)
