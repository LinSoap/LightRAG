"""
PyInstaller hook for python-pptx library
处理 pptx 库的所有依赖和数据文件
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules

# 收集所有 pptx 相关模块
datas, binaries, hiddenimports = collect_all("pptx")

# 确保收集所有子模块
hiddenimports += collect_submodules("pptx")

# 添加关键的隐藏导入
hiddenimports += [
    "pptx.presentation",
    "pptx.slide",
    "pptx.shapes",
    "pptx.util",
    "pptx.oxml",
    "lxml",
    "lxml.etree",
]
