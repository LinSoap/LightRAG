from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class DocumentEntry(BaseModel):
    status: str = Field(..., description="Processing status of the document")
    chunks_count: int = Field(..., description="Number of chunks")
    chunks_list: List[str] = Field(
        default_factory=list, description="List of chunk ids"
    )
    content_summary: Optional[str] = Field(
        None, description="Summary of the document content"
    )
    content_length: Optional[int] = Field(
        None, description="Length of the document content in characters"
    )
    created_at: Optional[str] = Field(
        None, description="Creation timestamp (ISO string)"
    )
    updated_at: Optional[str] = Field(
        None, description="Last update timestamp (ISO string)"
    )
    file_path: Optional[str] = Field(None, description="Path to the original file")
    track_id: Optional[str] = Field(None, description="Track id for this document")
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Optional metadata dictionary"
    )
    error_msg: Optional[str] = Field(
        None, description="Error message if processing failed"
    )


class DocumentItem(BaseModel):
    doc_id: str = Field(..., description="Document identifier")
    status: str = Field(..., description="Processing status of the document")
    chunks_count: int = Field(..., description="Number of chunks")
    chunks_list: List[str] = Field(
        default_factory=list, description="List of chunk ids"
    )
    content_summary: Optional[str] = Field(
        None, description="Summary of the document content"
    )
    content_length: Optional[int] = Field(
        None, description="Length of the document content in characters"
    )
    created_at: Optional[str] = Field(
        None, description="Creation timestamp (ISO string)"
    )
    updated_at: Optional[str] = Field(
        None, description="Last update timestamp (ISO string)"
    )
    file_path: Optional[str] = Field(None, description="Path to the original file")
    track_id: Optional[str] = Field(None, description="Track id for this document")
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Optional metadata dictionary"
    )
    error_msg: Optional[str] = Field(
        None, description="Error message if processing failed"
    )


class CollectionItem(BaseModel):
    collection_id: str = Field(..., description="Collection identifier")
    documents: List[DocumentItem] = Field(
        default_factory=list, description="List of documents in this collection"
    )


class ListCollectionsResponse(BaseModel):
    status: Literal["success", "fail"] = Field(..., description="Operation status")
    collections: List[CollectionItem] = Field(
        default_factory=list,
        description="List of collections with their documents",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "collections": [
                    {
                        "collection_id": "didi",
                        "documents": [
                            {
                                "doc_id": "doc-df2ed33a4ed078e9e9057e8744471358",
                                "status": "processed",
                                "chunks_count": 3,
                                "chunks_list": [
                                    "chunk-b084d20b86cbaf9caeeb427b6e7f483c",
                                    "chunk-e573b2b863f9ce5dadb4c3baa69214e3",
                                    "chunk-d1ebae9051d9ad4df4bb86e632320f2c",
                                ],
                                "content_summary": "在上节课使用Team运行任务的时候",
                                "content_length": 8308,
                                "created_at": "2025-09-11T00:28:26.700465+00:00",
                                "updated_at": "2025-09-11T00:29:07.441920+00:00",
                                "file_path": "1.4 Autogen-Message.md",
                                "track_id": "upload_20250911_082826_eb3672d2",
                                "metadata": {
                                    "processing_start_time": 1757550506,
                                    "processing_end_time": 1757550547,
                                },
                                "error_msg": None,
                            }
                        ],
                    }
                ],
            }
        }


class CreateCollectionResponse(BaseModel):
    status: Literal["success", "fail"] = Field(..., description="Operation status")
    message: str = Field(..., description="Human readable message")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Collection 'my_collection' created successfully.",
            }
        }


class DeleteCollectionResponse(BaseModel):
    status: Literal["success", "fail"] = Field(..., description="Operation status")
    message: str = Field(..., description="Human readable message")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Collection 'my_collection' deleted successfully.",
            }
        }
