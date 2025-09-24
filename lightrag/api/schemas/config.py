"""
Configuration API schemas for LightRAG.
API接口相关的数据结构定义。
"""

from typing import Optional
from pydantic import BaseModel, Field


class LLMConfigPayload(BaseModel):
    """LLM配置更新请求"""

    LLM_BINDING: Optional[str] = Field(None, description="LLM服务提供商")
    LLM_MODEL: Optional[str] = Field(None, description="LLM模型名称")
    LLM_BINDING_HOST: Optional[str] = Field(None, description="LLM服务地址")
    LLM_BINDING_API_KEY: Optional[str] = Field(None, description="LLM API密钥")


class EmbeddingConfigPayload(BaseModel):
    """Embedding配置更新请求"""

    EMBEDDING_BINDING: Optional[str] = Field(None, description="Embedding服务提供商")
    EMBEDDING_MODEL: Optional[str] = Field(None, description="Embedding模型名称")
    EMBEDDING_BINDING_HOST: Optional[str] = Field(None, description="Embedding服务地址")
    EMBEDDING_BINDING_API_KEY: Optional[str] = Field(
        None, description="Embedding API密钥"
    )
    EMBEDDING_DIM: Optional[int] = Field(None, description="Embedding向量维度")


class RerankConfigPayload(BaseModel):
    """Rerank配置更新请求"""

    COSINE_BETTER_THAN_THRESHOLD: Optional[float] = Field(
        None, description="余弦相似度更好阈值"
    )
    COSINE_THRESHOLD: Optional[float] = Field(None, description="余弦相似度阈值")
    MAX_BATCH_SIZE: Optional[int] = Field(None, description="最大批处理大小")


class TestPayload(BaseModel):
    """配置测试请求"""

    target: str = Field(default="llm", description="测试目标: llm 或 embedding")
    message: Optional[str] = Field(default="你好", description="测试消息")
