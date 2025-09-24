"""
Configuration API schemas for LightRAG.
统一配置相关的API模式定义。
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


class ConfigType(str, Enum):
    """Configuration type enumeration."""
    EMBEDDING = "embedding"
    RERANK = "rerank"
    ALL = "all"


class EmbeddingBinding(str, Enum):
    """Supported embedding service providers."""
    OLLAMA = "ollama"
    OPENAI = "openai"
    JINA = "jina"
    AZURE_OPENAI = "azure_openai"
    AWS_BEDROCK = "aws_bedrock"
    SILICONFLOW = "siliconflow"
    HUGGINGFACE = "huggingface"
    ZHIPU = "zhipu"
    ANTHROPIC = "anthropic"
    LOLLMS = "lollms"


class RerankBinding(str, Enum):
    """Supported rerank service providers."""
    NULL = "null"
    COHERE = "cohere"
    JINA = "jina"
    ALIYUN = "aliyun"


# 核心配置类
class LightRAGConfig(BaseModel):
    """LightRAG主配置类"""

    class Meta(BaseModel):
        """配置元数据"""
        version: str = "1.0.0"
        created_at: datetime = Field(default_factory=datetime.now)
        updated_at: datetime = Field(default_factory=datetime.now)

    class Embedding(BaseModel):
        """Embedding配置"""
        binding: EmbeddingBinding = Field(default=EmbeddingBinding.OPENAI)
        model: str = Field(default="text-embedding-3-small")
        dim: int = Field(default=1536, ge=1, le=100000)
        host: Optional[str] = Field(default=None)
        api_key: Optional[str] = Field(default=None)

    class Rerank(BaseModel):
        """Rerank配置"""
        binding: RerankBinding = Field(default=RerankBinding.NULL)
        model: Optional[str] = Field(default=None)
        host: Optional[str] = Field(default=None)
        api_key: Optional[str] = Field(default=None)
        by_default: bool = Field(default=False)
        min_score: float = Field(default=0.0, ge=0.0, le=1.0)

    meta: Meta = Field(default_factory=Meta)
    embedding: Embedding = Field(default_factory=Embedding)
    rerank: Rerank = Field(default_factory=Rerank)

    def update_metadata(self):
        """更新配置元数据"""
        self.meta.updated_at = datetime.now()

    def mask_api_keys(self) -> 'LightRAGConfig':
        """返回API密钥被遮蔽的配置副本"""
        config_dict = self.dict()

        # 遮蔽embedding API密钥
        if config_dict.get('embedding', {}).get('api_key'):
            config_dict['embedding']['api_key'] = '***masked***'

        # 遮蔽rerank API密钥
        if config_dict.get('rerank', {}).get('api_key'):
            config_dict['rerank']['api_key'] = '***masked***'

        return LightRAGConfig(**config_dict)

    def mask_api_key(self) -> 'LightRAGConfig':
        """返回API密钥被遮蔽的配置副本（保持向后兼容）"""
        return self.mask_api_keys()

    @classmethod
    def get_default_config(cls) -> "LightRAGConfig":
        """获取默认配置"""
        return cls()


# 配置组件类（用于类型提示）
class EmbeddingConfig(BaseModel):
    """Embedding配置组件"""
    binding: EmbeddingBinding = Field(default=EmbeddingBinding.OPENAI)
    model: str = Field(default="text-embedding-3-small")
    dim: int = Field(default=1536, ge=1, le=100000)
    host: Optional[str] = Field(default=None)
    api_key: Optional[str] = Field(default=None)


class RerankConfig(BaseModel):
    """Rerank配置组件"""
    binding: RerankBinding = Field(default=RerankBinding.NULL)
    model: Optional[str] = Field(default=None)
    host: Optional[str] = Field(default=None)
    api_key: Optional[str] = Field(default=None)
    by_default: bool = Field(default=False)
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)

    def mask_api_key(self) -> "RerankConfig":
        """返回API密钥被遮蔽的配置副本"""
        config_dict = self.dict()
        if config_dict.get("api_key"):
            config_dict["api_key"] = "***masked***"
        return RerankConfig(**config_dict)


class ConfigMetadata(BaseModel):
    """配置元数据"""
    version: str = "1.0.0"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# 配置更新请求
class EmbeddingConfigUpdate(BaseModel):
    """Embedding configuration update request."""
    binding: EmbeddingBinding = Field(..., description="Embedding服务提供商")
    model: str = Field(..., min_length=1, description="模型名称")
    dim: int = Field(..., ge=1, le=100000, description="向量维度")
    host: Optional[str] = Field(None, description="服务地址")
    api_key: Optional[str] = Field(None, description="API密钥")

    @validator('host')
    def validate_host(cls, v):
        """验证服务地址"""
        if v is None:
            return v
        if not v.startswith(('http://', 'https://')):
            raise ValueError('服务地址必须以 http:// 或 https:// 开头')
        return v


class RerankConfigUpdate(BaseModel):
    """Rerank configuration update request."""
    binding: RerankBinding = Field(..., description="Rerank服务提供商")
    model: Optional[str] = Field(None, description="模型名称")
    host: Optional[str] = Field(None, description="服务地址")
    api_key: Optional[str] = Field(None, description="API密钥")
    by_default: bool = Field(False, description="是否默认启用")
    min_score: float = Field(0.0, ge=0.0, le=1.0, description="最小分数阈值")

    @validator('host')
    def validate_host(cls, v):
        """验证服务地址"""
        if v is None:
            return v
        if not v.startswith(('http://', 'https://')):
            raise ValueError('服务地址必须以 http:// 或 https:// 开头')
        return v


# 配置测试相关
class ConfigTestRequest(BaseModel):
    """配置测试请求"""
    type: str = Field(..., description="测试类型: embedding 或 rerank")
    text: str = Field(..., description="测试文本")
    documents: Optional[list[str]] = Field(default=None, description="测试文档列表（仅rerank测试需要）")

    @validator('type')
    def validate_type(cls, v):
        """验证测试类型"""
        if v not in ['embedding', 'rerank']:
            raise ValueError("测试类型必须是 'embedding' 或 'rerank'")
        return v

    @validator('text')
    def validate_text(cls, v):
        """验证测试文本"""
        if not v or not v.strip():
            raise ValueError("测试文本不能为空")
        return v.strip()


class ConfigTestResponse(BaseModel):
    """配置测试响应"""
    status: str = Field(..., description="测试状态: success 或 error")
    message: str = Field(..., description="测试结果消息")
    data: Optional[Dict[str, Any]] = Field(default=None, description="测试数据")
    response_time: float = Field(..., description="响应时间（秒）")


class ConfigUpdateResponse(BaseModel):
    """配置更新响应"""
    status: str = Field(..., description="更新状态: success 或 error")
    message: str = Field(..., description="更新结果消息")
    data: Optional[Dict[str, Any]] = Field(default=None, description="更新后的配置数据")


# 其他配置API响应类
class ConfigResetRequest(BaseModel):
    """Configuration reset request."""
    config_type: ConfigType = Field(..., description="要重置的配置类型")

    @validator('config_type')
    def validate_config_type(cls, v):
        """Validate configuration type."""
        allowed_types = [ConfigType.EMBEDDING, ConfigType.RERANK, ConfigType.ALL]
        if v not in allowed_types:
            raise ValueError(f'Config type must be one of: {", ".join(allowed_types)}')
        return v


class ConfigInfoResponse(BaseModel):
    """Configuration information response."""
    config_exists: bool = Field(..., description="配置文件是否存在")
    config_file: str = Field(..., description="配置文件路径")
    file_size: Optional[int] = Field(None, description="文件大小（字节）")
    last_modified: Optional[str] = Field(None, description="最后修改时间")
    backup_count: int = Field(..., description="备份文件数量")
    permissions: str = Field(..., description="文件权限")


class ConfigBackupResponse(BaseModel):
    """Configuration backup response."""
    backup_created: bool = Field(..., description="备份是否创建成功")
    backup_file: str = Field(..., description="备份文件路径")
    backup_size: Optional[int] = Field(None, description="备份文件大小")
    timestamp: str = Field(..., description="备份时间戳")


class ConfigMigrationResponse(BaseModel):
    """Configuration migration response."""
    success: bool = Field(..., description="迁移是否成功")
    message: str = Field(..., description="迁移结果消息")
    migrated_keys: int = Field(..., description="迁移的配置项数量")
    warnings: List[str] = Field(default_factory=list, description="警告信息")


class ConfigValidationResponse(BaseModel):
    """Configuration validation response."""
    valid: bool = Field(..., description="配置是否有效")
    message: str = Field(..., description="验证结果消息")
    errors: List[str] = Field(default_factory=list, description="错误信息")
    warnings: List[str] = Field(default_factory=list, description="警告信息")