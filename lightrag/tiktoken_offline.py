"""
Tiktoken 离线模式支持

在程序启动时调用 setup_tiktoken_offline() 来配置 tiktoken 使用本地缓存，
避免在离线环境下尝试从互联网下载编码文件。
"""

import os
import sys
from pathlib import Path


def setup_tiktoken_offline():
    """
    配置 tiktoken 使用本地预下载的编码文件

    此函数会：
    1. 检测运行环境（开发模式 vs PyInstaller 打包）
    2. 设置 TIKTOKEN_CACHE_DIR 环境变量指向本地缓存目录
    3. 如果缓存目录不存在或为空，输出警告信息

    应在任何使用 tiktoken 的代码之前调用此函数。
    """
    # 检测是否在 PyInstaller 打包环境中运行
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # PyInstaller 打包后的运行时环境
        # sys._MEIPASS 是临时解压目录
        base_path = Path(sys._MEIPASS)
        cache_dir = base_path / "lightrag" / "tiktoken_cache"
    else:
        # 开发环境
        # 使用相对于此文件的路径
        base_path = Path(__file__).parent
        cache_dir = base_path / "tiktoken_cache"

    # 设置环境变量
    cache_dir_str = str(cache_dir.absolute())
    os.environ["TIKTOKEN_CACHE_DIR"] = cache_dir_str

    # 验证缓存目录
    if not cache_dir.exists():
        print(f"⚠️  警告: tiktoken 缓存目录不存在: {cache_dir}", file=sys.stderr)
        print("   程序可能会尝试从互联网下载编码文件", file=sys.stderr)
        print("   请运行: python scripts/download_tiktoken_cache.py", file=sys.stderr)
        return False

    # 检查是否有缓存文件
    cache_files = list(cache_dir.glob("*"))
    if not cache_files:
        print(f"⚠️  警告: tiktoken 缓存目录为空: {cache_dir}", file=sys.stderr)
        print("   请运行: python scripts/download_tiktoken_cache.py", file=sys.stderr)
        return False

    # 成功配置 - 显示详细信息
    env_mode = (
        "PyInstaller 打包环境"
        if (getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"))
        else "开发环境"
    )
    print(f"✅ tiktoken 离线模式已启用 ({env_mode})")
    print(f"   缓存目录: {cache_dir}")
    print(f"   编码文件: {len(cache_files)} 个")
    return True


def get_tiktoken_cache_dir() -> Path:
    """
    获取 tiktoken 缓存目录路径

    Returns:
        Path: 缓存目录路径
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)
        return base_path / "lightrag" / "tiktoken_cache"
    else:
        base_path = Path(__file__).parent
        return base_path / "tiktoken_cache"


def verify_tiktoken_cache() -> dict:
    """
    验证 tiktoken 缓存状态

    Returns:
        dict: 包含缓存状态信息的字典
    """
    cache_dir = get_tiktoken_cache_dir()

    result = {
        "cache_dir": str(cache_dir),
        "exists": cache_dir.exists(),
        "files": [],
        "total_size_mb": 0,
    }

    if cache_dir.exists():
        for file in cache_dir.iterdir():
            if file.is_file():
                size_mb = file.stat().st_size / 1024 / 1024
                result["files"].append(
                    {
                        "name": file.name,
                        "size_mb": round(size_mb, 2),
                    }
                )
                result["total_size_mb"] += size_mb

        result["total_size_mb"] = round(result["total_size_mb"], 2)

    return result
