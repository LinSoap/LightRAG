import traceback
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Path, Depends
from lightrag.api.schemas.graph import (
    EntityUpdateRequest,
    RelationUpdateRequest,
    GraphLabelsData,
    GraphData,
    EntityExistsData,
    EntityUpdateData,
    RelationUpdateData,
)
from lightrag.api.schemas.common import GenericResponse
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


@router.get("/label", response_model=GenericResponse[GraphLabelsData])
async def get_graph_labels(
    collection_id: str,
    rag=Depends(get_rag_instance)
) -> GenericResponse[GraphLabelsData]:
    """
    Get all graph labels

    Returns:
        GenericResponse[GraphLabelsData]: List of graph labels with metadata
    """
    try:
        labels = await rag.get_graph_labels()
        data = GraphLabelsData(
            labels=labels,
            total_labels=len(labels)
        )
        return GenericResponse(
            status="success",
            message=f"Found {len(labels)} graph labels",
            data=data
        )
    except Exception as e:
        logger.error(f"Error getting graph labels: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Error getting graph labels: {str(e)}"
        )


@router.get("/", response_model=GenericResponse[GraphData])
async def get_knowledge_graph(
    collection_id: str,
    label: str = Query(..., description="Label to get knowledge graph for"),
    max_depth: int = Query(3, description="Maximum depth of graph", ge=1),
    max_nodes: int = Query(1000, description="Maximum nodes to return", ge=1),
    rag=Depends(get_rag_instance)
) -> GenericResponse[GraphData]:
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
        GenericResponse[GraphData]: Knowledge graph for label with metadata
    """
    try:
        # Log the label parameter to check for leading spaces
        logger.debug(
            f"get_knowledge_graph called with label: '{label}' (length: {len(label)}, repr: {repr(label)})"
        )
        graph_result = await rag.get_knowledge_graph(
            node_label=label,
            max_depth=max_depth,
            max_nodes=max_nodes,
        )

        # Convert graph result to our data models
        nodes = [GraphNode(id=node.id, label=node.label, properties=node.properties) for node in graph_result.nodes]
        edges = [GraphEdge(source=edge.source, target=edge.target, type=edge.type, properties=edge.properties) for edge in graph_result.edges]

        data = GraphData(
            nodes=nodes,
            edges=edges,
            total_nodes=len(nodes),
            total_edges=len(edges),
            max_depth_reached=graph_result.max_depth if hasattr(graph_result, 'max_depth') else max_depth,
            query_label=label,
            timestamp=datetime.now()
        )

        return GenericResponse(
            status="success",
            message=f"Retrieved knowledge graph for label '{label}' with {len(nodes)} nodes and {len(edges)} edges",
            data=data
        )
    except Exception as e:
        logger.error(f"Error getting knowledge graph for label '{label}': {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Error getting knowledge graph: {str(e)}"
        )


@router.get("/entity", response_model=GenericResponse[EntityExistsData])
async def check_entity_exists(
    collection_id: str,
    name: str = Query(..., description="Entity name to check"),
    rag=Depends(get_rag_instance)
) -> GenericResponse[EntityExistsData]:
    """
    Check if an entity with the given name exists in the knowledge graph

    Args:
        name (str): Name of the entity to check

    Returns:
        GenericResponse[EntityExistsData]: Entity existence information with statistics
    """
    try:
        exists = await rag.chunk_entity_relation_graph.has_node(name)

        node_count = None
        edge_count = None

        if exists:
            # Get entity-specific statistics
            edges = await rag.chunk_entity_relation_graph.get_node_edges(name)
            if edges:
                edge_count = len(edges)
                connected_nodes = set()
                for src, tgt in edges:
                    if src != name:
                        connected_nodes.add(src)
                    if tgt != name:
                        connected_nodes.add(tgt)
                node_count = len(connected_nodes) + 1
            else:
                node_count = 1
                edge_count = 0

        data = EntityExistsData(
            exists=exists,
            entity_name=name,
            node_count=node_count,
            edge_count=edge_count,
            timestamp=datetime.now()
        )

        return GenericResponse(
            status="success",
            message=f"Entity '{name}' existence check completed",
            data=data
        )
    except Exception as e:
        logger.error(f"Error checking entity existence for '{name}': {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Error checking entity existence: {str(e)}"
        )


@router.post("/entity", response_model=GenericResponse[EntityUpdateData])
async def update_entity(
    collection_id: str,
    request: EntityUpdateRequest,
    rag=Depends(get_rag_instance)
) -> GenericResponse[EntityUpdateData]:
    """
    Update an entity's properties in the knowledge graph

    Args:
        request (EntityUpdateRequest): Request containing entity name, updated data, and rename flag

    Returns:
        GenericResponse[EntityUpdateData]: Updated entity information with metadata
    """
    try:
        result = await rag.aedit_entity(
            entity_name=request.entity_name,
            updated_data=request.updated_data,
            allow_rename=request.allow_rename,
        )

        # Extract rename information if applicable
        was_renamed = False
        old_name = None
        new_name = None

        if request.allow_rename and "new_name" in request.updated_data:
            was_renamed = True
            old_name = request.entity_name
            new_name = request.updated_data["new_name"]

        data = EntityUpdateData(
            entity_name=result.get("name", request.entity_name),
            updated_properties=result.get("properties", {}),
            was_renamed=was_renamed,
            old_name=old_name,
            new_name=new_name,
            timestamp=datetime.now()
        )

        return GenericResponse(
            status="success",
            message="Entity updated successfully",
            data=data
        )
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


@router.post("/relation", response_model=GenericResponse[RelationUpdateData])
async def update_relation(
    collection_id: str,
    request: RelationUpdateRequest,
    rag=Depends(get_rag_instance)
) -> GenericResponse[RelationUpdateData]:
    """
    Update a relation's properties in the knowledge graph

    Args:
        request (RelationUpdateRequest): Request containing source ID, target ID and updated data

    Returns:
        GenericResponse[RelationUpdateData]: Updated relation information with metadata
    """
    try:
        result = await rag.aedit_relation(
            source_entity=request.source_id,
            target_entity=request.target_id,
            updated_data=request.updated_data,
        )

        data = RelationUpdateData(
            source_id=request.source_id,
            target_id=request.target_id,
            relation_type=result.get("type", "unknown"),
            updated_properties=result.get("properties", {}),
            timestamp=datetime.now()
        )

        return GenericResponse(
            status="success",
            message="Relation updated successfully",
            data=data
        )
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
