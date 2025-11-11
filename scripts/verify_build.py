#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
打包验证脚本
用于验证打包配置是否正确，在打包前检查所有必需的库
"""

import sys
import importlib
from pathlib import Path

# 必需的文档处理库
REQUIRED_LIBS = {
    "docx": "python-docx",
    "pptx": "python-pptx",
    "openpyxl": "openpyxl",
    "PyPDF2": "PyPDF2",
    "PIL": "Pillow",
}

# 核心库
CORE_LIBS = [
    "numpy",
    "pandas",
    "scipy",
    "tiktoken",
    "fastapi",
    "uvicorn",
    "networkx",
]


def check_library(lib_name, package_name=None):
    """检查库是否已安装"""
    if package_name is None:
        package_name = lib_name

    try:
        importlib.import_module(lib_name)
        print(f"✅ {lib_name:20s} - 已安装 (package: {package_name})")
        return True
    except ImportError:
        print(f"❌ {lib_name:20s} - 未安装 (请安装: pip install {package_name})")
        return False


def check_hooks():
    """检查 PyInstaller hooks 是否存在"""
    hooks_dir = Path("scripts/hooks")

    if not hooks_dir.exists():
        print(f"❌ Hooks 目录不存在: {hooks_dir}")
        return False

    required_hooks = [
        "hook-docx.py",
        "hook-pptx.py",
        "hook-PyPDF2.py",
        "hook-openpyxl.py",
        "hook-numpy.py",
        "hook-pandas.py",
        "hook-scipy.py",
    ]

    missing_hooks = []
    for hook in required_hooks:
        hook_path = hooks_dir / hook
        if hook_path.exists():
            print(f"✅ Hook 文件存在: {hook}")
        else:
            print(f"⚠️  Hook 文件缺失: {hook}")
            missing_hooks.append(hook)

    return len(missing_hooks) == 0


def check_spec_file():
    """检查 spec 文件是否存在和配置正确"""
    spec_file = Path("lightrag-server.spec")

    if not spec_file.exists():
        print(f"❌ Spec 文件不存在: {spec_file}")
        return False

    print(f"✅ Spec 文件存在: {spec_file}")

    # 读取并检查关键配置
    with open(spec_file, "r", encoding="utf-8") as f:
        content = f.read()

    checks = {
        "hookspath=['scripts/hooks']": "自定义 hooks 路径",
        "collect_all('docx')": "docx 库收集",
        "collect_all('pptx')": "pptx 库收集",
        "'docx'": "docx 隐藏导入",
        "'pptx'": "pptx 隐藏导入",
    }

    all_passed = True
    for check, description in checks.items():
        if check in content:
            print(f"  ✅ {description}")
        else:
            print(f"  ❌ {description} - 未找到: {check}")
            all_passed = False

    return all_passed


def main():
    """主函数"""
    print("=" * 60)
    print("LightRAG 打包前验证")
    print("=" * 60)

    # 检查文档处理库
    print("\n📚 检查文档处理库:")
    doc_libs_ok = all(
        check_library(lib, package) for lib, package in REQUIRED_LIBS.items()
    )

    # 检查核心库
    print("\n🔧 检查核心库:")
    core_libs_ok = all(check_library(lib) for lib in CORE_LIBS)

    # 检查 PyInstaller
    print("\n📦 检查 PyInstaller:")
    pyinstaller_ok = check_library("PyInstaller", "pyinstaller")

    # 检查 hooks
    print("\n🪝 检查 PyInstaller Hooks:")
    hooks_ok = check_hooks()

    # 检查 spec 文件
    print("\n📄 检查 Spec 文件配置:")
    spec_ok = check_spec_file()

    # 总结
    print("\n" + "=" * 60)
    print("验证结果总结:")
    print("=" * 60)

    results = {
        "文档处理库": doc_libs_ok,
        "核心库": core_libs_ok,
        "PyInstaller": pyinstaller_ok,
        "Hooks 文件": hooks_ok,
        "Spec 文件配置": spec_ok,
    }

    for item, status in results.items():
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {item}")

    all_ok = all(results.values())

    if all_ok:
        print("\n🎉 所有检查通过！可以开始打包了。")
        print("\n运行打包命令:")
        print("  python scripts/build.py")
        print("或")
        print("  pyinstaller lightrag-server.spec --clean")
        return 0
    else:
        print("\n⚠️  存在问题，请先解决上述问题再进行打包。")
        print("\n安装缺失的库:")
        print("  pip install python-docx python-pptx openpyxl PyPDF2 Pillow")
        return 1


if __name__ == "__main__":
    sys.exit(main())
