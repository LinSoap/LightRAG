from pathlib import Path
import shutil
from lightrag.api.schemas.collection import (
    CreateCollectionResponse,
    DeleteCollectionResponse,
    ListCollectionsResponse,
)
from lightrag.document_manager import DocumentManager
from lightrag.lightrag_manager import LightRagManager
from fastapi import APIRouter, HTTPException
from lightrag.utils import logger


router = APIRouter(prefix="/collection", tags=["collection"])


def create_collection_routes():
    lightrag_manager = LightRagManager()

    @router.get("", response_model=ListCollectionsResponse)
    async def list_collections() -> ListCollectionsResponse:
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
                            {
                                "doc_id": doc_id,
                                "status": doc_data.get("status", "unknown"),
                                "chunks_count": doc_data.get("chunks_count", 0),
                                "chunks_list": doc_data.get("chunks_list", []),
                                "content_summary": doc_data.get("content_summary"),
                                "content_length": doc_data.get("content_length"),
                                "created_at": doc_data.get("created_at"),
                                "updated_at": doc_data.get("updated_at"),
                                "file_path": doc_data.get("file_path"),
                                "track_id": doc_data.get("track_id"),
                                "metadata": doc_data.get("metadata"),
                                "error_msg": doc_data.get("error_msg"),
                            }
                        )

                collections_list.append(
                    {"collection_id": name, "documents": documents_list}
                )

            return {"status": "success", "collections": collections_list}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("", response_model=CreateCollectionResponse)
    async def create_collection(collection_id: str) -> CreateCollectionResponse:
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
            return {
                "status": "success",
                "message": f"Collection '{collection_id}' created successfully.",
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.delete("", response_model=DeleteCollectionResponse)
    async def clear_documents(collection_id: str):
        rag = await lightrag_manager.get_rag_instance(collection_id)
        doc_manager = DocumentManager(input_dir="./inputs", workspace=collection_id)

        workspace_dir = rag.working_dir + f"/{collection_id}"
        input_dir = doc_manager.input_dir

        try:
            await lightrag_manager.clear_rag_instance(collection_id)
            if input_dir.exists() and input_dir.is_dir():
                # Remove all files in the input directory
                for item in input_dir.iterdir():
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
            if workspace_dir and Path(workspace_dir).exists():
                shutil.rmtree(workspace_dir)
                message = (
                    f"All documents in collection '{collection_id}' have been cleared."
                )
        except Exception as e:
            logger.exception("Error clearing documents: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

        return DeleteCollectionResponse(status="success", message=message)

    return router
