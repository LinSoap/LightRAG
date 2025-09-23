import argparse
import socket
import sys
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from lightrag.api.routers.documents_routers import create_document_routers
from lightrag.api.routers.common import router as common_router
from lightrag.api.routers.query_routers import create_query_routes
from lightrag.api.routers.graph_routers import create_graph_routes
from lightrag.api.routers.collection_routers import create_collection_routes
from lightrag.api.service_manager import service_manager, ServiceState
from lightrag.api.health_checker import health_checker
from lightrag.utils.path_config import get_global_config
from lightrag.utils.path_manager import PathManager

app = FastAPI()

# Add CORS middleware to allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 健康检查端点（必须在其他路由之前）
@app.get("/health")
async def health_check():
    """健康检查端点"""
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
    from fastapi import status as http_status
    if status_code != 200:
        from fastapi import HTTPException
        raise HTTPException(status_code=status_code, detail=health_result)

    return health_result


@app.get("/health/detailed")
async def detailed_health_check():
    """详细健康检查端点"""
    health_result = await health_checker.check_all_components()
    health_summary = health_checker.get_health_summary()
    health_trends = health_checker.get_health_trends(hours=24)

    return {
        "current_health": health_result,
        "health_summary": health_summary,
        "health_trends": health_trends,
        "version": "1.4.8"
    }


# 移除健康趋势端点，因为在本地服务场景中不必要
# @app.get("/health/trends")
# async def health_trends(hours: int = 24):
#     """健康趋势端点"""
#     return health_checker.get_health_trends(hours)


@app.get("/service-info")
async def get_service_info():
    """获取详细的服务信息"""
    return service_manager.get_service_info()

# Include the common router
app.include_router(common_router)
app.include_router(create_collection_routes())
app.include_router(create_document_routers())
app.include_router(create_query_routes())
app.include_router(create_graph_routes())


def find_free_port(start_port: int = 9621, max_attempts: int = 100) -> int:
    """查找可用端口"""
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('localhost', port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"在 {start_port}-{start_port + max_attempts - 1} 范围内无法找到可用端口")


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='LightRAG API Server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --port 8080                    # 使用指定端口
  %(prog)s --host 127.0.0.1               # 绑定特定地址
  %(prog)s --storage-dir /path/to/data    # 指定存储目录
  %(prog)s --workspace my_project         # 指定工作空间
  %(prog)s --port 0                       # 自动选择端口
  %(prog)s                                # 使用默认设置
        """
    )
    parser.add_argument(
        '--port',
        type=int,
        default=0,  # 改为默认自动选择端口
        help='指定端口号 (默认: 0表示自动选择)'
    )
    parser.add_argument(
        '--host',
        default='127.0.0.1',
        help='绑定地址 (默认: 127.0.0.1)'
    )
    parser.add_argument(
        '--storage-dir',
        type=str,
        help='存储目录路径 (默认: 使用系统默认路径)'
    )
    parser.add_argument(
        '--workspace',
        type=str,
        default='default',
        help='工作空间名称 (默认: default)'
    )
    parser.add_argument(
        '--reload',
        action='store_true',
        help='启用热重载模式 (仅开发环境使用)'
    )
    parser.add_argument(
        '--log-level',
        choices=['debug', 'info', 'warning', 'error'],
        default='info',
        help='日志级别 (默认: info)'
    )
    parser.add_argument(
        '--migrate-data',
        action='store_true',
        help='从旧目录迁移数据到新目录'
    )
    parser.add_argument(
        '--old-storage-dir',
        type=str,
        help='旧的存储目录路径 (用于数据迁移)'
    )
    return parser.parse_args()


def setup_path_configuration(args):
    """设置路径配置"""
    config = get_global_config()

    # 设置存储目录
    if args.storage_dir:
        config.set_storage_base_dir(args.storage_dir)
        print(f"📁 使用指定的存储目录: {args.storage_dir}")
    else:
        default_dir = PathManager.get_default_storage_dir()
        print(f"📁 使用默认存储目录: {default_dir}")

    # 设置工作空间
    if args.workspace:
        config.set_workspace(args.workspace)
        print(f"🏢 使用工作空间: {args.workspace}")

    # 处理数据迁移
    if args.migrate_data:
        if args.old_storage_dir:
            new_storage_dir = config.get_storage_base_dir() or str(PathManager.get_default_storage_dir())
            print(f"🔄 开始数据迁移: {args.old_storage_dir} -> {new_storage_dir}")

            success = PathManager.migrate_data(
                args.old_storage_dir,
                new_storage_dir,
                backup=True
            )

            if success:
                print("✅ 数据迁移完成")
            else:
                print("❌ 数据迁移失败")
        else:
            print("⚠️  需要指定 --old-storage-dir 参数进行数据迁移")

    # 确保目录存在
    if config.should_auto_create():
        storage_base_dir = config.get_storage_base_dir() or PathManager.get_default_storage_dir()
        working_dir = PathManager.get_working_dir(config.get_workspace(), storage_base_dir)
        PathManager.ensure_directory(working_dir)
        print(f"📂 确保工作目录存在: {working_dir}")


def setup_service_management():
    """设置服务管理"""
    # 设置服务为运行状态
    service_manager.set_running()

    # 注册关闭回调
    def shutdown_callback():
        print("\n🔄 正在执行关闭回调...")

    service_manager.register_shutdown_callback(shutdown_callback)

    print("✅ 服务管理器已启动")


def main():
    import uvicorn
    import logging

    args = parse_args()

    # 设置路径配置
    setup_path_configuration(args)

    # 设置服务管理
    setup_service_management()

    # 确定最终端口
    if args.port == 0:
        port = find_free_port()
        print(f"🚀 LightRAG 服务启动在自动选择的端口: {port}")
    else:
        port = args.port
        print(f"🚀 LightRAG 服务启动在指定端口: {port}")

    # 显示服务信息
    print(f"📍 绑定地址: {args.host}")
    print(f"📖 API文档: http://{args.host}:{port}/docs")
    print(f"💊 健康检查: http://{args.host}:{port}/health")
    print(f"🛡️  按 Ctrl+C 可优雅关闭服务")

    # 设置日志级别
    log_level = getattr(logging, args.log_level.upper())
    logging.basicConfig(level=log_level)

    try:
        # 启动服务
        uvicorn.run(
            "lightrag.api.main:app",
            host=args.host,
            port=port,
            access_log=(args.log_level == 'debug'),
            reload=args.reload,
            log_level=args.log_level
        )
    except KeyboardInterrupt:
        print("\n⚠️  收到中断信号，正在关闭服务...")
        service_manager.initiate_shutdown("KeyboardInterrupt received")
    except Exception as e:
        print(f"\n❌ 服务启动错误: {e}")
        service_manager.set_error(str(e))
        service_manager.initiate_shutdown(f"Service error: {e}")
    finally:
        # 显示最终状态
        service_info = service_manager.get_service_info()
        print(f"\n📊 服务统计:")
        print(f"   - 运行时间: {service_info.get('uptime', 0):.2f} 秒")
        print(f"   - 总请求数: {service_info.get('total_requests', 0)}")
        print(f"   - 最终状态: {service_info.get('state', 'unknown')}")
        if service_info.get('error_message'):
            print(f"   - 错误信息: {service_info['error_message']}")
        print("👋 LightRAG 服务已关闭")


if __name__ == "__main__":
    main()
