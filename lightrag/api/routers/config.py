"""
Configuration management API routes for LightRAG.
"""

import traceback
from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, Optional
from lightrag.config import ConfigManager
from lightrag.api.schemas.config import (
    ConfigTestRequest,
    ConfigTestResponse,
    ConfigUpdateResponse,
    EmbeddingConfigUpdate,
    RerankConfigUpdate,
)
from lightrag.config.exceptions import ConfigError, config_error_to_http_error
from lightrag.utils import logger

router = APIRouter(prefix="/api/config", tags=["configuration"])

# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """获取配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


async def initialize_config_manager():
    """初始化配置管理器"""
    try:
        config_manager = get_config_manager()
        await config_manager.initialize()
        logger.info("配置管理器初始化成功")
    except Exception as e:
        logger.error(f"配置管理器初始化失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"配置管理器初始化失败: {str(e)}")


@router.get("/models", response_model=Dict[str, Any])
async def get_models_config():
    """
    获取当前模型配置

    Returns:
        Dict[str, Any]: 当前embedding和rerank配置
    """
    try:
        config_manager = get_config_manager()
        return await config_manager.get_config()
    except Exception as e:
        logger.error(f"获取配置失败: {str(e)}")
        logger.error(traceback.format_exc())
        if isinstance(e, ConfigError):
            raise config_error_to_http_error(e)
        else:
            raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.put("/embedding", response_model=ConfigUpdateResponse)
async def update_embedding_config(
    config: EmbeddingConfigUpdate = Body(
        ...,
        description="Embedding配置",
        examples={
            "ollama_example": {
                "summary": "Ollama 本地部署示例",
                "description": "使用本地 Ollama 部署的 BGE-M3 模型",
                "value": {
                    "binding": "ollama",
                    "model": "bge-m3:latest",
                    "dim": 1024,
                    "host": "http://localhost:11434",
                    "api_key": None,
                },
            },
            "openai_example": {
                "summary": "OpenAI 云服务示例",
                "description": "使用 OpenAI 的 text-embedding-3-small 模型",
                "value": {
                    "binding": "openai",
                    "model": "text-embedding-3-small",
                    "dim": 1536,
                    "host": "https://api.openai.com",
                    "api_key": "sk-proj-xxxxxxxxxxxxxxxxxxxxxxxx",
                },
            },
            "jina_example": {
                "summary": "Jina AI 示例",
                "description": "使用 Jina AI 的嵌入模型",
                "value": {
                    "binding": "jina",
                    "model": "jina-embeddings-v2-base-en",
                    "dim": 768,
                    "host": "https://api.jina.ai",
                    "api_key": "jina_xxxxxxxxxxxxxxxxxxxxxxxxxx",
                },
            },
            "siliconflow_example": {
                "summary": "SiliconFlow 示例",
                "description": "使用 SiliconFlow 的嵌入模型",
                "value": {
                    "binding": "siliconflow",
                    "model": "Qwen/Qwen3-Embedding-0.6B",
                    "dim": 1024,
                    "host": "https://api.siliconflow.cn/v1",
                    "api_key": "sk-xxxxxxxxxxxxxxxxxxxxxxxx",
                },
            },
            "zhipu_example": {
                "summary": "智谱AI 示例",
                "description": "使用智谱AI的embedding模型",
                "value": {
                    "binding": "zhipu",
                    "model": "embedding-3",
                    "dim": 1024,
                    "host": "https://open.bigmodel.cn/api/paas/v4",
                    "api_key": "your-zhipuai-api-key",
                },
            },
            "huggingface_example": {
                "summary": "HuggingFace 示例",
                "description": "使用本地HuggingFace模型",
                "value": {
                    "binding": "huggingface",
                    "model": "BAAI/bge-small-zh-v1.5",
                    "dim": 512,
                    "host": None,
                    "api_key": None,
                },
            },
            "anthropic_example": {
                "summary": "Anthropic 示例",
                "description": "使用Anthropic (Voyage AI) 的嵌入模型",
                "value": {
                    "binding": "anthropic",
                    "model": "voyage-3",
                    "dim": 1024,
                    "host": "https://api.voyageai.com/v1",
                    "api_key": "your-voyage-api-key",
                },
            },
        },
    )
):
    """
    更新Embedding模型配置

    支持的 Embedding 服务提供商：
    - **ollama**: 本地部署，无需 API key
    - **openai**: OpenAI 官方服务，需要 API key
    - **jina**: Jina AI 服务，需要 API key
    - **azure_openai**: Azure OpenAI 服务，需要 API key
    - **siliconflow**: SiliconFlow 服务，需要 API key
    - **zhipu**: 智谱AI服务，需要 API key
    - **huggingface**: 本地HuggingFace模型，无需 API key
    - **anthropic**: Anthropic (Voyage AI) 服务，需要 API key

    **示例配置**:
    ```json
    {
      "binding": "ollama",
      "model": "bge-m3:latest",
      "dim": 1024,
      "host": "http://localhost:11434",
      "api_key": null
    }
    ```

    Args:
        config: Embedding配置数据

    Returns:
        ConfigUpdateResponse: 更新结果
    """
    try:
        config_manager = get_config_manager()
        return await config_manager.update_embedding_config(config.dict())
    except Exception as e:
        logger.error(f"更新Embedding配置失败: {str(e)}")
        logger.error(traceback.format_exc())
        if isinstance(e, ConfigError):
            raise config_error_to_http_error(e)
        else:
            raise HTTPException(
                status_code=500, detail=f"更新Embedding配置失败: {str(e)}"
            )


@router.put("/rerank", response_model=ConfigUpdateResponse)
async def update_rerank_config(
    config: RerankConfigUpdate = Body(
        ...,
        description="Rerank配置",
        examples={
            "null_example": {
                "summary": "禁用 Rerank 示例",
                "description": "不使用 rerank 功能",
                "value": {
                    "binding": "null",
                    "model": None,
                    "host": None,
                    "api_key": None,
                    "by_default": False,
                    "min_score": 0.0,
                },
            },
            "cohere_example": {
                "summary": "Cohere Rerank 示例",
                "description": "使用 Cohere 的 rerank 模型",
                "value": {
                    "binding": "cohere",
                    "model": "rerank-english-v3.5",
                    "host": "https://api.cohere.com",
                    "api_key": "xxxxxxxxxxxxxxxxxxxxxxxx",
                    "by_default": True,
                    "min_score": 0.5,
                },
            },
            "jina_example": {
                "summary": "Jina Rerank 示例",
                "description": "使用 Jina AI 的 rerank 模型",
                "value": {
                    "binding": "jina",
                    "model": "jina-reranker-v2-base-multilingual",
                    "host": "https://api.jina.ai",
                    "api_key": "jina_xxxxxxxxxxxxxxxxxxxxxxxxxx",
                    "by_default": True,
                    "min_score": 0.7,
                },
            },
        },
    )
):
    """
    更新Rerank模型配置

    支持的 Rerank 服务提供商：
    - **null**: 禁用 rerank 功能
    - **cohere**: Cohere Rerank 服务，需要 API key
    - **jina**: Jina AI Rerank 服务，需要 API key
    - **aliyun**: 阿里云 Rerank 服务，需要 API key

    **示例配置**:
    ```json
    {
      "binding": "cohere",
      "model": "rerank-english-v3.5",
      "host": "https://api.cohere.com",
      "api_key": "your-cohere-api-key",
      "by_default": true,
      "min_score": 0.5
    }
    ```

    Args:
        config: Rerank配置数据

    Returns:
        ConfigUpdateResponse: 更新结果
    """
    try:
        config_manager = get_config_manager()
        return await config_manager.update_rerank_config(config.dict())
    except Exception as e:
        logger.error(f"更新Rerank配置失败: {str(e)}")
        logger.error(traceback.format_exc())
        if isinstance(e, ConfigError):
            raise config_error_to_http_error(e)
        else:
            raise HTTPException(status_code=500, detail=f"更新Rerank配置失败: {str(e)}")


@router.post("/test", response_model=ConfigTestResponse)
async def test_config(
    test_request: ConfigTestRequest = Body(
        ...,
        description="配置测试请求",
        examples={
            "embedding_test_example": {
                "summary": "Embedding 配置测试示例",
                "description": "测试当前 embedding 配置是否正常工作",
                "value": {
                    "type": "embedding",
                    "text": "这是一个测试文本，用于验证 embedding 模型是否正常工作。",
                    "documents": None,
                },
            },
            "rerank_test_example": {
                "summary": "Rerank 配置测试示例",
                "description": "测试当前 rerank 配置是否正常工作",
                "value": {
                    "type": "rerank",
                    "text": "机器学习是人工智能的一个重要分支",
                    "documents": [
                        "深度学习是机器学习的一个子领域",
                        "自然语言处理专注于计算机与人类语言的交互",
                        "计算机视觉使机器能够理解和解释视觉信息",
                        "强化学习通过奖励机制训练智能体",
                        "数据挖掘帮助从大量数据中发现有价值的信息",
                    ],
                },
            },
            "embedding_multilingual_example": {
                "summary": "多语言 Embedding 测试",
                "description": "测试 embedding 模型的多语言处理能力",
                "value": {
                    "type": "embedding",
                    "text": "Machine learning is a subset of artificial intelligence. 机器学习是人工智能的一个重要分支。",
                    "documents": None,
                },
            },
            "rerank_long_documents_example": {
                "summary": "长文档 Rerank 测试",
                "description": "测试 rerank 模型处理长文档的能力",
                "value": {
                    "type": "rerank",
                    "text": "什么是神经网络？",
                    "documents": [
                        "神经网络是一种模仿生物神经系统的计算模型。它由大量相互连接的处理单元（神经元）组成，每个神经元接收输入信号，经过加权求和和非线性激活函数处理后产生输出。神经网络通过训练数据学习权重参数，能够自动发现数据中的模式和特征。",
                        "支持向量机（SVM）是一种监督学习算法，主要用于分类和回归问题。SVM的核心思想是找到一个最优的超平面来分隔不同类别的数据点，使得不同类别之间的间隔最大化。SVM在处理高维数据和小样本学习问题上表现出色。",
                        "决策树是一种基于树结构的监督学习算法。它通过一系列的判断规则将数据集划分成不同的子集，每个内部节点代表一个特征测试，每个分支代表测试结果，每个叶节点代表一个分类或回归结果。决策树易于理解和解释，但容易过拟合。",
                        "随机森林是一种集成学习方法，它构建多个决策树并结合它们的预测结果。每棵决策树在训练时使用了不同的数据子集和特征子集，这增加了模型的多样性并减少了过拟合的风险。随机森林通常比单个决策树具有更好的泛化性能。",
                        "逻辑回归是一种广泛用于二分类问题的统计方法。尽管名字中包含'回归'，但它实际上是一种分类算法。逻辑回归使用 sigmoid 函数将线性回归的输出映射到 (0,1) 区间，表示样本属于正类的概率。",
                    ],
                },
            },
        },
    )
):
    """
    测试模型配置

    此接口用于测试当前的 embedding 或 rerank 配置是否正常工作。通过发送测试文本和相关文档，
    可以验证模型连接、API密钥、网络连接等是否正常。

    **Embedding 测试**：
    - 验证 embedding 模型是否能正常生成向量
    - 测试模型连接性和 API 密钥有效性
    - 返回生成的向量维度和响应时间

    **Rerank 测试**：
    - 验证 rerank 模型是否能正常对文档进行重排序
    - 测试模型对查询和文档的相关性判断
    - 返回重排序后的文档列表和相关性分数

    **使用场景**：
    - 配置新的 embedding 或 rerank 模型后进行验证
    - 更新 API 密钥后测试连接性
    - 网络环境变化后验证服务可用性
    - 性能监控和故障排查

    Args:
        test_request: 测试请求数据，包含测试类型、文本和可选文档列表

    Returns:
        ConfigTestResponse: 测试结果，包含状态、消息、测试数据和响应时间

    **请求示例**：
    ```json
    // Embedding 测试
    {
      "type": "embedding",
      "text": "这是一个测试文本",
      "documents": null
    }

    // Rerank 测试
    {
      "type": "rerank",
      "text": "机器学习是什么？",
      "documents": [
        "机器学习是人工智能的分支",
        "深度学习是机器学习的子领域",
        "自然语言处理是AI的应用"
      ]
    }
    ```

    **响应示例**：
    ```json
    {
      "status": "success",
      "message": "Embedding test completed successfully",
      "data": {
        "embedding_dim": 1024,
        "response_time": 0.234,
        "model_info": "Qwen/Qwen3-Embedding-0.6B"
      },
      "response_time": 0.234
    }
    ```
    """
    try:
        config_manager = get_config_manager()
        return await config_manager.test_config(test_request)
    except Exception as e:
        logger.error(f"配置测试失败: {str(e)}")
        logger.error(traceback.format_exc())
        if isinstance(e, ConfigError):
            raise config_error_to_http_error(e)
        else:
            raise HTTPException(status_code=500, detail=f"配置测试失败: {str(e)}")


def create_config_routes():
    """
    创建并返回配置路由
    此函数保持向后兼容性
    """
    return router
