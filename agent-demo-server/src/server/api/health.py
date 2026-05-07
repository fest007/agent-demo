"""
健康检查 API 模块

提供简单的健康检查端点，用于：
- 负载均衡器探测服务是否存活
- Docker 容器健康检查
- 监控系统定期检测
"""
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health_check():
    """返回服务状态"""
    return {"status": "ok", "service": "agent-demo-server"}
