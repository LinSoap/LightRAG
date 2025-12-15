import os
import sys
import socket
import logging
import argparse
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.middleware.cors import CORSMiddleware
from lightrag.api.routers.documents import create_document_routers
from lightrag.api.routers.query import create_query_routes
from lightrag.api.routers.graph import create_graph_routes
from lightrag.api.routers.collection import create_collection_routes
from lightrag.api.service_manager import service_manager
from lightrag.api.routers.config_routers import create_config_routes

app = FastAPI(docs_url=None, redoc_url=None)

# Mount static files
if getattr(sys, "frozen", False):
    # PyInstaller mode
    base_dir = sys._MEIPASS
    static_dir = os.path.join(base_dir, "lightrag", "api", "static")
    if not os.path.exists(static_dir):
        # Fallback to check other possible locations if needed, or log warning
        print(f"Warning: Static directory not found at {static_dir}, trying root static")
        static_dir = os.path.join(base_dir, "static")
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    static_dir = os.path.join(current_dir, "static")

if not os.path.exists(static_dir):
    # Create empty directory to prevent crash if static files are missing
    print(f"Warning: Static directory {static_dir} does not exist. Creating it to prevent crash.")
    os.makedirs(static_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html(request: Request):
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url=request.url_for("static", path="swagger-ui-bundle.js"),
        swagger_css_url=request.url_for("static", path="swagger-ui.css"),
    )


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
    raise RuntimeError(f"在 {start_port}-{start_port + max_attempts - 1} 范围内无法找到可用端口")


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="LightRAG API Server")
    parser.add_argument("--port", type=int, default=0, help="端口号 (默认: 0表示自动选择)")
    parser.add_argument("--host", default="127.0.0.1", help="绑定地址 (默认: 127.0.0.1)")
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
