import argparse
import socket
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from lightrag.api.routers.documents_routers import create_document_routers
from lightrag.api.routers.common import router as common_router
from lightrag.api.routers.query_routers import create_query_routes
from lightrag.api.routers.graph_routers import create_graph_routes
from lightrag.api.routers.collection_routers import create_collection_routes

app = FastAPI()

# Add CORS middleware to allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
  %(prog)s --port 8080           # 使用指定端口
  %(prog)s --host 127.0.0.1      # 绑定特定地址
  %(prog)s --port 0              # 自动选择端口
  %(prog)s                       # 使用默认设置
        """
    )
    parser.add_argument(
        '--port',
        type=int,
        default=9621,
        help='指定端口号 (默认: 9621, 0表示自动选择)'
    )
    parser.add_argument(
        '--host',
        default='127.0.0.1',
        help='绑定地址 (默认: 127.0.0.1)'
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
    return parser.parse_args()


def main():
    import uvicorn
    import logging

    args = parse_args()

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

    # 设置日志级别
    log_level = getattr(logging, args.log_level.upper())
    logging.basicConfig(level=log_level)

    # 启动服务
    uvicorn.run(
        "lightrag.api.main:app",
        host=args.host,
        port=port,
        access_log=(args.log_level == 'debug'),
        reload=args.reload,
        log_level=args.log_level
    )


if __name__ == "__main__":
    main()
