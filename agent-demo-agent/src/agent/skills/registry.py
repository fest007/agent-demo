"""
技能注册中心模块

技能（Skill）是 Markdown 格式的规范文档，用于指导 AI 的行为。
与工具不同，技能不是可执行代码，而是"给 AI 写的 SOP"：

- 工具：单个原子操作（如搜索、计算）
- 技能：Markdown 规范文档（如研究助手规范、编程助手规范）

内置技能：
- research: 研究助手
- coding: 编程助手
- data_analyst: 数据分析
- writer: 写作助手

自定义技能：
- 通过 LLM 自动生成 Markdown 规范文档，注册为新技能
"""
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class Skill:
    """
    技能数据类

    属性：
    - name: 技能名称（唯一标识，英文蛇形命名）
    - description: 一句话描述
    - content: Markdown 内容（核心，包含规则、示例、禁止事项）
    - is_builtin: 是否为内置技能
    - created_at: 创建时间
    """
    name: str
    description: str
    content: str = ""
    is_builtin: bool = True
    created_at: datetime = field(default_factory=datetime.now)


class SkillRegistry:
    """
    技能注册中心

    管理所有技能的注册、查询和删除。
    技能以 Markdown 文件形式存储，按需加载到内存。
    """

    def __init__(self):
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        """注册一个技能"""
        self._skills[skill.name] = skill

    def get(self, name: str) -> Skill | None:
        """按名称获取技能"""
        return self._skills.get(name)

    def list_all(self) -> list[Skill]:
        """列出所有技能"""
        return list(self._skills.values())

    def list_names(self) -> list[str]:
        """列出所有技能名称"""
        return list(self._skills.keys())

    def remove(self, name: str) -> bool:
        """删除一个技能，返回是否成功"""
        if name in self._skills:
            del self._skills[name]
            return True
        return False


# 全局单例
skill_registry = SkillRegistry()


def load_builtin_skills() -> None:
    """
    从 builtin/ 目录加载内置技能的 .md 文件

    文件格式：
    - 文件名即技能名（如 research.md → research）
    - 第一个 # 标题后的文字作为 description
    - 整个文件内容作为 content
    """
    builtin_dir = Path(__file__).parent / "builtin"
    if not builtin_dir.exists():
        return

    for md_file in builtin_dir.glob("*.md"):
        _load_skill_from_md(md_file, is_builtin=True)


def load_persisted_skills() -> None:
    """
    从 store/ 目录加载用户生成的持久化技能 .md 文件
    """
    store_dir = Path(__file__).parent / "store"
    if not store_dir.exists():
        return

    for md_file in store_dir.glob("*.md"):
        _load_skill_from_md(md_file, is_builtin=False)


def _load_skill_from_md(md_file: Path, is_builtin: bool = True) -> None:
    """
    从 .md 文件加载一个技能

    解析逻辑：
    - 文件名（不含扩展名）作为 name
    - 第一个 # 标题后的第一行非空文字作为 description
    - 整个文件内容作为 content
    - 文件修改时间作为 created_at
    """
    content = md_file.read_text(encoding="utf-8")
    name = md_file.stem

    # 提取 description：第一个 # 标题后的第一行非空文字
    description = ""
    lines = content.split("\n")
    found_title = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# ") and not found_title:
            found_title = True
            continue
        if found_title and stripped and not stripped.startswith("#"):
            description = stripped
            break

    if not description:
        description = f"技能: {name}"

    skill = Skill(
        name=name,
        description=description,
        content=content,
        is_builtin=is_builtin,
        created_at=datetime.fromtimestamp(md_file.stat().st_mtime),
    )
    skill_registry.register(skill)
