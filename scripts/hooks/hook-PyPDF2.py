"""
PyInstaller hook for PyPDF2 library
处理 PyPDF2 库的所有依赖
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules

# 收集所有 PyPDF2 相关模块
datas, binaries, hiddenimports = collect_all("PyPDF2")

# 确保收集所有子模块
hiddenimports += collect_submodules("PyPDF2")
