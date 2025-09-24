from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from lightrag.config_manager import (
    get_app_config,
    reload_app_config,
    save_app_config,
    AppConfig,
)


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
    status: str
    message: Optional[str] = None
    data: Optional[dict] = None


def create_config_routes():
    """Create and return config router with routes defined inside to match project style."""

    @router.get("", response_model=GenericResponse)
    async def get_config():
        """Return the current application configuration."""
        try:
            reload_app_config()
            cfg = get_app_config()
            # use pydantic's model_dump to get plain dict
            data = cfg.model_dump()
            return GenericResponse(status="success", data=data)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/llm", response_model=GenericResponse)
    async def configure_llm(payload: LLMConfigPayload):
        """Update LLM configuration and persist to disk."""
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
        """Update Embedding configuration and persist to disk."""
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
        """Update simple rerank-related fields on lightrag_config and persist."""
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

    return router
