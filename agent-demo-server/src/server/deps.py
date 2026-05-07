"""
依赖注入模块

FastAPI 的依赖注入机制：
- 通过 Depends() 声明依赖
- FastAPI 自动解析并注入到路由函数参数中
- 支持嵌套依赖

本模块定义了用户上下文的获取方式。
初版返回默认用户，后续可替换为 JWT/OAuth 认证。
"""
from fastapi import Request
from dataclasses import dataclass


@dataclass
class UserContext:
    """
    用户上下文

    存储当前请求的用户信息。
    所有需要用户信息的 API 都通过依赖注入获取这个对象。
    """
    user_id: str = "default"   # 用户唯一标识
    username: str = "default"  # 用户名


async def get_current_user(request: Request) -> UserContext:
    """
    获取当前用户的依赖函数

    初版实现：返回默认用户（不验证身份）。
    后续接入认证后，只需修改这个函数：
    1. 从请求头中提取 JWT Token
    2. 验证 Token 有效性
    3. 解析出用户信息
    4. 返回 UserContext

    Args:
        request: FastAPI 请求对象

    Returns:
        UserContext 实例
    """
    # TODO: 后续接入 JWT/Session 认证
    return UserContext(user_id="default", username="default")
