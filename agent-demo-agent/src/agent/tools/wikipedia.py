from langchain_core.tools import tool


@tool
def wikipedia_query(query: str, lang: str = "zh") -> str:
    """查询维基百科获取百科知识。适合查找定义、历史、人物等事实性信息。"""
    try:
        import wikipedia
        wikipedia.set_lang(lang)
        results = wikipedia.search(query, results=3)
        if not results:
            return "未找到相关维基百科条目"
        summaries = []
        for title in results[:2]:
            try:
                page = wikipedia.page(title, auto_suggest=False)
                summaries.append(f"**{page.title}**\n{page.summary[:500]}")
            except wikipedia.DisambiguationError as e:
                page = wikipedia.page(e.options[0], auto_suggest=False)
                summaries.append(f"**{page.title}**\n{page.summary[:500]}")
            except Exception:
                continue
        return "\n\n".join(summaries) if summaries else "未找到相关维基百科条目"
    except ImportError:
        return "wikipedia 包未安装，请运行: pip install wikipedia"
    except Exception as e:
        return f"维基百科查询失败: {str(e)}"
