from typing import Any, Dict, List, Literal, Optional
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from lightrag.api.utils.date import format_datetime
from lightrag.base import DocStatus


# 保持原有的请求模型，这些不需要改为GenericResponse格式
class DeleteDocRequest(BaseModel):
    doc_ids: List[str] = Field(..., description="The IDs of the documents to delete.")
    delete_file: bool = Field(
        default=False,
        description="Whether to delete the corresponding file in the upload directory.",
    )

    @field_validator("doc_ids", mode="after")
    @classmethod
    def validate_doc_ids(cls, doc_ids: List[str]) -> List[str]:
        if not doc_ids:
            raise ValueError("Document IDs list cannot be empty")

        validated_ids = []
        for doc_id in doc_ids:
            if not doc_id or not doc_id.strip():
                raise ValueError("Document ID cannot be empty")
            validated_ids.append(doc_id.strip())

        # Check for duplicates
        if len(validated_ids) != len(set(validated_ids)):
            raise ValueError("Document IDs must be unique")

        return validated_ids


# 新的数据模型用于GenericResponse
class DocumentItem(BaseModel):
    id: str = Field(description="Document identifier")
    collection_id: str = Field(description="Collection identifier")
    content_summary: str = Field(description="Summary of document content")
    content_length: int = Field(description="Length of document content in characters")
    status: DocStatus = Field(description="Current processing status")
    created_at: str = Field(description="Creation timestamp (ISO format string)")
    updated_at: str = Field(description="Last update timestamp (ISO format string)")
    track_id: Optional[str] = Field(
        default=None, description="Tracking ID for monitoring progress"
    )
    chunks_count: Optional[int] = Field(
        default=None, description="Number of chunks the document was split into"
    )
    error_msg: Optional[str] = Field(
        default=None, description="Error message if processing failed"
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None, description="Additional metadata about the document"
    )
    file_path: str = Field(description="Path to the document file")


class DocumentsListData(BaseModel):
    documents: List[DocumentItem]
    total_documents: int
    collection_id: str


class DocumentChunk(BaseModel):
    id: str = Field(description="Chunk identifier")
    content: str = Field(description="Chunk content")
    document_id: str = Field(description="Parent document ID")
    chunk_index: int = Field(description="Index of the chunk in the document")
    metadata: Optional[dict[str, Any]] = Field(
        default=None, description="Additional metadata about the chunk"
    )


class DocumentChunksData(BaseModel):
    doc_id: str
    chunks: List[DocumentChunk]
    total_chunks: int
    limit: int
    offset: int


class DocumentUploadData(BaseModel):
    filename: str
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    track_id: str
    upload_status: Literal["success", "duplicated", "partial_success", "failure"]
    message: str
    processing_started: bool
    timestamp: datetime


class PipelineStatusData(BaseModel):
    autoscanned: bool
    busy: bool
    job_name: str
    job_start: Optional[str]
    docs: int
    batchs: int
    cur_batch: int
    request_pending: bool
    latest_message: str
    history_messages: Optional[List[str]]
    update_status: Optional[dict]
    timestamp: datetime


class TrackStatusData(BaseModel):
    track_id: str
    documents: List[DocumentItem]
    total_count: int
    status_summary: Dict[str, int]
    timestamp: datetime


class DocumentDeletionData(BaseModel):
    operation_id: str
    status: Literal["deletion_started", "busy", "not_allowed"]
    message: str
    affected_documents: List[str]
    files_to_delete: bool
    timestamp: datetime
