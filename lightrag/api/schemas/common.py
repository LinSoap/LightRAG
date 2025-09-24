from typing import Optional, TypeVar, Generic
from pydantic import BaseModel

from lightrag.config_manager import (
    LLMConfig,
    EmbeddingConfig,
    LightRAGConfig,
)


T = TypeVar("T")


class GenericResponse(BaseModel, Generic[T]):
    """通用响应结构，支持泛型data字段。"""

    status: str
    message: Optional[str] = None
    data: Optional[T] = None


class AppConfigData(BaseModel):
    """应用配置数据结构，包含三个子配置。"""

    lightrag_config: LightRAGConfig
    llm_config: LLMConfig
    embedding_config: EmbeddingConfig


class TestResponseData(BaseModel):
    """测试接口返回的数据结构。"""

    result: str