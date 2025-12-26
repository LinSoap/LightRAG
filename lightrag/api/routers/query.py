import json
import time
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException

from lightrag.api.schemas.query import QueryRequest, QueryResponse
from lightrag.api.schemas.common import GenericResponse
from ascii_colors import trace_exception

from lightrag.lightrag_manager import LightRagManager


router = APIRouter(tags=["query"])


def create_query_routes():
    @router.post("/query", response_model=GenericResponse[QueryResponse])
    async def query_text(
        collection_id: str, request: QueryRequest
    ) -> GenericResponse[QueryResponse]:
        """
        处理 POST /query 请求，使用 RAG（检索增强生成）能力处理用户查询。

        示例:
            {
              "query": "宪法",
              "mode": "mix",
              "only_need_context": true,
              "only_need_prompt": true,
              "response_type": "Multiple Paragraphs",
              "top_k": 20,
              "chunk_top_k": 20,
              "max_entity_tokens": 12000,
              "max_relation_tokens": 12000,
              "max_total_tokens": 12000
            }

        参数:
            - query: 查询文本。
            - mode: 查询模式（local、global、hybrid、naive、mix、bypass）。
            - only_need_context: 若为 True，则只返回检索到的上下文，不生成最终回答。
            - only_need_prompt: 若为 True，则只返回生成的 prompt，不返回最终回答。
            - response_type: 返回格式，示例：'Multiple Paragraphs'、'Single Paragraph'、'Bullet Points'。
            - top_k: 检索的实体数量上限。
            - chunk_top_k: 检索的文本块数量上限。
            - max_entity_tokens: 实体的最大 token 限制。
            - max_relation_tokens: 关系的最大 token 限制。
            - max_total_tokens: 总 token 限制。

        返回:
            GenericResponse[QueryResponse]：包含查询结果与元信息的标准化响应。

        异常:
            HTTPException：处理请求时发生错误时抛出，状态码为 500，detail 包含异常信息。
        """
        try:
            param = request.to_query_params(False)
            lightrag_manager = LightRagManager()
            rag = await lightrag_manager.get_rag_instance(collection_id=collection_id)
            response = await rag.aquery(request.query, param=param)

            return GenericResponse(
                status="success",
                message="Query processed successfully",
                data=response,
            )
        except Exception as e:
            trace_exception(e)
            raise HTTPException(status_code=500, detail=str(e))

    return router


def _extract_sources_count(response) -> Optional[int]:
    """Extract the number of sources from the response."""
    if isinstance(response, dict):
        sources = response.get("sources", [])
        if isinstance(sources, list):
            return len(sources)
    return None


def _extract_conversation_turns(conversation_history) -> Optional[int]:
    """Extract the number of conversation turns from the history."""
    if conversation_history:
        return len(conversation_history) // 2  # Each turn consists of user + assistant
    return None

    return router
