"""
技能执行器模块

提供技能的查询和管理接口。
供后端 API 层调用。
"""
from agent.skills.registry import Skill, skill_registry


def get_skill(name: str) -> Skill | None:
    """按名称获取技能"""
    return skill_registry.get(name)


def list_skills() -> list[dict]:
    """列出所有技能（返回字典格式，适合 API 序列化）"""
    skills = skill_registry.list_all()
    return [
        {
            "name": s.name,
            "description": s.description,
            "content": s.content,
            "is_builtin": s.is_builtin,
            "created_at": s.created_at.isoformat(),
        }
        for s in skills
    ]
