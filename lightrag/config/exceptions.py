"""
Custom exceptions for LightRAG configuration management.
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException


class ConfigError(Exception):
    """配置管理基础异常"""
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code or "CONFIG_ERROR"
        self.details = details or {}
        super().__init__(self.message)


class ConfigValidationError(ConfigError):
    """配置验证错误"""
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CONFIG_VALIDATION_ERROR",
            details={**(details or {}), "field": field} if field else details
        )
        self.field = field


class ConfigStorageError(ConfigError):
    """配置存储错误"""
    def __init__(self, message: str, file_path: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CONFIG_STORAGE_ERROR",
            details={**(details or {}), "file_path": file_path} if file_path else details
        )
        self.file_path = file_path




class ConfigTestError(ConfigError):
    """配置测试错误"""
    def __init__(self, message: str, test_type: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CONFIG_TEST_ERROR",
            details={**(details or {}), "test_type": test_type} if test_type else details
        )
        self.test_type = test_type


class ConfigNotFoundError(ConfigError):
    """配置文件未找到错误"""
    def __init__(self, message: str, file_path: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="CONFIG_NOT_FOUND_ERROR",
            details={"file_path": file_path} if file_path else None
        )
        self.file_path = file_path


class ConfigPermissionError(ConfigError):
    """配置文件权限错误"""
    def __init__(self, message: str, file_path: Optional[str] = None, required_permissions: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="CONFIG_PERMISSION_ERROR",
            details={
                "file_path": file_path,
                "required_permissions": required_permissions
            } if file_path or required_permissions else None
        )
        self.file_path = file_path
        self.required_permissions = required_permissions


class ConfigHTTPError(HTTPException):
    """配置管理HTTP异常"""
    def __init__(self, status_code: int, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.error_code = error_code
        self.details = details or {}

        # 构造响应体
        response_data = {
            "status": "error",
            "message": message,
            "error_code": error_code or "HTTP_ERROR",
            "details": self.details
        }

        super().__init__(status_code=status_code, detail=response_data)


def config_error_to_http_error(config_error: ConfigError) -> ConfigHTTPError:
    """将配置错误转换为HTTP错误"""

    error_mapping = {
        "CONFIG_VALIDATION_ERROR": 400,
        "CONFIG_STORAGE_ERROR": 500,
        "CONFIG_TEST_ERROR": 400,
        "CONFIG_NOT_FOUND_ERROR": 404,
        "CONFIG_PERMISSION_ERROR": 403,
        "CONFIG_ERROR": 500
    }

    status_code = error_mapping.get(config_error.error_code, 500)

    return ConfigHTTPError(
        status_code=status_code,
        message=config_error.message,
        error_code=config_error.error_code,
        details=config_error.details
    )