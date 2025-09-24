import json
import time
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException

from lightrag.api.schemas.query import QueryRequest, QueryData
from lightrag.api.schemas.common import GenericResponse
from ascii_colors import trace_exception

from lightrag.lightrag_manager import LightRagManager


router = APIRouter(tags=["query"])


def create_query_routes():
    @router.post("/query", response_model=GenericResponse[QueryData])
    async def query_text(collection_id: str, request: QueryRequest) -> GenericResponse[QueryData]:
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
            start_time = time.time()
            param = request.to_query_params(False)
            lightrag_manager = LightRagManager()
            rag = await lightrag_manager.get_rag_instance(collection_id=collection_id)
            response = await rag.aquery(request.query, param=param)
            query_time = time.time() - start_time

            # Extract response content
            if isinstance(response, str):
                response_content = response
            elif isinstance(response, dict):
                response_content = json.dumps(response, indent=2)
            else:
                response_content = str(response)

            # Extract metadata
            sources_count = _extract_sources_count(response)
            conversation_turns = _extract_conversation_turns(request.conversation_history)

            data = QueryData(
                response=response_content,
                query_mode=request.mode,
                response_type=request.response_type,
                query_time=query_time,
                sources_count=sources_count,
                conversation_turns=conversation_turns,
                timestamp=datetime.now()
            )

            return GenericResponse(
                status="success",
                message="Query processed successfully",
                data=data
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
