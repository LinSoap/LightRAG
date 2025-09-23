from fastapi import APIRouter, HTTPException
from lightrag.api.service_manager import service_manager
from lightrag.api.health_checker import health_checker

router = APIRouter(tags=["system"])


@router.get("/overview")
async def get_overview():
    """系统概览端点 - 包含系统状态和collection信息总览"""
    # 执行完整的健康检查
    health_result = await health_checker.check_all_components()

    # 获取基础服务信息
    service_info = service_manager.get_service_info()

    # 合并服务信息到健康检查结果
    health_result["service_manager"] = service_info
    health_result["version"] = "1.4.8"

    # 根据整体状态确定HTTP状态码
    overall_status = health_result.get("overall_status", "unknown")
    if overall_status == "healthy":
        status_code = 200
    elif overall_status == "degraded":
        status_code = 200
    elif overall_status == "unhealthy":
        status_code = 503
    else:
        status_code = 500

    # 如果有严重错误，返回500状态码
    if len(health_result.get("errors", [])) > 0:
        status_code = 500

    # 根据状态返回不同的HTTP状态码
    if status_code != 200:
        raise HTTPException(status_code=status_code, detail=health_result)

    return health_result


@router.get("/service-info")
async def get_service_info():
    """获取详细的服务信息"""
    return service_manager.get_service_info()