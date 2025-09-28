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
        Handle a POST request at the /query endpoint to process user queries using RAG capabilities.

        Parameters:
            request (QueryRequest): The request object containing the query parameters.
        Returns:
            GenericResponse[QueryData]: A standardized response containing the query result with metadata.

        Raises:
            HTTPException: Raised when an error occurs during the request handling process,
                       with status code 500 and detail containing the exception message.
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
