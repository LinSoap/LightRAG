"""
Configuration storage and persistence management for LightRAG.
"""

import os
import json
import stat
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from lightrag.api.schemas.config import LightRAGConfig
from .exceptions import ConfigStorageError, ConfigPermissionError, ConfigNotFoundError
from lightrag.utils import logger


class ConfigStorage:
    """配置存储管理器"""

    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化配置存储管理器

        Args:
            config_dir: 配置目录路径，默认为 ~/.lightrag
        """
        self.config_dir = Path(config_dir) if config_dir else self._get_default_config_dir()
        self.config_file = self.config_dir / "config.json"
        self.backup_dir = self.config_dir / "backups"
        self._ensure_directories()

    def _get_default_config_dir(self) -> Path:
        """获取默认配置目录"""
        # 优先使用环境变量中的配置
        if "LIGHTRAG_CONFIG_DIR" in os.environ:
            return Path(os.environ["LIGHTRAG_CONFIG_DIR"])

        # 默认使用用户主目录下的 .lightrag
        home_dir = Path.home()
        return home_dir / ".lightrag"

    def _ensure_directories(self):
        """确保必要的目录存在"""
        try:
            # 创建主配置目录
            self.config_dir.mkdir(parents=True, exist_ok=True)

            # 创建备份目录
            self.backup_dir.mkdir(parents=True, exist_ok=True)

            # 设置目录权限 (700 - 仅所有者可读写执行)
            self.config_dir.chmod(0o700)
            self.backup_dir.chmod(0o700)

            logger.info(f"配置目录已创建: {self.config_dir}")

        except Exception as e:
            raise ConfigStorageError(
                f"无法创建配置目录: {str(e)}",
                file_path=str(self.config_dir),
                details={"error": str(e)}
            )

    def _ensure_file_permissions(self, file_path: Path):
        """确保文件权限正确 (600 - 仅所有者可读写)"""
        try:
            if file_path.exists():
                current_mode = file_path.stat().st_mode
                required_mode = stat.S_IRUSR | stat.S_IWUSR  # 600

                if (current_mode & 0o777) != required_mode:
                    file_path.chmod(required_mode)
                    logger.debug(f"文件权限已修正: {file_path}")

        except Exception as e:
            raise ConfigPermissionError(
                f"无法设置文件权限: {str(e)}",
                file_path=str(file_path),
                required_permissions="600"
            )

    def _create_backup(self) -> Path:
        """创建配置文件备份"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"config_{timestamp}.json"

        try:
            if self.config_file.exists():
                shutil.copy2(self.config_file, backup_file)
                # 设置备份文件权限
                backup_file.chmod(0o600)
                logger.info(f"配置备份已创建: {backup_file}")

                # 清理旧备份 (保留最近10个)
                self._cleanup_old_backups()

            return backup_file

        except Exception as e:
            raise ConfigStorageError(
                f"无法创建配置备份: {str(e)}",
                file_path=str(backup_file),
                details={"error": str(e)}
            )

    def _cleanup_old_backups(self, keep_count: int = 10):
        """清理旧备份文件"""
        try:
            backup_files = sorted(self.backup_dir.glob("config_*.json"), key=lambda x: x.stat().st_mtime)

            if len(backup_files) > keep_count:
                for backup_file in backup_files[:-keep_count]:
                    backup_file.unlink()
                    logger.debug(f"旧备份已删除: {backup_file}")

        except Exception as e:
            logger.warning(f"清理旧备份失败: {str(e)}")

    def load_config(self) -> LightRAGConfig:
        """加载配置文件"""
        try:
            if not self.config_file.exists():
                logger.info("配置文件不存在，创建默认配置")
                default_config = LightRAGConfig.get_default_config()
                self.save_config(default_config)
                return default_config

            # 检查文件权限
            self._ensure_file_permissions(self.config_file)

            # 读取配置文件
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            # 解析配置
            config = LightRAGConfig.parse_obj(config_data)
            logger.info(f"配置已加载: {self.config_file}")

            return config

        except json.JSONDecodeError as e:
            # 配置文件损坏，创建备份并重置
            logger.error(f"配置文件格式错误: {str(e)}")
            self._handle_corrupted_config()
            return LightRAGConfig.get_default_config()

        except Exception as e:
            raise ConfigStorageError(
                f"加载配置文件失败: {str(e)}",
                file_path=str(self.config_file),
                details={"error": str(e)}
            )

    def save_config(self, config: LightRAGConfig) -> None:
        """保存配置文件"""
        try:
            # 创建备份
            self._create_backup()

            # 更新元数据
            config.update_metadata()

            # 序列化配置
            config_data = config.dict()

            # 自定义JSON序列化器处理datetime对象
            def json_serializer(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

            # 写入临时文件
            temp_file = self.config_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False, default=json_serializer)

            # 设置临时文件权限
            temp_file.chmod(0o600)

            # 原子性地替换原文件
            temp_file.replace(self.config_file)

            logger.info(f"配置已保存: {self.config_file}")

        except Exception as e:
            # 清理临时文件
            if temp_file.exists():
                temp_file.unlink()

            raise ConfigStorageError(
                f"保存配置文件失败: {str(e)}",
                file_path=str(self.config_file),
                details={"error": str(e)}
            )

    def _handle_corrupted_config(self):
        """处理损坏的配置文件"""
        try:
            if self.config_file.exists():
                # 创建损坏文件的备份
                corrupted_backup = self.backup_dir / f"config_corrupted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                shutil.copy2(self.config_file, corrupted_backup)
                corrupted_backup.chmod(0o600)
                logger.warning(f"损坏的配置文件已备份: {corrupted_backup}")

                # 删除损坏的文件
                self.config_file.unlink()

        except Exception as e:
            logger.error(f"处理损坏配置文件失败: {str(e)}")

    def reset_config(self, config_type: str = "all") -> LightRAGConfig:
        """重置配置"""
        try:
            # 加载当前配置
            current_config = self.load_config()

            # 获取默认配置
            default_config = LightRAGConfig.get_default_config()

            # 根据类型重置配置
            if config_type == "embedding":
                current_config.embedding = default_config.embedding
            elif config_type == "rerank":
                current_config.rerank = default_config.rerank
            elif config_type == "all":
                current_config = default_config
            else:
                raise ValueError(f"不支持的配置类型: {config_type}")

            # 保存重置后的配置
            self.save_config(current_config)

            logger.info(f"配置已重置: {config_type}")
            return current_config

        except Exception as e:
            raise ConfigStorageError(
                f"重置配置失败: {str(e)}",
                details={"config_type": config_type, "error": str(e)}
            )

    def get_config_info(self) -> Dict[str, Any]:
        """获取配置文件信息"""
        try:
            info = {
                "config_file": str(self.config_file),
                "config_dir": str(self.config_dir),
                "backup_dir": str(self.backup_dir),
                "config_exists": self.config_file.exists(),
                "backup_count": len(list(self.backup_dir.glob("config_*.json"))),
            }

            if self.config_file.exists():
                stat_info = self.config_file.stat()
                info.update({
                    "file_size": stat_info.st_size,
                    "last_modified": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                    "file_permissions": oct(stat_info.st_mode & 0o777),
                })

            return info

        except Exception as e:
            raise ConfigStorageError(
                f"获取配置信息失败: {str(e)}",
                details={"error": str(e)}
            )

    def delete_config(self) -> None:
        """删除配置文件"""
        try:
            if self.config_file.exists():
                # 创建最终备份
                final_backup = self.backup_dir / f"config_deleted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                shutil.copy2(self.config_file, final_backup)
                final_backup.chmod(0o600)

                # 删除配置文件
                self.config_file.unlink()

                logger.info(f"配置文件已删除并备份: {final_backup}")

        except Exception as e:
            raise ConfigStorageError(
                f"删除配置文件失败: {str(e)}",
                file_path=str(self.config_file),
                details={"error": str(e)}
            )

    def restore_from_backup(self, backup_file: Optional[str] = None) -> LightRAGConfig:
        """从备份恢复配置"""
        try:
            if backup_file:
                backup_path = Path(backup_file)
                if not backup_path.exists() or not backup_path.is_file():
                    raise ConfigNotFoundError(f"备份文件不存在: {backup_file}")
            else:
                # 使用最新的备份
                backup_files = sorted(self.backup_dir.glob("config_*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
                if not backup_files:
                    raise ConfigNotFoundError("没有找到可用的备份文件")

                backup_path = backup_files[0]

            # 从备份加载配置
            with open(backup_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            config = LightRAGConfig.parse_obj(config_data)

            # 保存恢复的配置
            self.save_config(config)

            logger.info(f"配置已从备份恢复: {backup_path}")
            return config

        except Exception as e:
            raise ConfigStorageError(
                f"从备份恢复配置失败: {str(e)}",
                details={"backup_file": backup_file, "error": str(e)}
            )

    def list_backups(self) -> list:
        """列出所有备份文件"""
        try:
            backup_files = []
            for backup_path in sorted(self.backup_dir.glob("config_*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
                stat_info = backup_path.stat()
                backup_files.append({
                    "filename": backup_path.name,
                    "path": str(backup_path),
                    "size": stat_info.st_size,
                    "created": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                    "permissions": oct(stat_info.st_mode & 0o777),
                })

            return backup_files

        except Exception as e:
            raise ConfigStorageError(
                f"列出备份文件失败: {str(e)}",
                details={"error": str(e)}
            )