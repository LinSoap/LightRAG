"""
路径配置管理器 - 处理配置文件和环境变量
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, Union
import logging

# 尝试导入yaml，如果不可用则使用JSON
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

logger = logging.getLogger(__name__)


class PathConfig:
    """路径配置管理器"""

    def __init__(self, config_file: Optional[Union[str, Path]] = None):
        """初始化配置管理器"""
        self.config_file = config_file or self._get_default_config_file()
        self.config_data: Dict[str, Any] = {}
        self._load_config()

    def _get_default_config_file(self) -> Path:
        """获取默认配置文件路径"""
        # 优先使用当前目录的配置文件
        current_dir = Path.cwd()
        config_files = [
            current_dir / "lightrag_config.yaml",
            current_dir / "lightrag_config.json",
            current_dir / "config.yaml",
            current_dir / "config.json"
        ]

        for config_file in config_files:
            if config_file.exists():
                return config_file

        # 如果没有配置文件，返回默认位置
        return current_dir / "lightrag_config.yaml"

    def _load_config(self):
        """加载配置文件"""
        if not self.config_file.exists():
            self.config_data = self._get_default_config()
            return

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                if self.config_file.suffix.lower() == '.json':
                    self.config_data = json.load(f)
                elif HAS_YAML:
                    self.config_data = yaml.safe_load(f) or {}
                else:
                    # 如果没有yaml支持，只支持JSON格式
                    if self.config_file.suffix.lower() in ['.yaml', '.yml']:
                        logger.warning("YAML format detected but PyYAML not installed. Please install PyYAML or use JSON format.")
                        self.config_data = self._get_default_config()
                    else:
                        # 尝试作为JSON解析
                        try:
                            self.config_data = json.load(f)
                        except json.JSONDecodeError:
                            self.config_data = self._get_default_config()

            logger.info(f"Loaded configuration from {self.config_file}")

        except Exception as e:
            logger.error(f"Failed to load configuration from {self.config_file}: {e}")
            self.config_data = self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "storage": {
                "base_dir": None,  # None表示使用默认路径
                "workspace": "default",
                "auto_create": True,
                "auto_migrate": True
            },
            "server": {
                "host": "127.0.0.1",
                "port": 0,  # 0表示自动选择端口
                "auto_reload": False,
                "log_level": "info"
            },
            "system": {
                "max_memory_mb": 1024,
                "max_cpu_percent": 90,
                "health_check_interval": 30
            }
        }

    def save_config(self):
        """保存配置文件"""
        try:
            # 确保配置文件目录存在
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_file, 'w', encoding='utf-8') as f:
                if self.config_file.suffix.lower() == '.json':
                    json.dump(self.config_data, f, indent=2, ensure_ascii=False)
                elif HAS_YAML:
                    yaml.dump(self.config_data, f, default_flow_style=False, allow_unicode=True)
                else:
                    # 如果没有yaml支持，强制使用JSON格式
                    if self.config_file.suffix.lower() in ['.yaml', '.yml']:
                        # 更改为JSON格式
                        json_file = self.config_file.with_suffix('.json')
                        logger.info(f"Converting YAML config to JSON format: {json_file}")
                        json.dump(self.config_data, f, indent=2, ensure_ascii=False)
                    else:
                        json.dump(self.config_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved configuration to {self.config_file}")

        except Exception as e:
            logger.error(f"Failed to save configuration to {self.config_file}: {e}")

    def get_storage_base_dir(self) -> Optional[str]:
        """获取存储基础目录"""
        # 优先级：环境变量 > 配置文件 > 默认值
        env_dir = os.getenv("LIGHTRAG_STORAGE_DIR")
        if env_dir:
            return env_dir

        return self.config_data.get("storage", {}).get("base_dir")

    def get_workspace(self) -> str:
        """获取工作空间名称"""
        env_workspace = os.getenv("LIGHTRAG_WORKSPACE")
        if env_workspace:
            return env_workspace

        return self.config_data.get("storage", {}).get("workspace", "default")

    def should_auto_create(self) -> bool:
        """是否自动创建目录"""
        env_create = os.getenv("LIGHTRAG_AUTO_CREATE")
        if env_create is not None:
            return env_create.lower() in ("true", "1", "yes", "on")

        return self.config_data.get("storage", {}).get("auto_create", True)

    def should_auto_migrate(self) -> bool:
        """是否自动迁移数据"""
        env_migrate = os.getenv("LIGHTRAG_AUTO_MIGRATE")
        if env_migrate is not None:
            return env_migrate.lower() in ("true", "1", "yes", "on")

        return self.config_data.get("storage", {}).get("auto_migrate", True)

    def get_server_config(self) -> Dict[str, Any]:
        """获取服务器配置"""
        server_config = self.config_data.get("server", {})

        # 环境变量覆盖
        env_host = os.getenv("LIGHTRAG_HOST")
        if env_host:
            server_config["host"] = env_host

        env_port = os.getenv("LIGHTRAG_PORT")
        if env_port:
            try:
                server_config["port"] = int(env_port)
            except ValueError:
                logger.warning(f"Invalid LIGHTRAG_PORT value: {env_port}")

        env_reload = os.getenv("LIGHTRAG_AUTO_RELOAD")
        if env_reload is not None:
            server_config["auto_reload"] = env_reload.lower() in ("true", "1", "yes", "on")

        env_log_level = os.getenv("LIGHTRAG_LOG_LEVEL")
        if env_log_level:
            server_config["log_level"] = env_log_level

        return server_config

    def get_system_config(self) -> Dict[str, Any]:
        """获取系统配置"""
        return self.config_data.get("system", {})

    def set_storage_base_dir(self, base_dir: Union[str, Path]):
        """设置存储基础目录"""
        if "storage" not in self.config_data:
            self.config_data["storage"] = {}
        self.config_data["storage"]["base_dir"] = str(base_dir)

    def set_workspace(self, workspace: str):
        """设置工作空间"""
        if "storage" not in self.config_data:
            self.config_data["storage"] = {}
        self.config_data["storage"]["workspace"] = workspace

    def set_server_config(self, config: Dict[str, Any]):
        """设置服务器配置"""
        self.config_data["server"] = config

    def set_system_config(self, config: Dict[str, Any]):
        """设置系统配置"""
        self.config_data["system"] = config


# 全局配置实例
_global_config: Optional[PathConfig] = None


def get_global_config() -> PathConfig:
    """获取全局配置实例"""
    global _global_config
    if _global_config is None:
        _global_config = PathConfig()
    return _global_config


def reset_global_config():
    """重置全局配置实例"""
    global _global_config
    _global_config = None