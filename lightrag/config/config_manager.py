"""
Configuration manager for LightRAG model configuration.
简化版本，专注于核心配置管理功能。
"""

import asyncio
import time
from typing import Optional, Dict, Any
from lightrag.api.schemas.config import (
    LightRAGConfig,
    EmbeddingConfig,
    RerankConfig,
    ConfigTestRequest,
    ConfigTestResponse,
    ConfigUpdateResponse,
)
from .storage import ConfigStorage
from .exceptions import (
    ConfigError,
    ConfigValidationError,
    ConfigTestError,
    config_error_to_http_error,
)
from lightrag.utils import logger


class ConfigManager:
    """LightRAG配置管理器 - 简化版本"""

    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_dir: 配置目录路径
        """
        self.storage = ConfigStorage(config_dir)
        self._config: Optional[LightRAGConfig] = None
        self._last_load_time: Optional[float] = None
        self._lock = asyncio.Lock()

    async def initialize(self):
        """初始化配置管理器"""
        try:
            logger.info("正在初始化配置管理器...")
            await self._load_config_async()
            logger.info("配置管理器初始化完成")
        except Exception as e:
            logger.error(f"配置管理器初始化失败: {str(e)}")
            raise ConfigError(f"配置管理器初始化失败: {str(e)}")

    async def _load_config_async(self) -> LightRAGConfig:
        """异步加载配置"""
        async with self._lock:
            try:
                # 如果配置已缓存且最近加载过，直接返回
                if (
                    self._config is not None
                    and self._last_load_time is not None
                    and time.time() - self._last_load_time < 60
                ):  # 60秒缓存
                    return self._config

                # 从存储加载配置
                self._config = self.storage.load_config()
                self._last_load_time = time.time()

                logger.debug("配置已加载到缓存")
                return self._config

            except Exception as e:
                logger.error(f"加载配置失败: {str(e)}")
                raise ConfigError(f"加载配置失败: {str(e)}")

    def _load_config_sync(self) -> LightRAGConfig:
        """同步加载配置（用于初始化等场景）"""
        try:
            self._config = self.storage.load_config()
            self._last_load_time = time.time()
            return self._config
        except Exception as e:
            logger.error(f"同步加载配置失败: {str(e)}")
            raise ConfigError(f"同步加载配置失败: {str(e)}")

    async def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        try:
            config = await self._load_config_async()

            return {"status": "success", "data": config.model_dump()}

        except Exception as e:
            logger.error(f"获取配置失败: {str(e)}")
            raise config_error_to_http_error(ConfigError(f"获取配置失败: {str(e)}"))

    async def update_embedding_config(
        self, embedding_config: Dict[str, Any]
    ) -> ConfigUpdateResponse:
        """更新Embedding配置"""
        try:
            # 验证输入数据
            new_config = EmbeddingConfig.model_validate(embedding_config)

            # 加载当前配置
            current_config = await self._load_config_async()

            # 更新配置
            current_config.embedding = new_config
            current_config.update_metadata()

            # 保存配置
            self.storage.save_config(current_config)

            # 更新缓存
            self._config = current_config

            logger.info("Embedding配置已更新")

            return ConfigUpdateResponse(
                status="success",
                message="Embedding configuration updated successfully",
                data=new_config.model_dump(),
            )

        except Exception as e:
            logger.error(f"更新Embedding配置失败: {str(e)}")
            if isinstance(e, ConfigError):
                raise config_error_to_http_error(e)
            else:
                raise config_error_to_http_error(
                    ConfigError(f"更新Embedding配置失败: {str(e)}")
                )

    async def update_rerank_config(
        self, rerank_config: Dict[str, Any]
    ) -> ConfigUpdateResponse:
        """更新Rerank配置"""
        try:
            # 验证输入数据
            new_config = RerankConfig.model_validate(rerank_config)

            # 加载当前配置
            current_config = await self._load_config_async()

            # 更新配置
            current_config.rerank = new_config
            current_config.update_metadata()

            # 保存配置
            self.storage.save_config(current_config)

            # 更新缓存
            self._config = current_config

            logger.info("Rerank配置已更新")

            return ConfigUpdateResponse(
                status="success",
                message="Rerank configuration updated successfully",
                data=new_config.dict(),
            )

        except Exception as e:
            logger.error(f"更新Rerank配置失败: {str(e)}")
            if isinstance(e, ConfigError):
                raise config_error_to_http_error(e)
            else:
                raise config_error_to_http_error(
                    ConfigError(f"更新Rerank配置失败: {str(e)}")
                )

    async def test_config(self, test_request: ConfigTestRequest) -> ConfigTestResponse:
        """测试配置 - 委托给LLM模块"""
        start_time = time.time()

        try:
            if test_request.type == "embedding":
                return await self._test_embedding_config(test_request)
            elif test_request.type == "rerank":
                return await self._test_rerank_config(test_request)
            else:
                raise ConfigValidationError(f"不支持的测试类型: {test_request.type}")

        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"配置测试失败: {str(e)}")

            if isinstance(e, ConfigTestError):
                return ConfigTestResponse(
                    status="error",
                    message=str(e),
                    data=e.details if hasattr(e, "details") else None,
                    response_time=response_time,
                )
            else:
                return ConfigTestResponse(
                    status="error",
                    message=f"Configuration test failed: {str(e)}",
                    response_time=response_time,
                )

    async def _test_embedding_config(
        self, test_request: ConfigTestRequest
    ) -> ConfigTestResponse:
        """测试Embedding配置 - 直接使用原始LLM模块"""
        start_time = time.time()

        try:
            # 加载当前配置
            config = await self._load_config_async()
            binding = config.embedding.binding.value

            # 根据binding直接调用对应的LLM模块
            if binding == "openai":
                result = await self._test_openai_embedding(
                    config.embedding, test_request.text
                )
            elif binding == "ollama":
                result = await self._test_ollama_embedding(
                    config.embedding, test_request.text
                )
            elif binding == "jina":
                result = await self._test_jina_embedding(
                    config.embedding, test_request.text
                )
            elif binding == "siliconflow":
                result = await self._test_siliconflow_embedding(
                    config.embedding, test_request.text
                )
            elif binding == "azure_openai":
                result = await self._test_azure_openai_embedding(
                    config.embedding, test_request.text
                )
            elif binding == "zhipu":
                result = await self._test_zhipu_embedding(
                    config.embedding, test_request.text
                )
            elif binding == "anthropic":
                result = await self._test_anthropic_embedding(
                    config.embedding, test_request.text
                )
            else:
                raise ValueError(f"Unsupported embedding provider: {binding}")

            response_time = time.time() - start_time

            return ConfigTestResponse(
                status="success",
                message="Embedding test completed successfully",
                data={
                    "type": "embedding",
                    "binding": binding,
                    "model": config.embedding.model,
                    "dim": config.embedding.dim,
                    **result,
                },
                response_time=response_time,
            )

        except Exception as e:
            response_time = time.time() - start_time
            logger.error(
                f"Embedding test failed for {binding if 'binding' in locals() else 'unknown'}: {str(e)}"
            )
            return ConfigTestResponse(
                status="error",
                message=f"Embedding test failed: {str(e)}",
                data={
                    "type": "embedding",
                    "binding": binding if "binding" in locals() else "unknown",
                    "model": (
                        config.embedding.model if "config" in locals() else "unknown"
                    ),
                    "dim": 0,
                    "embedding_dim": 0,
                    "embedding_preview": [],
                    "usage": {},
                },
                response_time=response_time,
            )

    async def _test_rerank_config(
        self, test_request: ConfigTestRequest
    ) -> ConfigTestResponse:
        """测试Rerank配置 - 简化版本"""
        start_time = time.time()

        try:
            # 加载当前配置
            config = await self._load_config_async()

            response_time = time.time() - start_time

            return ConfigTestResponse(
                status="success",
                message="Rerank configuration test successful",
                data={
                    "type": "rerank",
                    "binding": config.rerank.binding.value,
                    "model": config.rerank.model,
                    "by_default": config.rerank.by_default,
                    "min_score": config.rerank.min_score,
                    "test_text": (
                        test_request.text[:100] + "..."
                        if len(test_request.text) > 100
                        else test_request.text
                    ),
                    "documents_count": (
                        len(test_request.documents) if test_request.documents else 0
                    ),
                },
                response_time=response_time,
            )

        except Exception as e:
            response_time = time.time() - start_time
            if isinstance(e, ConfigTestError):
                raise
            else:
                raise ConfigTestError(f"Rerank test failed: {str(e)}")

    async def test_configuration(self, config_type: str) -> Dict[str, Any]:
        """测试配置 - 简化版本"""
        try:
            config = await self._load_config_async()

            if config_type == "embedding":
                return {
                    "success": True,
                    "message": "Embedding configuration available",
                    "details": {
                        "binding": config.embedding.binding.value,
                        "model": config.embedding.model,
                        "dim": config.embedding.dim,
                        "host": config.embedding.host,
                    },
                }

            elif config_type == "rerank":
                return {
                    "success": True,
                    "message": "Rerank configuration available",
                    "details": {
                        "binding": config.rerank.binding.value,
                        "model": config.rerank.model,
                        "by_default": config.rerank.by_default,
                        "min_score": config.rerank.min_score,
                    },
                }

            else:
                return {
                    "success": False,
                    "message": f"Invalid config type: {config_type}",
                    "details": {},
                }

        except Exception as e:
            logger.error(f"测试配置失败: {str(e)}")
            if isinstance(e, ConfigError):
                raise config_error_to_http_error(e)
            else:
                raise ConfigTestError(f"Configuration test failed: {str(e)}")

    async def reset_config(self, config_type: str) -> Dict[str, Any]:
        """重置配置"""
        try:
            # 重置配置
            new_config = self.storage.reset_config(config_type)

            # 更新缓存
            self._config = new_config

            logger.info(f"配置已重置: {config_type}")

            return {
                "status": "success",
                "message": f"Configuration reset to defaults successfully",
                "data": new_config.dict(),
            }

        except Exception as e:
            logger.error(f"重置配置失败: {str(e)}")
            raise config_error_to_http_error(ConfigError(f"重置配置失败: {str(e)}"))

    def get_config_info(self) -> Dict[str, Any]:
        """获取配置信息"""
        try:
            return {"status": "success", "data": self.storage.get_config_info()}
        except Exception as e:
            logger.error(f"获取配置信息失败: {str(e)}")
            raise config_error_to_http_error(ConfigError(f"获取配置信息失败: {str(e)}"))

    async def refresh_cache(self):
        """刷新配置缓存"""
        try:
            async with self._lock:
                self._config = None
                self._last_load_time = None
                await self._load_config_async()
                logger.debug("配置缓存已刷新")
        except Exception as e:
            logger.error(f"刷新配置缓存失败: {str(e)}")
            raise ConfigError(f"刷新配置缓存失败: {str(e)}")

    def get_embedding_config_for_rag(self) -> EmbeddingConfig:
        """获取用于RAG的Embedding配置（同步）"""
        try:
            if self._config is None:
                self._load_config_sync()
            return self._config.embedding
        except Exception as e:
            logger.error(f"获取Embedding配置失败: {str(e)}")
            raise ConfigError(f"获取Embedding配置失败: {str(e)}")

    def get_rerank_config_for_rag(self) -> RerankConfig:
        """获取用于RAG的Rerank配置（同步）"""
        try:
            if self._config is None:
                self._load_config_sync()
            return self._config.rerank
        except Exception as e:
            logger.error(f"获取Rerank配置失败: {str(e)}")
            raise ConfigError(f"获取Rerank配置失败: {str(e)}")

    # Embedding测试方法
    async def _test_openai_embedding(self, config, text: str) -> Dict[str, Any]:
        """Test OpenAI embedding configuration"""
        from lightrag.llm.openai import openai_embed
        import time

        start_time = time.time()
        try:
            embeddings = await openai_embed(
                texts=[text],
                model=config.model,
                base_url=config.host,
                api_key=config.api_key,
            )

            return {
                "embedding_dim": len(embeddings[0]),
                "embedding_preview": embeddings[0].tolist()[:5],
                "response_time": time.time() - start_time,
                "usage": {},
                "model_info": config.model,
            }
        except Exception as e:
            raise Exception(f"OpenAI embedding test failed: {str(e)}")

    async def _test_ollama_embedding(self, config, text: str) -> Dict[str, Any]:
        """Test Ollama embedding configuration"""
        from lightrag.llm.ollama import ollama_embed
        import time

        start_time = time.time()
        try:
            embeddings = await ollama_embed(
                texts=[text],
                embed_model=config.model,
                host=config.host,
                api_key=config.api_key,
                timeout=60,
            )

            return {
                "embedding_dim": len(embeddings[0]),
                "embedding_preview": embeddings[0].tolist()[:5],
                "response_time": time.time() - start_time,
                "usage": {},
                "model_info": config.model,
            }
        except Exception as e:
            raise Exception(f"Ollama embedding test failed: {str(e)}")

    async def _test_jina_embedding(self, config, text: str) -> Dict[str, Any]:
        """Test Jina embedding configuration"""
        from lightrag.llm.jina import jina_embed
        import time

        start_time = time.time()
        try:
            embeddings = await jina_embed(
                texts=[text],
                dimensions=config.dim,
                base_url=config.host,
                api_key=config.api_key,
            )

            return {
                "embedding_dim": len(embeddings[0]),
                "embedding_preview": embeddings[0].tolist()[:5],
                "response_time": time.time() - start_time,
                "usage": {},
                "model_info": config.model,
            }
        except Exception as e:
            raise Exception(f"Jina embedding test failed: {str(e)}")

    async def _test_siliconflow_embedding(self, config, text: str) -> Dict[str, Any]:
        """Test SiliconFlow embedding configuration"""
        from lightrag.llm.siliconcloud import siliconcloud_embedding
        import time

        start_time = time.time()
        try:
            embeddings = await siliconcloud_embedding(
                texts=[text],
                model=config.model,
                base_url=config.host,
                api_key=config.api_key,
            )

            return {
                "embedding_dim": len(embeddings[0]),
                "embedding_preview": embeddings[0].tolist()[:5],
                "response_time": time.time() - start_time,
                "usage": {},
                "model_info": config.model,
            }
        except Exception as e:
            raise Exception(f"SiliconFlow embedding test failed: {str(e)}")

    async def _test_azure_openai_embedding(self, config, text: str) -> Dict[str, Any]:
        """Test Azure OpenAI embedding configuration"""
        # Azure OpenAI uses the same interface as OpenAI
        return await self._test_openai_embedding(config, text)

    async def _test_zhipu_embedding(self, config, text: str) -> Dict[str, Any]:
        """Test Zhipu embedding configuration"""
        from lightrag.llm.zhipu import zhipu_embedding
        import time

        start_time = time.time()
        try:
            embeddings = await zhipu_embedding(
                texts=[text], model=config.model, api_key=config.api_key
            )

            return {
                "embedding_dim": len(embeddings[0]),
                "embedding_preview": embeddings[0].tolist()[:5],
                "response_time": time.time() - start_time,
                "usage": {},
                "model_info": config.model,
            }
        except Exception as e:
            raise Exception(f"Zhipu embedding test failed: {str(e)}")

    async def _test_anthropic_embedding(self, config, text: str) -> Dict[str, Any]:
        """Test Anthropic embedding configuration"""
        from lightrag.llm.anthropic import anthropic_embed
        import time

        start_time = time.time()
        try:
            embeddings = await anthropic_embed(
                texts=[text],
                model=config.model,
                base_url=config.host,
                api_key=config.api_key,
            )

            return {
                "embedding_dim": len(embeddings[0]),
                "embedding_preview": embeddings[0].tolist()[:5],
                "response_time": time.time() - start_time,
                "usage": {},
                "model_info": config.model,
            }
        except Exception as e:
            raise Exception(f"Anthropic embedding test failed: {str(e)}")
