"""
路径管理工具 - 处理跨平台存储路径配置
"""
import os
import platform
import shutil
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
    def get_working_dir(workspace: str = "", base_dir: Optional[Union[str, Path]] = None) -> Path:
        """获取工作目录"""
        if base_dir is None:
            base_dir = PathManager.get_default_storage_dir()
        else:
            base_dir = Path(base_dir)

        if workspace:
            return base_dir / workspace
        return base_dir

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

    @staticmethod
    def get_directory_size(directory: Union[str, Path]) -> int:
        """获取目录大小（字节）"""
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                return 0

            total_size = 0
            for dirpath, dirnames, filenames in os.walk(dir_path):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    if os.path.exists(file_path):
                        total_size += os.path.getsize(file_path)

            return total_size
        except Exception as e:
            logger.warning(f"Failed to get directory size for {directory}: {e}")
            return 0

    @staticmethod
    def migrate_data(old_dir: Union[str, Path], new_dir: Union[str, Path], backup: bool = True) -> bool:
        """迁移数据从旧目录到新目录"""
        try:
            old_path = Path(old_dir)
            new_path = Path(new_dir)

            if not old_path.exists():
                logger.info(f"Old directory {old_dir} does not exist, no migration needed")
                return True

            if new_path.exists():
                logger.warning(f"New directory {new_dir} already exists, skipping migration")
                return False

            # 创建备份
            if backup:
                backup_path = old_path.parent / f"{old_path.name}_backup"
                shutil.copytree(old_path, backup_path)
                logger.info(f"Created backup at {backup_path}")

            # 迁移数据
            shutil.copytree(old_path, new_path)
            logger.info(f"Successfully migrated data from {old_dir} to {new_dir}")

            # 可选：删除旧目录
            # shutil.rmtree(old_path)
            # logger.info(f"Removed old directory {old_dir}")

            return True

        except Exception as e:
            logger.error(f"Failed to migrate data from {old_dir} to {new_dir}: {e}")
            return False

    @staticmethod
    def get_storage_info(directory: Union[str, Path]) -> dict:
        """获取存储目录信息"""
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                return {
                    "exists": False,
                    "writable": False,
                    "size_bytes": 0,
                    "size_mb": 0,
                    "file_count": 0
                }

            size_bytes = PathManager.get_directory_size(dir_path)
            file_count = sum(len(files) for _, _, files in os.walk(dir_path))

            return {
                "exists": True,
                "writable": PathManager.is_directory_writable(dir_path),
                "size_bytes": size_bytes,
                "size_mb": size_bytes / 1024 / 1024,
                "file_count": file_count,
                "path": str(dir_path.resolve())
            }

        except Exception as e:
            logger.error(f"Failed to get storage info for {directory}: {e}")
            return {"error": str(e)}


def get_default_storage_dir() -> Path:
    """获取默认存储目录的便捷函数"""
    return PathManager.get_default_storage_dir()


def get_working_dir(workspace: str = "", base_dir: Optional[Union[str, Path]] = None) -> Path:
    """获取工作目录的便捷函数"""
    return PathManager.get_working_dir(workspace, base_dir)