"""
LightRAG工具包
"""

# 从父utils模块导入所有内容以保持兼容性
import sys
import os
import importlib

# 获取父目录路径
parent_dir = os.path.dirname(os.path.dirname(__file__))

# 检查父utils模块是否存在
parent_utils_path = os.path.join(parent_dir, "utils.py")
if os.path.exists(parent_utils_path):
    # 动态导入父utils模块
    try:
        spec = importlib.util.spec_from_file_location("parent_utils", parent_utils_path)
        parent_utils = importlib.util.module_from_spec(spec)
        sys.modules["parent_utils"] = parent_utils
        spec.loader.exec_module(parent_utils)
        parent_utils_exists = True
    except Exception:
        parent_utils_exists = False
else:
    parent_utils_exists = False

# 如果父utils模块存在，复制其属性
if parent_utils_exists:
    # 将所有父utils的属性复制到当前模块
    for attr_name in dir(parent_utils):
        if not attr_name.startswith('_'):
            globals()[attr_name] = getattr(parent_utils, attr_name)
    parent_all = list(dir(parent_utils))
else:
    parent_all = []

# 导入我们的新模块
from .path_manager import PathManager, get_default_storage_dir, get_working_dir
from .path_config import PathConfig, get_global_config

__all__ = parent_all + [
    "PathManager",
    "get_default_storage_dir",
    "get_working_dir",
    "PathConfig",
    "get_global_config"
]