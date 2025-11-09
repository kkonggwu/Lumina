import time
from django.conf import settings
from django.http import JsonResponse, HttpRequest
from django.db import connection
from django.core.cache import cache
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework.decorators import api_view
from rest_framework import status


@api_view(["GET"])
@extend_schema(
    summary="健康检查", 
    description="""
    检查服务各个组件的健康状态，用于监控和运维。
    
    **检查项目：**
    - 数据库连接状态
    - 缓存系统状态
    - Django配置状态
    - 系统内存使用情况
    
    **响应说明：**
    - 200: 所有组件正常
    - 503: 部分组件异常
    """,
    tags=["系统监控"],
    responses={
        200: OpenApiResponse(description="所有组件正常"),
        503: OpenApiResponse(description="部分组件异常")
    }
)
def health_check(request: HttpRequest):
    """
    健康检查接口
    
    检查以下组件状态：
    - 数据库连接
    - 缓存系统
    - 服务运行时间
    - 内存使用情况
    """
    health_status = {
        "status": "ok",
        "timestamp": int(time.time()),
        "service": "Lumina",
        "version": "1.0.0",
        "checks": {}
    }
    
    overall_status = "ok"
    
    # 检查数据库连接
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            health_status["checks"]["database"] = {
                "status": "ok",
                "message": "数据库连接正常"
            }
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "error",
            "message": f"数据库连接失败: {str(e)}"
        }
        overall_status = "error"
    
    # 检查缓存系统
    try:
        cache.set("health_check", "ok", 10)
        cache_result = cache.get("health_check")
        if cache_result == "ok":
            health_status["checks"]["cache"] = {
                "status": "ok",
                "message": "缓存系统正常"
            }
        else:
            health_status["checks"]["cache"] = {
                "status": "error",
                "message": "缓存系统异常"
            }
            overall_status = "error"
    except Exception as e:
        health_status["checks"]["cache"] = {
            "status": "error",
            "message": f"缓存系统失败: {str(e)}"
        }
        overall_status = "error"
    
    # 检查Django设置
    try:
        debug_mode = settings.DEBUG
        secret_key = bool(settings.SECRET_KEY)
        health_status["checks"]["settings"] = {
            "status": "ok",
            "message": "Django设置正常",
            "debug_mode": debug_mode,
            "secret_key_configured": secret_key
        }
    except Exception as e:
        health_status["checks"]["settings"] = {
            "status": "error",
            "message": f"Django设置异常: {str(e)}"
        }
        overall_status = "error"
    
    # 系统信息
    import psutil
    try:
        memory = psutil.virtual_memory()
        health_status["system"] = {
            "memory_usage_percent": memory.percent,
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "memory_total_gb": round(memory.total / (1024**3), 2)
        }
    except ImportError:
        health_status["system"] = {
            "message": "psutil未安装，无法获取系统信息"
        }
    except Exception as e:
        health_status["system"] = {
            "error": f"获取系统信息失败: {str(e)}"
        }
    
    health_status["status"] = overall_status
    
    # 根据整体状态返回相应的HTTP状态码
    http_status = status.HTTP_200_OK if overall_status == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JsonResponse(health_status, status=http_status)