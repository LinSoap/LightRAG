#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LightRAG Server 构建脚本
用于将LightRAG服务打包成独立的可执行文件
"""

import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path


def get_python_executable():
    """获取Python可执行文件路径"""
    return sys.executable


def check_pyinstaller():
    """检查PyInstaller是否安装"""
    try:
        result = subprocess.run([get_python_executable(), '-m', 'PyInstaller', '--version'],
                              capture_output=True, text=True, check=True)
        print(f"PyInstaller已安装，版本: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError:
        print("PyInstaller未安装，正在安装...")
        try:
            subprocess.run([get_python_executable(), '-m', 'pip', 'install', 'pyinstaller'],
                          check=True)
            print("PyInstaller安装成功")
            return True
        except subprocess.CalledProcessError as e:
            print(f"PyInstaller安装失败: {e}")
            return False


def clean_build_artifacts():
    """清理构建产物"""
    build_dirs = ['build', 'dist', '__pycache__']
    for dir_name in build_dirs:
        if os.path.exists(dir_name):
            print(f"清理目录: {dir_name}")
            shutil.rmtree(dir_name)


def create_build_info():
    """创建构建信息文件"""
    info = {
        "build_time": subprocess.run(['date', '+%Y-%m-%d %H:%M:%S'],
                                  capture_output=True, text=True).stdout.strip(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "build_script": __file__
    }

    with open('build_info.txt', 'w', encoding='utf-8') as f:
        f.write("LightRAG Server 构建信息\n")
        f.write("=" * 40 + "\n")
        for key, value in info.items():
            f.write(f"{key}: {value}\n")

    print("构建信息已写入 build_info.txt")


def run_build():
    """运行构建过程"""
    spec_file = "scripts/lightrag-server.spec"

    if not os.path.exists(spec_file):
        print(f"错误: 找不到spec文件 {spec_file}")
        return False

    # 设置工作目录为项目根目录
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    # 运行PyInstaller
    cmd = [get_python_executable(), '-m', 'PyInstaller', spec_file, '--clean']

    print(f"执行构建命令: {' '.join(cmd)}")
    print("构建开始...")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("构建成功！")
        print("构建输出:")
        print(result.stdout)

        if result.stderr:
            print("构建警告/错误:")
            print(result.stderr)

        return True
    except subprocess.CalledProcessError as e:
        print(f"构建失败: {e}")
        print("错误输出:")
        print(e.stdout)
        print(e.stderr)
        return False


def create_portable_package():
    """创建便携式包"""
    dist_dir = Path("dist")
    if not dist_dir.exists():
        print("错误: dist目录不存在")
        return False

    # 查找可执行文件
    exe_files = list(dist_dir.glob("lightrag-server*"))
    if not exe_files:
        print("错误: 未找到可执行文件")
        return False

    exe_file = exe_files[0]
    print(f"找到可执行文件: {exe_file}")

    # 创建启动脚本
    system = platform.system()
    if system == "Windows":
        startup_script = "@echo off\necho Starting LightRAG Server...\n\"%~dp0lightrag-server.exe\" %*"
        script_name = "start_server.bat"
    else:
        startup_script = """#!/bin/bash
echo "Starting LightRAG Server..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
./lightrag-server "$@"
"""
        script_name = "start_server.sh"

    with open(dist_dir / script_name, 'w', encoding='utf-8') as f:
        f.write(startup_script)

    if system != "Windows":
        # 设置执行权限
        os.chmod(dist_dir / script_name, 0o755)

    print(f"启动脚本已创建: {dist_dir / script_name}")

    # 创建README文件
    readme_content = """# LightRAG Server 便携版

## 使用方法

### Windows
```cmd
start_server.bat --port 8000 --host 0.0.0.0
```

### Linux/Mac
```bash
chmod +x start_server.sh
./start_server.sh --port 8000 --host 0.0.0.0
```

### 直接运行
```bash
./lightrag-server --port 8000 --host 0.0.0.0
```

## 参数说明
- `--port`: 服务端口 (默认: 8000)
- `--host`: 监听地址 (默认: 127.0.0.1)
- `--reload`: 启用热重载 (开发模式)
- `--log-level`: 日志级别 (debug, info, warning, error)

## 默认配置
- API文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health
- 存储路径: ./rag_storage/
"""

    with open(dist_dir / "README.txt", 'w', encoding='utf-8') as f:
        f.write(readme_content)

    print("README文件已创建")


def main():
    """主函数"""
    print("LightRAG Server 构建脚本")
    print("=" * 40)

    # 检查PyInstaller
    if not check_pyinstaller():
        sys.exit(1)

    # 清理之前的构建产物
    clean_build_artifacts()

    # 创建构建信息
    create_build_info()

    # 运行构建
    if not run_build():
        sys.exit(1)

    # 创建便携式包
    create_portable_package()

    print("\n" + "=" * 40)
    print("构建完成！")
    print("可执行文件位置: ./dist/")
    print("使用说明请查看 ./dist/README.txt")


if __name__ == "__main__":
    main()