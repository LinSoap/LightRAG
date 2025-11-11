"""
PyInstaller hook for python-docx library
处理 docx 库的所有依赖和数据文件
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules

# 收集所有 docx 相关模块
datas, binaries, hiddenimports = collect_all("docx")

# 确保收集所有子模块
hiddenimports += collect_submodules("docx")

# 添加关键的隐藏导入
hiddenimports += [
    "docx.document",
    "docx.shared",
    "docx.text",
    "docx.text.paragraph",
    "docx.oxml",
    "docx.oxml.text.paragraph",
    "docx.parts",
    "docx.parts.document",
    "lxml",
    "lxml.etree",
]
