from pathlib import Path
import shutil
from datetime import datetime
from lightrag.api.schemas.collection import (
    CollectionsListData,
    CollectionCreateData,
    CollectionDeleteData,
    CollectionBatchData,
    CollectionItem,
    DocumentItem,
)
from lightrag.api.schemas.common import GenericResponse
from lightrag.path_manager import get_default_storage_dir
from lightrag.document_manager import DocumentManager
from lightrag.lightrag_manager import LightRagManager
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from lightrag.utils import logger


router = APIRouter(prefix="/collection", tags=["collection"])


def create_collection_routes():
    lightrag_manager = LightRagManager()

    @router.get("", response_model=GenericResponse[CollectionsListData])
    async def list_collections() -> GenericResponse[CollectionsListData]:
        """List all collections"""
        try:
            # Initialize the RAG instance
            rag_manager = LightRagManager()
            collections = await rag_manager.list_collections()
            collections_list = []
            # collections is a mapping: collection_name -> {doc_id: doc_status_dict}
            for name, docs in collections.items():
                documents_list = []
                if isinstance(docs, dict):
                    for doc_id, doc_data in docs.items():
                        # doc_data may already be a dict with expected keys
                        documents_list.append(
                            DocumentItem(
                                doc_id=doc_id,
                                status=doc_data.get("status", "unknown"),
                                chunks_count=doc_data.get("chunks_count", 0),
                                chunks_list=doc_data.get("chunks_list", []),
                                content_summary=doc_data.get("content_summary"),
                                content_length=doc_data.get("content_length"),
                                created_at=doc_data.get("created_at"),
                                updated_at=doc_data.get("updated_at"),
                                file_path=doc_data.get("file_path"),
                                track_id=doc_data.get("track_id"),
                                metadata=doc_data.get("metadata"),
                                error_msg=doc_data.get("error_msg"),
                            )
                        )

                collections_list.append(
                    CollectionItem(collection_id=name, documents=documents_list)
                )

            data = CollectionsListData(
                collections=collections_list, total_collections=len(collections_list)
            )

            return GenericResponse(
                status="success",
                message=f"Found {len(collections_list)} collections",
                data=data,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("", response_model=GenericResponse[CollectionCreateData])
    async def create_collection(
        collection_id: str,
    ) -> GenericResponse[CollectionCreateData]:
        """Create a new collection"""
        try:
            rag_manager = LightRagManager()
            rag = await rag_manager.create_lightrag_instance(
                collection_id=collection_id
            )
            if rag is None:
                raise HTTPException(
                    status_code=500, detail="Failed to create collection"
                )

            data = CollectionCreateData(
                collection_id=collection_id, created_at=datetime.now().isoformat()
            )

            return GenericResponse(
                status="success",
                message=f"Collection '{collection_id}' created successfully.",
                data=data,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    class CollectionBatchRequest(BaseModel):
        collection_ids: list[str]

    @router.post("/batch", response_model=GenericResponse[CollectionBatchData])
    async def get_collections_batch(request: CollectionBatchRequest):
        """批量获取指定集合信息（通过 JSON body 提交 collection_ids 列表）"""
        try:
            collection_ids = request.collection_ids
            rag_manager = LightRagManager()
            all_collections = await rag_manager.list_collections()

            # 过滤出请求的集合
            found_collections = []
            missing_collections = []

            for requested_id in collection_ids:
                if requested_id in all_collections:
                    docs_data = all_collections[requested_id]
                    documents_list = []

                    if isinstance(docs_data, dict):
                        for doc_id, doc_data in docs_data.items():
                            documents_list.append(
                                DocumentItem(
                                    doc_id=doc_id,
                                    status=doc_data.get("status", "unknown"),
                                    chunks_count=doc_data.get("chunks_count", 0),
                                    chunks_list=doc_data.get("chunks_list", []),
                                    content_summary=doc_data.get("content_summary"),
                                    content_length=doc_data.get("content_length"),
                                    created_at=doc_data.get("created_at"),
                                    updated_at=doc_data.get("updated_at"),
                                    file_path=doc_data.get("file_path"),
                                    track_id=doc_data.get("track_id"),
                                    metadata=doc_data.get("metadata"),
                                    error_msg=doc_data.get("error_msg"),
                                )
                            )

                    found_collections.append(
                        CollectionItem(
                            collection_id=requested_id, documents=documents_list
                        )
                    )
                else:
                    missing_collections.append(requested_id)

            data = CollectionBatchData(
                collections=found_collections,
                found_count=len(found_collections),
                requested_count=len(collection_ids),
                missing_collections=missing_collections,
            )

            return GenericResponse(
                status="success",
                message=f"Found {len(found_collections)} out of {len(collection_ids)} requested collections",
                data=data,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.delete("", response_model=GenericResponse[CollectionDeleteData])
    async def clear_documents(collection_id: str):
        rag = await lightrag_manager.get_rag_instance(collection_id)
        if rag is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        doc_manager = DocumentManager(
            input_dir=str(get_default_storage_dir() / "inputs"), workspace=collection_id
        )

        workspace_dir = rag.working_dir + f"/{collection_id}"
        input_dir = doc_manager.input_dir

        deleted_documents_count = 0
        workspace_cleared = False

        try:
            await lightrag_manager.clear_rag_instance(collection_id)

            # Count documents before deletion
            if input_dir.exists() and input_dir.is_dir():
                deleted_documents_count = len(list(input_dir.iterdir()))

                # Remove all files in the input directory
                for item in input_dir.iterdir():
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)

            if workspace_dir and Path(workspace_dir).exists():
                shutil.rmtree(workspace_dir)
                workspace_cleared = True

            message = (
                f"All documents in collection '{collection_id}' have been cleared."
            )

            data = CollectionDeleteData(
                collection_id=collection_id,
                deleted_documents_count=deleted_documents_count,
                workspace_cleared=workspace_cleared,
            )

            return GenericResponse(status="success", message=message, data=data)
        except HTTPException:
            # Preserve HTTPException (e.g. 404) raised by underlying calls
            raise
        except FileNotFoundError as e:
            logger.exception("File/directory not found while clearing documents: %s", e)
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.exception("Error clearing documents: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    return router
