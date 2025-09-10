from lightrag.lightrag_manager import LightRagManager
from fastapi import APIRouter, HTTPException
import json


router = APIRouter(tags=["common"])


@router.get("/health/{collection_id}")
async def get_health(collection_id: str):
    """Get health status for a specific collection"""
    try:
        # Initialize the RAG instance
        rag_manager = LightRagManager()
        rag = await rag_manager.create_lightrag_instance(collection_id=collection_id)

        # Select only valuable health-related attributes
        health_attributes = {
            "workspace": getattr(rag, "workspace", None),
            "llm_model_name": getattr(rag, "llm_model_name", None),
            "max_graph_nodes": getattr(rag, "max_graph_nodes", None),
            "enable_llm_cache": getattr(rag, "enable_llm_cache", None),
            "chunk_token_size": getattr(rag, "chunk_token_size", None),
            "cosine_threshold": getattr(rag, "cosine_threshold", None),
            "summary_max_tokens": getattr(rag, "summary_max_tokens", None),
        }

        # Filter out non-serializable if needed, but these should be fine
        serializable_health = {}
        for key, value in health_attributes.items():
            try:
                json.dumps(value)
                serializable_health[key] = value
            except (TypeError, ValueError):
                serializable_health[key] = str(type(value).__name__)

        return {"status": "healthy", "health_attributes": serializable_health}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
