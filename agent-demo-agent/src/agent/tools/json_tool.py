from langchain_core.tools import tool
import json


@tool
def json_parse(json_string: str, query: str = "") -> str:
    """解析 JSON 字符串并可选地查询特定字段。query 为空时返回格式化的 JSON。"""
    try:
        data = json.loads(json_string)
        if query:
            keys = query.split(".")
            result = data
            for key in keys:
                if isinstance(result, dict):
                    result = result.get(key, f"字段 '{key}' 不存在")
                elif isinstance(result, list) and key.isdigit():
                    idx = int(key)
                    result = result[idx] if 0 <= idx < len(result) else f"索引 {idx} 超出范围"
                else:
                    return f"无法查询路径 '{query}'"
            return json.dumps(result, ensure_ascii=False, indent=2)
        return json.dumps(data, ensure_ascii=False, indent=2)
    except json.JSONDecodeError as e:
        return f"JSON 解析失败: {str(e)}"
    except Exception as e:
        return f"查询失败: {str(e)}"
