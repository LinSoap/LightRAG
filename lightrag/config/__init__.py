"""
LightRAG Configuration Management Module

This module provides a simplified configuration management system for LightRAG,
focused on core configuration persistence and access.
"""

from .config_manager import ConfigManager
from .storage import ConfigStorage
from .exceptions import (
    ConfigError,
    ConfigValidationError,
    ConfigStorageError,
    ConfigTestError,
    ConfigNotFoundError,
    ConfigPermissionError,
    ConfigHTTPError,
    config_error_to_http_error
)

__version__ = "1.0.0"
__author__ = "LightRAG Team"

__all__ = [
    # Core Classes
    "ConfigManager",
    "ConfigStorage",

    # Exceptions
    "ConfigError",
    "ConfigValidationError",
    "ConfigStorageError",
    "ConfigTestError",
    "ConfigNotFoundError",
    "ConfigPermissionError",
    "ConfigHTTPError",
    "config_error_to_http_error",
]
