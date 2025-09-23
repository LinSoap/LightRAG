# -*- mode: python ; coding: utf-8 -*-

"""
PyInstaller spec file for LightRAG Server
用于将LightRAG服务打包成独立的可执行文件
"""

block_cipher = None

# 分析所有需要导入的模块
a = Analysis(
    ['../lightrag/api/main.py'],  # 主入口文件
    pathex=[],  # 额外的导入路径
    binaries=[],  # 二进制文件
    datas=[],  # 数据文件（将在下面配置）
    hiddenimports=[  # 隐藏的导入（基于依赖分析结果）
        # 核心模块
        'lightrag.utils.path_manager',
        'lightrag.utils.path_config',
        'lightrag.api.health_checker',
        'lightrag.api.service_manager',
        'lightrag.lightrag_manager',
        'lightrag.lightrag',
        'lightrag.base',
        'lightrag.types',
        'lightrag.constants',
        'lightrag.document_manager',
        'lightrag.exceptions',

        # API路由模块
        'lightrag.api.routers.documents_routers',
        'lightrag.api.routers.query_routers',
        'lightrag.api.routers.graph_routers',
        'lightrag.api.routers.collection_routers',
        'lightrag.api.routers.common',

        # API工具模块
        'lightrag.api.utils.background',
        'lightrag.api.utils.date',
        'lightrag.api.utils.file',

        # API模式模块
        'lightrag.api.schema.collection_schema',
        'lightrag.api.schema.document_schema',
        'lightrag.api.schema.graph_schema',
        'lightrag.api.schema.query_schema',

        # 存储实现
        'lightrag.kg.json_kv_impl',
        'lightrag.kg.nano_vector_db_impl',
        'lightrag.kg.networkx_impl',
        'lightrag.kg.json_doc_status_impl',
        'lightrag.kg.shared_storage',

        # LLM相关
        'lightrag.llm.openai',
        'lightrag.llm.ollama',
        'lightrag.llm.jina',

        # 工具模块
        'lightrag.utils',

        # 第三方库（基于分析结果）
        'numpy',
        'pandas',
        'fastapi',
        'uvicorn',
        'psutil',
        'networkx',
        'pydantic',
        'httpx',
        'aiofiles',
        'python_multipart',
        'json_repair',
        'nano_vectordb',
        'pypinyin',
        'tqdm',
        'tenacity',
        'tiktoken',
        'openai',
        'dotenv',

        # 可选第三方库（如果有的话）
        'yaml',
        'scipy',
        'sklearn',
    ],
    hookspath=['./hooks'],  # 钩子路径
    hooksconfig={},  # 钩子配置
    runtime_hooks=[],  # 运行时钩子
    excludes=[],  # 排除的模块
    win_no_prefer_redirects=False,  # Windows重定向
    win_private_assemblies=False,  # Windows私有程序集
    cipher=block_cipher,  # 加密
    noarchive=False,  # 不创建存档
)

# 配置数据文件
# 格式: (源路径, 目标路径)
datas = [
    # 包含父utils.py文件
    ('../lightrag/utils.py', 'lightrag/utils.py'),

    # 包含字体和静态资源（如果存在）
    # ('../lightrag/tools/lightrag_visualizer/assets', 'lightrag/tools/lightrag_visualizer/assets'),

    # 包含配置文件（可选）
    # ('../pyproject.toml', 'pyproject.toml'),
    # ('../docker-compose.yml', 'docker-compose.yml'),

    # 如果有其他必要的静态资源，可以在这里添加
]

# 过滤掉不需要的文件（如__pycache__、.pyc等）
def remove_py_cache(path):
    """移除Python缓存文件"""
    import os
    for root, dirs, files in os.walk(path):
        # 跳过__pycache__目录
        if '__pycache__' in dirs:
            dirs.remove('__pycache__')

        # 移除.pyc文件
        for file in files:
            if file.endswith('.pyc') or file.endswith('.pyo'):
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                except:
                    pass

# 应用过滤
for data in a.datas:
    if len(data) >= 2 and os.path.isdir(data[0]):
        remove_py_cache(data[0])

# 重新添加过滤后的数据文件
a.datas += [(data[0], data[1], 'DATA') for data in datas]

# 打包配置
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 创建可执行文件
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='lightrag-server',  # 可执行文件名
    debug=False,  # 调试模式
    bootloader_ignore_signals=False,  # 忽略信号
    strip=False,  # 剥离符号
    upx=True,  # 使用UPX压缩
    upx_exclude=[],  # UPX排除列表
    runtime_tmpdir=None,  # 运行时临时目录
    console=True,  # 显示控制台窗口（调试用）
    disable_windowed_traceback=False,  # 禁用窗口回溯
    argv_emulation=False,  # 参数模拟
    target_arch=None,  # 目标架构
    codesign_identity=None,  # 代码签名身份
    entitlements_file=None,  # 权限文件
)

# 可选：创建一个不显示控制台的版本（用于生产环境）
# exe_no_console = EXE(
#     pyz,
#     a.scripts,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     [],
#     name='lightrag-server-console',  # 可执行文件名
#     debug=False,
#     bootloader_ignore_signals=False,
#     strip=False,
#     upx=True,
#     runtime_tmpdir=None,
#     console=False,  # 不显示控制台
#     disable_windowed_traceback=False,
#     argv_emulation=False,
#     target_arch=None,
#     codesign_identity=None,
#     entitlements_file=None,
# )