from fastapi import APIRouter, HTTPException

from lightrag.config_manager import (
    EmbeddingConfig,
    LLMConfig,
    LightRAGConfig,
    get_app_config,
    reload_app_config,
    save_app_config,
)
from lightrag.lightrag_manager import LightRagManager
from lightrag.api.schemas.common import (
    GenericResponse,
    AppConfigData,
    TestResponseData,
)
from lightrag.api.schemas.config import (
    LLMConfigPayload,
    EmbeddingConfigPayload,
    RerankConfigPayload,
    TestPayload,
)
import numpy as _np


router = APIRouter(prefix="/config", tags=["config"])


def create_config_routes():
    """Create and return config router with routes defined inside to match project style."""

    @router.get("", response_model=GenericResponse[AppConfigData])
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
                data=AppConfigData(
                    lightrag_config=cfg.lightrag_config,
                    llm_config=cfg.llm_config,
                    embedding_config=cfg.embedding_config,
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
            "LLM_BINDING_API_KEY": "sk-..."
        }

        响应示例：

        {"status": "success", "message": "LLM config updated", "data": {...}}
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
            return GenericResponse(
                status="success", message="LLM config updated", data=llm.model_dump()
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
            "EMBEDDING_BINDING_API_KEY": "sk-..."
        }

        响应示例：

        {"status": "success", "message": "Embedding config updated", "data": {...}}
        """

        try:
            cfg = get_app_config()
            emb = cfg.embedding_config
            for k, v in payload.model_dump().items():
                if v is not None:
                    setattr(emb, k, v)
            save_app_config()
            return GenericResponse(
                status="success",
                message="Embedding config updated",
                data=emb.model_dump(),
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/rerank", response_model=GenericResponse[LightRAGConfig])
    async def configure_rerank(payload: RerankConfigPayload):
        """
        更新 rerank 相关的简易配置字段（目前写入 `lightrag_config` 下）。

        请求示例： {"COSINE_THRESHOLD": 0.25, "MAX_BATCH_SIZE": 16}
        """
        try:
            cfg = get_app_config()
            lr = cfg.lightrag_config
            for k, v in payload.model_dump().items():
                if v is not None and hasattr(lr, k):
                    setattr(lr, k, v)
            save_app_config()
            return GenericResponse(
                status="success", message="Rerank config updated", data=lr.model_dump()
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/test", response_model=GenericResponse[TestResponseData])
    async def test_connection(payload: TestPayload):
        """
        测试 LLM / Embedding 的连通性。

        请求体（JSON）示例：

        - 测试 LLM:
          {"target": "llm", "message": "你好"}

        - 测试 Embedding:
          {"target": "embedding", "message": "测试向量"}

        成功响应示例（LLM）：
        {"status":"success","message":"LLM test succeeded","data":{"result":"..."}}

        成功响应示例（Embedding）：
        {"status":"success","message":"Embedding test succeeded","data":{"result": [[0.12, -0.03, ...]]}}
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

            else:
                raise HTTPException(
                    status_code=400,
                    detail="Unsupported test target. Use 'llm' or 'embedding'.",
                )

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router
