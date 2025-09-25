from typing import Any, Dict, Optional, TypeVar, Generic, List, Union
from pydantic import BaseModel

T = TypeVar("T")


class GenericResponse(BaseModel, Generic[T]):
    """通用响应结构，支持泛型data字段。"""

    status: str
    message: Optional[str] = None
    data: Optional[T] = None


class TestResponseData(BaseModel):
    """测试接口返回的数据结构。

    `result` 字段可以是：
    - LLM 返回的字符串
    - Embedding 返回的向量列表（List[List[float]]）
    - Rerank 返回的重排序结果（List[Dict[str, Any]]）
    """

    result: Union[str, List[List[float]], List[Dict[str, Any]]]
