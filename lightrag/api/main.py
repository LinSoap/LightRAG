import argparse
import socket
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from lightrag.api.routers.documents import create_document_routers
from lightrag.api.routers.query import create_query_routes
from lightrag.api.routers.graph import create_graph_routes
from lightrag.api.routers.collection import create_collection_routes
from lightrag.api.service_manager import service_manager
from lightrag.api.routers.config_routers import create_config_routes

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(create_collection_routes())
app.include_router(create_document_routers())
app.include_router(create_query_routes())
app.include_router(create_graph_routes())
app.include_router(create_config_routes())


def find_free_port(start_port: int = 9621, max_attempts: int = 100) -> int:
    """查找可用端口"""
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("localhost", port))
                return port
            except OSError:
                continue
    raise RuntimeError(
        f"在 {start_port}-{start_port + max_attempts - 1} 范围内无法找到可用端口"
    )


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="LightRAG API Server")
    parser.add_argument(
        "--port", type=int, default=0, help="端口号 (默认: 0表示自动选择)"
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="绑定地址 (默认: 127.0.0.1)"
    )
    parser.add_argument("--storage-dir", type=str, help="存储目录路径")
    parser.add_argument("--config", type=str, help="配置文件路径 (config.json)")
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error"],
        default="info",
        help="日志级别",
    )
    return parser.parse_args()


async def main_async():
    """异步主函数"""
    args = parse_args()

    port = find_free_port() if args.port == 0 else args.port
    print(f"🚀 LightRAG 启动: http://{args.host}:{port}")
    print(f"📖 API文档: http://{args.host}:{port}/docs")
    print(f"💊 系统概览: http://{args.host}:{port}/overview")
    print(f"⚙️ 配置管理: http://{args.host}:{port}/api/config/models")

    logging.basicConfig(level=getattr(logging, args.log_level.upper()))

    return args, port


def main():
    import uvicorn

    # 运行异步初始化
    try:
        import asyncio

        args, port = asyncio.run(main_async())
    except Exception as e:
        print(f"❌ 启动失败: {str(e)}")
        return

    try:
        uvicorn.run(
            "lightrag.api.main:app",
            host=args.host,
            port=port,
            access_log=(args.log_level == "debug"),
            log_level=args.log_level,
        )
    except KeyboardInterrupt:
        service_manager.initiate_shutdown("KeyboardInterrupt received")
    except Exception as e:
        service_manager.set_error(str(e))
        service_manager.initiate_shutdown(f"Service error: {e}")
    finally:
        service_info = service_manager.get_service_info()
        print(f"\n📊 服务运行时间: {service_info.get('uptime', 0):.2f} 秒")
        print("👋 LightRAG 服务已关闭")


if __name__ == "__main__":
    main()
