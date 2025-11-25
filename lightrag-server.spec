# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
import tiktoken
import os

datas = []
binaries = []
hiddenimports = []
tmp_ret = collect_all('lightrag')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('numpy')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pandas')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('scipy')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# 显式添加静态文件，确保 Swagger UI 资源被包含
if os.path.exists('lightrag/api/static'):
    datas.append(('lightrag/api/static', 'lightrag/api/static'))

# 收集文档处理库
try:
    tmp_ret = collect_all('docx')
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
except Exception as e:
    print(f"Warning: Could not collect docx: {e}")

try:
    tmp_ret = collect_all('pptx')
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
except Exception as e:
    print(f"Warning: Could not collect pptx: {e}")

try:
    tmp_ret = collect_all('openpyxl')
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
except Exception as e:
    print(f"Warning: Could not collect openpyxl: {e}")

try:
    tmp_ret = collect_all('PyPDF2')
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
except Exception as e:
    print(f"Warning: Could not collect PyPDF2: {e}")

try:
    tmp_ret = collect_all('PIL')
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
except Exception as e:
    print(f"Warning: Could not collect PIL: {e}")

# 添加 tiktoken 相关的数据文件和隐藏导入
tiktoken_path = os.path.dirname(tiktoken.__file__)
datas.append((os.path.join(tiktoken_path, '*'), 'tiktoken'))
# 添加 tiktoken_ext
tiktoken_ext_path = os.path.join(os.path.dirname(tiktoken.__file__), 'tiktoken_ext')
if os.path.exists(tiktoken_ext_path):
    datas.append((os.path.join(tiktoken_ext_path, '*'), 'tiktoken_ext'))

# 隐藏导入模块
hiddenimports.extend([
    'tiktoken',
    'tiktoken_ext',
    'tiktoken_ext.openai_public',
    'tiktoken.registry',
    # 文档处理库 - 运行时动态导入的模块
    'docx',  # python-docx
    'docx.document',
    'docx.shared',
    'docx.text',
    'pptx',  # python-pptx
    'pptx.presentation',
    'openpyxl',  # Excel处理
    'PyPDF2',  # PDF处理
    'PIL',  # 图片处理
    'PIL.Image',
    # 其他可能的运行时导入
    'pipmaster',  # 包管理器
])


a = Analysis(
    ['lightrag/api/main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['scripts/hooks'],  # 添加自定义 hooks 路径
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='lightrag-server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
