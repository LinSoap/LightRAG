from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel


class RelationUpdateRequest(BaseModel):
    source_id: str
    target_id: str
    updated_data: Dict[str, Any]


class EntityUpdateRequest(BaseModel):
    entity_name: str
    updated_data: Dict[str, Any]
    allow_rename: bool = False


class GraphLabelsData(BaseModel):
    labels: List[str]
    total_labels: int


class GraphNode(BaseModel):
    id: str
    label: str
    properties: Dict[str, Any]


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str
    properties: Dict[str, Any]


class GraphData(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    total_nodes: int
    total_edges: int
    max_depth_reached: int
    query_label: str
    timestamp: datetime


class EntityExistsData(BaseModel):
    exists: bool
    entity_name: str
    node_count: Optional[int] = None
    edge_count: Optional[int] = None
    timestamp: datetime


class EntityUpdateData(BaseModel):
    entity_name: str
    updated_properties: Dict[str, Any]
    was_renamed: bool
    old_name: Optional[str] = None
    new_name: Optional[str] = None
    timestamp: datetime


class RelationUpdateData(BaseModel):
    source_id: str
    target_id: str
    relation_type: str
    updated_properties: Dict[str, Any]
    timestamp: datetime
