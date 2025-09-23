import traceback
from fastapi import APIRouter, HTTPException, Query, Path, Depends
from lightrag.api.schema.graph_schema import (
    EntityUpdateRequest,
    RelationUpdateRequest,
)
from lightrag.utils import (
    logger,
)

from lightrag.lightrag_manager import LightRagManager

router = APIRouter(prefix="/graph", tags=["graph"])


async def get_rag_manager():
    """Dependency to get LightRagManager instance"""
    return LightRagManager()


async def get_rag_instance(collection_id: str, manager: LightRagManager = Depends(get_rag_manager)):
    """Dependency to get RAG instance for a collection"""
    return await manager.get_rag_instance(collection_id)


@router.get("/label")
async def get_graph_labels(
    collection_id: str,
    rag=Depends(get_rag_instance)
):
    """
    Get all graph labels

    Returns:
        List[str]: List of graph labels
    """
    try:
        return await rag.get_graph_labels()
    except Exception as e:
        logger.error(f"Error getting graph labels: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Error getting graph labels: {str(e)}"
        )


@router.get("/")
async def get_knowledge_graph(
    collection_id: str,
    label: str = Query(..., description="Label to get knowledge graph for"),
    max_depth: int = Query(3, description="Maximum depth of graph", ge=1),
    max_nodes: int = Query(1000, description="Maximum nodes to return", ge=1),
    rag=Depends(get_rag_instance)
):
    """
    Retrieve a connected subgraph of nodes where the label includes the specified label.
    When reducing the number of nodes, the prioritization criteria are as follows:
        1. Hops(path) to the staring node take precedence
        2. Followed by the degree of the nodes

    Args:
        label (str): Label of the starting node
        max_depth (int, optional): Maximum depth of the subgraph,Defaults to 3
        max_nodes: Maximum nodes to return

    Returns:
        Dict[str, List[str]]: Knowledge graph for label
    """
    try:
        # Log the label parameter to check for leading spaces
        logger.debug(
            f"get_knowledge_graph called with label: '{label}' (length: {len(label)}, repr: {repr(label)})"
        )
        return await rag.get_knowledge_graph(
            node_label=label,
            max_depth=max_depth,
            max_nodes=max_nodes,
        )
    except Exception as e:
        logger.error(f"Error getting knowledge graph for label '{label}': {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Error getting knowledge graph: {str(e)}"
        )


@router.get("/entity")
async def check_entity_exists(
    collection_id: str,
    name: str = Query(..., description="Entity name to check"),
    rag=Depends(get_rag_instance)
):
    """
    Check if an entity with the given name exists in the knowledge graph

    Args:
        name (str): Name of the entity to check

    Returns:
        Dict[str, bool]: Dictionary with 'exists' key indicating if entity exists
    """
    try:
        exists = await rag.chunk_entity_relation_graph.has_node(name)
        return {"exists": exists}
    except Exception as e:
        logger.error(f"Error checking entity existence for '{name}': {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Error checking entity existence: {str(e)}"
        )


@router.post("/entity")
async def update_entity(
    collection_id: str,
    request: EntityUpdateRequest,
    rag=Depends(get_rag_instance)
):
    """
    Update an entity's properties in the knowledge graph

    Args:
        request (EntityUpdateRequest): Request containing entity name, updated data, and rename flag

    Returns:
        Dict: Updated entity information
    """
    try:
        result = await rag.aedit_entity(
            entity_name=request.entity_name,
            updated_data=request.updated_data,
            allow_rename=request.allow_rename,
        )
        return {
            "status": "success",
            "message": "Entity updated successfully",
            "data": result,
        }
    except ValueError as ve:
        logger.error(
            f"Validation error updating entity '{request.entity_name}': {str(ve)}"
        )
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error updating entity '{request.entity_name}': {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Error updating entity: {str(e)}"
        )


@router.post("/relation")
async def update_relation(
    collection_id: str,
    request: RelationUpdateRequest,
    rag=Depends(get_rag_instance)
):
    """
    Update a relation's properties in the knowledge graph

    Args:
        request (RelationUpdateRequest): Request containing source ID, target ID and updated data

    Returns:
        Dict: Updated relation information
    """
    try:
        result = await rag.aedit_relation(
            source_entity=request.source_id,
            target_entity=request.target_id,
            updated_data=request.updated_data,
        )
        return {
            "status": "success",
            "message": "Relation updated successfully",
            "data": result,
        }
    except ValueError as ve:
        logger.error(
            f"Validation error updating relation between '{request.source_id}' and '{request.target_id}': {str(ve)}"
        )
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(
            f"Error updating relation between '{request.source_id}' and '{request.target_id}': {str(e)}"
        )
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Error updating relation: {str(e)}"
        )


def create_graph_routes():
    """
    Create and return the graph router
    This function is maintained for backward compatibility
    """
    return router
