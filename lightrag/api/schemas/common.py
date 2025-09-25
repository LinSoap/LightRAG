from typing import Optional, TypeVar, Generic, List, Union
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


class TestResponseData(BaseModel):
    """测试接口返回的数据结构。

    `result` 字段可以是 LLM 返回的字符串，也可以是 Embedding 返回的向量列表（List[List[float]])。
    """

    result: Union[str, List[List[float]]]
