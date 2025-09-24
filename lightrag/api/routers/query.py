import json
from fastapi import APIRouter, HTTPException

from lightrag.api.schemas.query import QueryRequest, QueryResponse
from ascii_colors import trace_exception

from lightrag.lightrag_manager import LightRagManager


router = APIRouter(tags=["query"])


def create_query_routes():
    @router.post("/query", response_model=QueryResponse)
    async def query_text(collection_id: str, request: QueryRequest):
        """
        Handle a POST request at the /query endpoint to process user queries using RAG capabilities.

        Parameters:
            request (QueryRequest): The request object containing the query parameters.
        Returns:
            QueryResponse: A Pydantic model containing the result of the query processing.
                       If a string is returned (e.g., cache hit), it's directly returned.
                       Otherwise, an async generator may be used to build the response.

        Raises:
            HTTPException: Raised when an error occurs during the request handling process,
                       with status code 500 and detail containing the exception message.
        """
        try:
            param = request.to_query_params(False)
            lightrag_manager = LightRagManager()
            rag = await lightrag_manager.get_rag_instance(collection_id=collection_id)
            response = await rag.aquery(request.query, param=param)

            # If response is a string (e.g. cache hit), return directly
            if isinstance(response, str):
                return QueryResponse(response=response)

            if isinstance(response, dict):
                result = json.dumps(response, indent=2)
                return QueryResponse(response=result)
            else:
                return QueryResponse(response=str(response))
        except Exception as e:
            trace_exception(e)
            raise HTTPException(status_code=500, detail=str(e))

    return router
