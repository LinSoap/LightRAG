"""
LightRAG工具包
"""

# 从父utils模块导入所有内容以保持兼容性
import sys
import os
import importlib

# 获取父目录路径
parent_dir = os.path.dirname(os.path.dirname(__file__))

# 动态导入父utils模块
spec = importlib.util.spec_from_file_location("parent_utils", os.path.join(parent_dir, "utils.py"))
parent_utils = importlib.util.module_from_spec(spec)
sys.modules["parent_utils"] = parent_utils
spec.loader.exec_module(parent_utils)

# 将所有父utils的属性复制到当前模块
for attr_name in dir(parent_utils):
    if not attr_name.startswith('_'):
        globals()[attr_name] = getattr(parent_utils, attr_name)

# 导入我们的新模块
from .path_manager import PathManager, get_default_storage_dir, get_working_dir
from .path_config import PathConfig, get_global_config

__all__ = list(dir(parent_utils)) + [
    "PathManager",
    "get_default_storage_dir",
    "get_working_dir",
    "PathConfig",
    "get_global_config"
]