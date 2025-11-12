from fastapi import APIRouter, HTTPException

from lightrag.config_manager import (
    AppConfig,
    EmbeddingConfig,
    LLMConfig,
    RerankConfig,
    get_app_config,
    reload_app_config,
    save_app_config,
)
from lightrag.lightrag_manager import LightRagManager
from lightrag.api.schemas.common import (
    GenericResponse,
    TestResponseData,
)
from lightrag.api.schemas.config import (
    LLMConfigPayload,
    EmbeddingConfigPayload,
    TestPayload,
)
import numpy as _np


router = APIRouter(prefix="/config", tags=["config"])


def create_config_routes():
    """Create and return config router with routes defined inside to match project style."""

    @router.get("", response_model=GenericResponse[AppConfig])
    async def get_config():
        """
        获取当前应用配置。

        返回示例：
        {
          "status": "success",
          "lightrag_config": { ... },
          "llm_config": { ... },
          "embedding_config": { ... }
        }
        """
        try:
            reload_app_config()
            cfg = get_app_config()
            return GenericResponse(
                status="success",
                data=AppConfig(
                    lightrag_config=cfg.lightrag_config,
                    llm_config=cfg.llm_config,
                    embedding_config=cfg.embedding_config,
                    rerank_config=cfg.rerank_config,
                ),
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/llm", response_model=GenericResponse[LLMConfig])
    async def configure_llm(payload: LLMConfigPayload):
        """
        更新 LLM 配置并持久化。

        请求示例：

        - 测试性更新（只更新模型名称）
        {
            "LLM_MODEL": "gpt-4o-mini"
        }

        - 全量更新（替换绑定与 host）
        {
            "LLM_BINDING": "openai",
            "LLM_MODEL": "gpt-4o-mini",
            "LLM_BINDING_HOST": "https://api.openai.com/v1",
            "LLM_BINDING_API_KEY": "sk-...",
            "LLM_TIMEOUT": 600
        }

        响应示例：

        {"status": "success", "message": "LLM config updated", "data": {...}}

        注意：更新配置后，所有现有的 RAG 实例将被清除，新的请求会使用新配置创建实例。
        """

        try:
            cfg = get_app_config()
            # update only provided fields
            llm = cfg.llm_config
            for k, v in payload.model_dump().items():
                if v is not None:
                    setattr(llm, k, v)
            # save
            save_app_config()

            # 清除所有现有的 RAG 实例，以便使用新配置重新创建
            # 这确保超时等配置立即生效
            manager = LightRagManager()
            cleared_count = len(manager.rag_instances)
            manager.rag_instances.clear()

            message = f"LLM config updated. {cleared_count} RAG instance(s) cleared and will be recreated with new config."
            return GenericResponse(
                status="success", message=message, data=llm.model_dump()
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/embedding", response_model=GenericResponse[EmbeddingConfig])
    async def configure_embedding(payload: EmbeddingConfigPayload):
        """
        更新 Embedding 配置并持久化。

        请求示例：

        - 更换 Embedding 提供方并指定模型
        {
            "EMBEDDING_BINDING": "openai",
            "EMBEDDING_MODEL": "text-embedding-3-large",
            "EMBEDDING_DIM": 3072,
            "EMBEDDING_BINDING_HOST": "https://api.openai.com/v1",
            "EMBEDDING_BINDING_API_KEY": "sk-...",
            "EMBEDDING_TIMEOUT": 300
        }

        响应示例：

        {"status": "success", "message": "Embedding config updated", "data": {...}}

        注意：更新配置后，所有现有的 RAG 实例将被清除，新的请求会使用新配置创建实例。
        """

        try:
            cfg = get_app_config()
            emb = cfg.embedding_config
            for k, v in payload.model_dump().items():
                if v is not None:
                    setattr(emb, k, v)
            save_app_config()

            # 清除所有现有的 RAG 实例，以便使用新配置重新创建
            manager = LightRagManager()
            cleared_count = len(manager.rag_instances)
            manager.rag_instances.clear()

            message = f"Embedding config updated. {cleared_count} RAG instance(s) cleared and will be recreated with new config."
            return GenericResponse(
                status="success",
                message=message,
                data=emb.model_dump(),
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/rerank", response_model=GenericResponse[RerankConfig])
    async def configure_rerank(payload: RerankConfig):
        """
        更新 rerank 配置并持久化。

        RerankConfig 字段说明：
        - ENABLE_RERANK (bool): 是否启用重排序，默认 True。
        - RERANK_BINDING (Optional[str]): 绑定提供方，可能值：None, "cohere", "jina", "aliyun" 等。
        - RERANK_MODEL (Optional[str]): 重排序使用的模型名称。
        - RERANK_BINDING_HOST (Optional[str]): 绑定的主机地址。
        - RERANK_BINDING_API_KEY (Optional[str]): 绑定的 API Key。
        - MIN_RERANK_SCORE (float): 最低重排序分数阈值，默认 0.6。

        请求示例（部分更新）：
        {
            "MIN_RERANK_SCORE": 0.5,
            "ENABLE_RERANK": true
        }

        请求示例（全量更新）：
        {
            "ENABLE_RERANK": true,
            "RERANK_BINDING": "cohere",
            "RERANK_MODEL": "rerank-medium",
            "RERANK_BINDING_HOST": "https://api.cohere.ai",
            "RERANK_BINDING_API_KEY": "cohere-xxxxxx",
            "MIN_RERANK_SCORE": 0.65
        }

        注意：
        - 仅提供的字段会被更新，未提供的字段将保持原值。
        - MIN_RERANK_SCORE 应为 0.0 到 1.0 之间的浮点数。
        """
        try:
            cfg = get_app_config()
            rerank = cfg.rerank_config

            # Update rerank config fields
            for k, v in payload.model_dump().items():
                if v is not None:
                    setattr(rerank, k, v)

            save_app_config()
            return GenericResponse(
                status="success",
                message="Rerank config updated",
                data=rerank.model_dump(),
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/test", response_model=GenericResponse[TestResponseData])
    async def test_connection(payload: TestPayload):
        """
        测试 LLM / Embedding / Rerank 的连通性。

        请求体（JSON）示例：

        - 测试 LLM:
          {"target": "llm", "message": "你好"}

        - 测试 Embedding:
          {"target": "embedding", "message": "测试向量"}

        - 测试 Rerank:
          {
            "target": "rerank",
            "message": "什么是机器学习？",
            "documents": [
              "机器学习是人工智能的一个重要分支。",
              "深度学习是机器学习的子集。",
              "神经网络是深度学习的基础。"
            ]
          }

        成功响应示例（LLM）：
        {"status":"success","message":"LLM test succeeded","data":{"result":"..."}}

        成功响应示例（Embedding）：
        {"status":"success","message":"Embedding test succeeded","data":{"result": [[0.12, -0.03, ...]]}}

        成功响应示例（Rerank）：
        {"status":"success","message":"Rerank test succeeded","data":{"result": [{"index": 1, "relevance_score": 0.95}, {"index": 0, "relevance_score": 0.75}]}}
        """
        try:
            target = (payload.target or "").lower()
            manager = LightRagManager()

            if target == "llm":
                binding = manager.llm_config.LLM_BINDING or "openai"
                # create llm function from binding
                llm_func = manager._create_llm_model_func(binding)
                # call with a small test prompt
                prompt = payload.message or "你好"
                result = await llm_func(prompt)

                # handle async generator responses
                if hasattr(result, "__aiter__"):
                    parts = []
                    async for chunk in result:
                        parts.append(str(chunk))
                    normalized = "".join(parts)
                else:
                    normalized = str(result)

                return GenericResponse(
                    status="success",
                    message="LLM test succeeded",
                    data={"result": normalized},
                )

            elif target == "embedding":
                emb_func = manager.create_optimized_embedding_function()
                texts = [payload.message or "Test embedding"]
                emb = await emb_func(texts)

                def _np_to_list(obj):
                    try:
                        if isinstance(obj, _np.ndarray):
                            return obj.tolist()
                    except Exception:
                        pass
                    if isinstance(obj, list):
                        return [_np_to_list(x) for x in obj]
                    return obj

                normalized = _np_to_list(emb)
                return GenericResponse(
                    status="success",
                    message="Embedding test succeeded",
                    data={"result": normalized},
                )
            elif target == "rerank":
                # Test rerank functionality - use message as query and documents as document list
                query = payload.message or "什么是机器学习？"
                documents = payload.documents or [
                    "机器学习是人工智能的一个重要分支。",
                    "深度学习是机器学习的子集。",
                    "神经网络是深度学习的基础。",
                ]

                # Try to get a configured rerank function from rerank module
                from lightrag.rerank import get_rerank_func

                cfg = get_app_config()
                binding = (cfg.rerank_config.RERANK_BINDING or "jina").lower()

                # Prefer the configured universal rerank function when available
                rerank_func = get_rerank_func(
                    api_key=cfg.rerank_config.RERANK_BINDING_API_KEY,
                    model=cfg.rerank_config.RERANK_MODEL,
                    base_url=cfg.rerank_config.RERANK_BINDING_HOST,
                )

                if rerank_func is None:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unsupported rerank binding for test: {binding}",
                    )

                raw_result = await rerank_func(
                    query=query, documents=documents, top_n=3
                )

                # If rerank returns index-based results, map back to document texts
                if (
                    raw_result
                    and isinstance(raw_result, list)
                    and isinstance(raw_result[0], dict)
                    and "index" in raw_result[0]
                ):
                    mapped = []
                    for item in raw_result:
                        idx = item.get("index")
                        score = item.get("relevance_score")
                        doc_text = (
                            documents[idx]
                            if isinstance(idx, int) and 0 <= idx < len(documents)
                            else None
                        )
                        mapped.append(
                            {
                                "index": idx,
                                "relevance_score": score,
                                "document": doc_text,
                            }
                        )
                    result = mapped
                else:
                    # Legacy format or already full documents
                    result = raw_result

                return GenericResponse(
                    status="success",
                    message=f"Rerank test succeeded (using {binding} provider)",
                    data={"result": result},
                )

            else:
                raise HTTPException(
                    status_code=400,
                    detail="Unsupported test target. Use 'llm', 'embedding' or 'rerank'.",
                )

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router
