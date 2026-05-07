"""通用工具函数"""
import re


def strip_markdown(text: str) -> str:
    """去除 Markdown 语法，返回纯文本"""
    result = text
    result = re.sub(r'```[\w]*\n?([\s\S]*?)```', r'\1', result)
    result = re.sub(r'`([^`]+)`', r'\1', result)
    result = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', result)
    result = re.sub(r'\[([^\]]*)\]\([^)]+\)', r'\1', result)
    result = re.sub(r'^#{1,6}\s+', '', result, flags=re.MULTILINE)
    result = re.sub(r'\*\*(.+?)\*\*', r'\1', result)
    result = re.sub(r'__(.+?)__', r'\1', result)
    result = re.sub(r'\*(.+?)\*', r'\1', result)
    result = re.sub(r'_(.+?)_', r'\1', result)
    result = re.sub(r'~~(.+?)~~', r'\1', result)
    result = re.sub(r'^>\s?', '', result, flags=re.MULTILINE)
    result = re.sub(r'^[-*_]{3,}\s*$', '', result, flags=re.MULTILINE)
    result = re.sub(r'^[\s]*[-*+]\s+', '', result, flags=re.MULTILINE)
    result = re.sub(r'^[\s]*\d+\.\s+', '', result, flags=re.MULTILINE)
    result = re.sub(r'<[^>]+>', '', result)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip()
