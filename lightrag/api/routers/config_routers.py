from typing import Optional, Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from lightrag.config_manager import (
    get_app_config,
    reload_app_config,
    save_app_config,
)
from lightrag.lightrag_manager import LightRagManager
import numpy as _np


router = APIRouter(prefix="/config", tags=["config"])


class LLMConfigPayload(BaseModel):
    LLM_BINDING: Optional[str] = None
    LLM_MODEL: Optional[str] = None
    LLM_BINDING_HOST: Optional[str] = None
    LLM_BINDING_API_KEY: Optional[str] = None


class EmbeddingConfigPayload(BaseModel):
    EMBEDDING_BINDING: Optional[str] = None
    EMBEDDING_MODEL: Optional[str] = None
    EMBEDDING_BINDING_HOST: Optional[str] = None
    EMBEDDING_BINDING_API_KEY: Optional[str] = None
    EMBEDDING_DIM: Optional[int] = None


class RerankConfigPayload(BaseModel):
    # Rerank settings are stored under 'lightrag_config' for now; keep simple fields
    COSINE_BETTER_THAN_THRESHOLD: Optional[float] = None
    COSINE_THRESHOLD: Optional[float] = None
    MAX_BATCH_SIZE: Optional[int] = None


class GenericResponse(BaseModel):
    """通用响应结构。"""

    status: str
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class AppConfigResponse(BaseModel):
    """更精确地返回 AppConfig 的三部分子配置，便于客户端使用。"""

    status: str
    lightrag_config: Dict[str, Any]
    llm_config: Dict[str, Any]
    embedding_config: Dict[str, Any]


class TestPayload(BaseModel):
    """用于 /config/test 的请求体。

    target: 要测试的目标，支持 'llm' 或 'embedding'；
    message: 发送给 LLM 的短文本或用于生成 embedding 的文本。
    """

    target: str = "llm"
    message: Optional[str] = "你好"


def create_config_routes():
    """Create and return config router with routes defined inside to match project style."""

    @router.get("", response_model=AppConfigResponse)
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
            data = cfg.model_dump()
            return AppConfigResponse(
                status="success",
                lightrag_config=data.get("lightrag_config", {}),
                llm_config=data.get("llm_config", {}),
                embedding_config=data.get("embedding_config", {}),
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/llm", response_model=GenericResponse)
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

    @router.post("/embedding", response_model=GenericResponse)
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

    @router.post("/rerank", response_model=GenericResponse)
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

    @router.post("/test", response_model=GenericResponse)
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
