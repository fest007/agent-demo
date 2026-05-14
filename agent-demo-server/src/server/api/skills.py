"""
技能管理 API 模块

提供技能的查询和生成接口：
- GET /api/skills/list: 列出所有技能
- GET /api/skills/{name}: 获取技能详情
- PUT /api/skills/{name}: 更新技能
- POST /api/skills/generate: LLM 自动生成新技能
"""
from fastapi import APIRouter, Depends, HTTPException
from server.models.skill import SkillInfo, SkillCreateRequest, SkillGenerateRequest, SkillUpdateRequest
from server.deps import get_current_user, UserContext
from server.agent_import import ensure_agent_on_path

router = APIRouter(prefix="/api/skills", tags=["skills"])


def _get_skills():
    """动态导入技能模块，如果技能注册中心为空则先加载所有技能"""
    ensure_agent_on_path()
    from agent.skills.executor import list_skills, get_skill
    from agent.skills.generator import generate_skill
    from agent.skills.registry import Skill, skill_registry, load_builtin_skills, load_persisted_skills

    # 如果注册中心为空，加载所有技能
    if not skill_registry.list_all():
        load_builtin_skills()
        load_persisted_skills()

    return list_skills, get_skill, generate_skill, Skill, skill_registry


@router.get("/list")
async def list_all_skills(user: UserContext = Depends(get_current_user)):
    """列出所有已注册的技能（内置 + 自定义）"""
    list_skills_fn, _, _, _, _ = _get_skills()
    return list_skills_fn()


@router.get("/{skill_name}")
async def get_skill_detail(skill_name: str, user: UserContext = Depends(get_current_user)):
    """获取技能详情"""
    _, get_skill_fn, _, _, _ = _get_skills()
    skill = get_skill_fn(skill_name)
    if not skill:
        raise HTTPException(status_code=404, detail=f"技能 '{skill_name}' 不存在")
    return {
        "name": skill.name,
        "description": skill.description,
        "content": skill.content,
        "is_builtin": skill.is_builtin,
        "created_at": skill.created_at.isoformat(),
    }


@router.put("/{skill_name}")
async def update_skill(
    skill_name: str,
    request: SkillUpdateRequest,
    user: UserContext = Depends(get_current_user),
):
    """更新技能的描述和内容"""
    _, get_skill_fn, _, _, _ = _get_skills()
    skill = get_skill_fn(skill_name)
    if not skill:
        raise HTTPException(status_code=404, detail=f"技能 '{skill_name}' 不存在")
    if request.description is not None:
        skill.description = request.description
    if request.content is not None:
        skill.content = request.content
    return {
        "status": "success",
        "name": skill.name,
        "description": skill.description,
        "content": skill.content,
    }


@router.post("/generate")
async def generate_skill_endpoint(
    request: SkillGenerateRequest,
    user: UserContext = Depends(get_current_user),
):
    """
    LLM 自动生成新技能

    流程：
    1. 用户描述技能需求
    2. LLM 生成 Markdown 格式的 Skill 规范文档
    3. 自动注册并持久化
    """
    _, _, generate_skill_fn, _, _ = _get_skills()

    ensure_agent_on_path()
    from agent.config import get_settings
    from langchain_openai import ChatOpenAI
    from agent.model_providers import resolve_model_config

    settings = get_settings()
    model_config = resolve_model_config(
        provider_id=request.model_provider,
        model_id=request.model,
        key_id=request.api_key_id,
        purpose="fast",
    )
    base_url = request.custom_base_url or model_config.base_url
    api_key = request.custom_api_key or model_config.api_key
    llm = ChatOpenAI(
        model=model_config.model,
        api_key=api_key,
        base_url=base_url,
        timeout=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
    )

    try:
        skill = await generate_skill_fn(llm, request.description)
        return {"status": "success", "name": skill.name, "description": skill.description}
    except Exception as e:
        return {"status": "error", "message": str(e)}
