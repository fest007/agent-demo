from langchain_core.tools import tool
import csv
import io


@tool
def csv_query(csv_content: str, query: str = "") -> str:
    """解析 CSV 内容并可选地查询。query 为空时返回前 20 行预览。"""
    try:
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)
        if not rows:
            return "CSV 内容为空"
        if query:
            query_lower = query.lower()
            filtered = [r for r in rows if any(query_lower in str(v).lower() for v in r.values())]
            if not filtered:
                return f"未找到匹配 '{query}' 的行"
            return "\n".join([", ".join(f"{k}: {v}" for k, v in row.items()) for row in filtered[:20]])
        preview = rows[:20]
        headers = list(rows[0].keys())
        lines = [", ".join(headers)]
        for row in preview:
            lines.append(", ".join(str(row[h]) for h in headers))
        total = len(rows)
        if total > 20:
            lines.append(f"\n... 共 {total} 行，仅显示前 20 行")
        return "\n".join(lines)
    except Exception as e:
        return f"CSV 解析失败: {str(e)}"
