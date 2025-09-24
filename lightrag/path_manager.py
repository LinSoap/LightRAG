"""
路径管理工具 - 处理跨平台存储路径配置
"""

import os
import platform
from pathlib import Path
from typing import Optional, Union
import logging

logger = logging.getLogger(__name__)


class PathManager:
    """路径管理器 - 负责跨平台路径管理"""

    @staticmethod
    def get_default_storage_dir() -> Path:
        """获取默认存储目录（跨平台）"""
        system = platform.system()

        if system == "Windows":
            # Windows: %APPDATA%/LightRAG
            base_dir = Path(os.environ.get("APPDATA", ""))
            return base_dir / "LightRAG"
        elif system == "Darwin":  # macOS
            # macOS: ~/.lightrag
            return Path.home() / ".lightrag"
        else:  # Linux
            # Linux: ~/.lightrag
            return Path.home() / ".lightrag"

    @staticmethod
    def ensure_directory(directory: Union[str, Path]) -> Path:
        """确保目录存在"""
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    @staticmethod
    def is_directory_writable(directory: Union[str, Path]) -> bool:
        """检查目录是否可写"""
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)

            test_file = dir_path / ".write_test"
            test_file.touch()
            test_file.unlink()
            return True
        except Exception as e:
            logger.warning(f"Directory {directory} is not writable: {e}")
            return False


def get_default_storage_dir() -> Path:
    """获取默认存储目录的便捷函数"""
    return PathManager.get_default_storage_dir()
