#!/usr/bin/env python3
"""
下载 tiktoken 编码文件到本地，用于离线环境和 PyInstaller 打包

此脚本会下载以下编码文件：
- o200k_base: 用于 gpt-4o, gpt-4o-mini 等模型
- cl100k_base: 用于 gpt-4, gpt-3.5-turbo 等模型
- r50k_base: 用于旧版 GPT 模型
- p50k_base: 用于 code 模型

下载后的文件会保存在项目的 lightrag/tiktoken_cache/ 目录中
"""

import hashlib
import os
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("错误: 需要安装 requests 库")
    print("请运行: pip install requests")
    sys.exit(1)


# 定义需要下载的编码文件
ENCODINGS = {
    "o200k_base": {
        "url": "https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken",
        "hash": "446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d",
        "description": "用于 gpt-4o, gpt-4o-mini 等最新模型",
    },
    "cl100k_base": {
        "url": "https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken",
        "hash": "223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7",
        "description": "用于 gpt-4, gpt-3.5-turbo, text-embedding-ada-002 等模型",
    },
    "r50k_base": {
        "url": "https://openaipublic.blob.core.windows.net/encodings/r50k_base.tiktoken",
        "hash": "306cd27f03c1a714eca7108e03d66b7dc042abe8c258b44c199a7ed9838dd930",
        "description": "用于旧版 GPT-3 模型",
    },
    "p50k_base": {
        "url": "https://openaipublic.blob.core.windows.net/encodings/p50k_base.tiktoken",
        "hash": "94b5ca7dff4d00767bc256fdd1b27e5b17361d7b8a5f968547f9f23eb70d2069",
        "description": "用于 code-davinci 等代码模型",
    },
}


def calculate_sha256(file_path: Path) -> str:
    """计算文件的 SHA256 哈希值"""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def download_file(url: str, output_path: Path, expected_hash: str) -> bool:
    """下载文件并验证哈希值"""
    try:
        print(f"  正在下载: {url}")
        response = requests.get(url, timeout=60)
        response.raise_for_status()

        # 写入文件
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(response.content)

        # 验证哈希
        actual_hash = calculate_sha256(output_path)
        if actual_hash != expected_hash:
            print(f"  ❌ 哈希验证失败!")
            print(f"     期望: {expected_hash}")
            print(f"     实际: {actual_hash}")
            output_path.unlink()
            return False

        file_size = len(response.content) / 1024 / 1024  # MB
        print(f"  ✅ 下载成功 ({file_size:.2f} MB)")
        return True

    except requests.RequestException as e:
        print(f"  ❌ 下载失败: {e}")
        return False
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        return False


def get_cache_key(url: str) -> str:
    """根据 URL 生成缓存文件名（与 tiktoken 逻辑一致）"""
    return hashlib.sha1(url.encode()).hexdigest()


def main():
    """主函数：下载所有编码文件"""
    # 确定输出目录
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    cache_dir = project_dir / "lightrag" / "tiktoken_cache"

    print("=" * 70)
    print("开始下载 tiktoken 编码文件")
    print("=" * 70)
    print(f"目标目录: {cache_dir}")
    print()

    # 创建缓存目录
    cache_dir.mkdir(parents=True, exist_ok=True)

    # 下载每个编码文件
    success_count = 0
    total_count = len(ENCODINGS)

    for encoding_name, info in ENCODINGS.items():
        print(f"[{success_count + 1}/{total_count}] {encoding_name}")
        print(f"  说明: {info['description']}")

        # 生成缓存文件名（与 tiktoken 一致）
        cache_key = get_cache_key(info["url"])
        output_path = cache_dir / cache_key

        # 检查是否已存在且哈希正确
        if output_path.exists():
            actual_hash = calculate_sha256(output_path)
            if actual_hash == info["hash"]:
                print(f"  ℹ️  文件已存在且哈希正确，跳过下载")
                success_count += 1
                print()
                continue
            else:
                print(f"  ⚠️  文件存在但哈希不匹配，重新下载")

        # 下载文件
        if download_file(info["url"], output_path, info["hash"]):
            success_count += 1

        print()

    # 输出结果
    print("=" * 70)
    if success_count == total_count:
        print(f"✅ 全部完成! 成功下载 {success_count}/{total_count} 个文件")
        print()
        print("下载的文件列表:")
        for file in sorted(cache_dir.iterdir()):
            if file.is_file():
                size = file.stat().st_size / 1024 / 1024
                print(f"  - {file.name} ({size:.2f} MB)")
        print()
        print("下一步:")
        print("  1. 运行 PyInstaller 打包程序")
        print("  2. 编码文件会自动包含在打包结果中")
        return 0
    else:
        print(f"⚠️  部分失败: 成功 {success_count}/{total_count} 个文件")
        return 1


if __name__ == "__main__":
    sys.exit(main())
