"""
技能生成器模块

使用 LLM 自动生成新的技能（Markdown 规范文档）。

生成流程：
1. 用户描述技能需求
2. LLM 生成 Markdown 格式的 Skill 文件
3. 验证格式
4. 注册到技能中心
5. 持久化到磁盘（skills/store/ 目录）
"""
from langchain_core.language_models import BaseChatModel
from agent.prompts import SKILL_GENERATION_PROMPT
from agent.skills.registry import Skill, skill_registry
from datetime import datetime
from pathlib import Path
import re


async def generate_skill(llm: BaseChatModel, description: str) -> Skill:
    """
    使用 LLM 生成新技能（Markdown 规范文档）

    Args:
        llm: 大语言模型实例
        description: 用户对技能需求的描述

    Returns:
        生成并注册好的 Skill 对象
    """
    # 第一步：让 LLM 生成 Markdown 内容
    prompt = SKILL_GENERATION_PROMPT.format(description=description)
    response = await llm.ainvoke(prompt)

    # 第二步：提取 Markdown 内容
    content = _extract_markdown(response.content)

    # 第三步：提取技能名称（从第一个 # 标题）
    name = _extract_name(content, description)

    # 第四步：提取描述（第一个 # 标题后的第一行非空文字）
    skill_description = _extract_description(content, description)

    # 第五步：创建 Skill 对象并注册
    skill = Skill(
        name=name,
        description=skill_description,
        content=content,
        is_builtin=False,
        created_at=datetime.now(),
    )
    skill_registry.register(skill)

    # 第六步：持久化到磁盘
    _persist_skill(name, content)

    return skill


def _extract_markdown(text: str) -> str:
    """
    从 LLM 输出中提取 Markdown 内容

    如果 LLM 用 ```markdown ... ``` 包裹，提取其中内容。
    否则返回原始文本。
    """
    # 尝试提取 markdown 代码块
    match = re.search(r"```(?:markdown)?\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # 如果没有代码块，返回整个文本
    return text.strip()


def _extract_name(content: str, description: str) -> str:
    """
    从 Markdown 内容中提取技能名称

    逻辑：
    1. 尝试从第一个 # 标题提取中文名称
    2. 将中文名称转为英文蛇形命名
    3. 如果无法提取，使用描述生成
    """
    # 提取第一个 # 标题
    match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if match:
        title = match.group(1).strip()
        # 如果标题是中文，尝试生成英文名
        name = _chinese_to_snake(title)
        if name:
            return name

    # 从描述中生成名称
    name = _chinese_to_snake(description)
    if name:
        return name

    # 兜底：使用时间戳
    return f"skill_{int(datetime.now().timestamp())}"


def _extract_description(content: str, fallback: str) -> str:
    """从 Markdown 内容中提取描述"""
    lines = content.split("\n")
    found_title = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# ") and not found_title:
            found_title = True
            continue
        if found_title and stripped and not stripped.startswith("#"):
            return stripped
    return fallback


def _chinese_to_snake(text: str) -> str:
    """
    将中文文本转为英文蛇形命名

    简单映射常见词汇，其余保留原文。
    """
    # 常见中文词汇映射
    word_map = {
        "研究": "research", "助手": "assistant", "编程": "coding",
        "代码": "code", "分析": "analyst", "数据": "data",
        "写作": "writer", "文章": "article", "搜索": "search",
        "计算": "calculator", "翻译": "translate", "转换": "convert",
        "汇率": "currency", "天气": "weather", "新闻": "news",
        "音乐": "music", "图片": "image", "视频": "video",
        "知识": "knowledge", "问答": "qa", "聊天": "chat",
        "管理": "manager", "生成": "generator", "处理": "processor",
        "工具": "tool", "技能": "skill", "测试": "test",
        "监控": "monitor", "提醒": "reminder", "计划": "planner",
        "报告": "report", "邮件": "email", "文档": "document",
    }

    words = []
    remaining = text
    for cn, en in word_map.items():
        if cn in remaining:
            words.append(en)
            remaining = remaining.replace(cn, "", 1)

    if words:
        return "_".join(words)

    # 如果没有匹配到任何中文词汇，尝试用英文
    english_words = re.findall(r"[a-zA-Z]+", text)
    if english_words:
        return "_".join(w.lower() for w in english_words)

    return ""


def _persist_skill(name: str, content: str) -> None:
    """
    将技能内容持久化到磁盘

    保存到 skills/store/{name}.md
    """
    store_dir = Path(__file__).parent / "store"
    store_dir.mkdir(exist_ok=True)
    skill_file = store_dir / f"{name}.md"
    skill_file.write_text(content, encoding="utf-8")
