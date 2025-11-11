"""
PyInstaller hook for openpyxl library
处理 openpyxl 库的所有依赖和数据文件
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules

# 收集所有 openpyxl 相关模块
datas, binaries, hiddenimports = collect_all("openpyxl")

# 确保收集所有子模块
hiddenimports += collect_submodules("openpyxl")

# 添加关键的隐藏导入
hiddenimports += [
    "openpyxl.styles",
    "openpyxl.cell",
    "openpyxl.worksheet",
    "openpyxl.workbook",
]
