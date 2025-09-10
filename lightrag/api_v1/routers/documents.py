import asyncio
from pathlib import Path
import shutil
from typing import Dict, List
from lightrag.api_v1.schema.document_schema import (
    ClearDocumentsResponse,
    DocStatusResponse,
    DocsStatusesResponse,
    InsertResponse,
)
from lightrag.api_v1.utils.file import pipeline_enqueue_file, sanitize_filename
from lightrag.base import DocProcessingStatus, DocStatus
from lightrag.document_manager import DocumentManager
from lightrag.lightrag import LightRAG
from lightrag.lightrag_manager import LightRagManager
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from lightrag.api_v1.utils.date import format_datetime

import logging

# module logger
logger = logging.getLogger(__name__)

from lightrag.utils import generate_track_id


def create_document_routers() -> APIRouter:
    """Factory to create documents APIRouter using provided or global logger/manager.

    If logger or manager is not provided, defaults are used.
    """
    router = APIRouter(prefix="/documents", tags=["documents"])

    lightrag_manager = LightRagManager()

    @router.get("", response_model=DocsStatusesResponse)
    async def documents(collection_id: str) -> DocsStatusesResponse:
        try:
            statuses = (
                DocStatus.PENDING,
                DocStatus.PROCESSING,
                DocStatus.PROCESSED,
                DocStatus.FAILED,
            )

            rag = await lightrag_manager.get_rag_instance(collection_id)
            logger.info(f"rag instance for collection {collection_id}: {rag}")
            if rag is None:
                logger.warning(f"Collection {collection_id} not found")
                raise HTTPException(status_code=404, detail="Collection not found")

            tasks = [rag.get_docs_by_status(status) for status in statuses]
            results: List[Dict[str, DocProcessingStatus]] = await asyncio.gather(*tasks)

            response = DocsStatusesResponse()

            for idx, result in enumerate(results):
                status = statuses[idx]
                for doc_id, doc_status in result.items():
                    if status not in response.statuses:
                        response.statuses[status] = []
                    response.statuses[status].append(
                        DocStatusResponse(
                            id=doc_id,
                            content_summary=doc_status.content_summary,
                            content_length=doc_status.content_length,
                            status=doc_status.status,
                            created_at=format_datetime(doc_status.created_at),
                            updated_at=format_datetime(doc_status.updated_at),
                            track_id=doc_status.track_id,
                            chunks_count=doc_status.chunks_count,
                            error_msg=doc_status.error_msg,
                            metadata=doc_status.metadata,
                            file_path=doc_status.file_path,
                        )
                    )
            return response
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.exception("Error in documents endpoint: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/upload", response_model=InsertResponse)
    async def upload_to_input_dir(
        collection_id: str,
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
    ):
        try:
            # Sanitize filename to prevent Path Traversal attacks
            doc_manager = DocumentManager(input_dir="./inputs", workspace=collection_id)

            rag = await lightrag_manager.create_lightrag_instance(collection_id)

            safe_filename = sanitize_filename(file.filename, doc_manager.input_dir)

            if not doc_manager.is_supported_file(safe_filename):
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type. Supported types: {doc_manager.supported_extensions}",
                )

            file_path = doc_manager.input_dir / safe_filename
            # Check if file already exists
            if file_path.exists():
                return InsertResponse(
                    status="duplicated",
                    message=f"File '{safe_filename}' already exists in the input directory.",
                    track_id="",
                )

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            track_id = generate_track_id("upload")

            # Add to background tasks and get track_id
            background_tasks.add_task(pipeline_index_file, rag, file_path, track_id)

            return InsertResponse(
                status="success",
                message=f"File '{safe_filename}' uploaded successfully. Processing will continue in background.",
                track_id=track_id,
            )

        except Exception as e:
            logger.exception("Error uploading file: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    async def pipeline_index_file(rag: LightRAG, file_path: Path, track_id: str = None):
        """Index a file with track_id

        Args:
            rag: LightRAG instance
            file_path: Path to the saved file
            track_id: Optional tracking ID
        """
        try:
            success, returned_track_id = await pipeline_enqueue_file(
                rag, file_path, track_id
            )
            if success:
                await rag.apipeline_process_enqueue_documents()

        except Exception as e:
            logger.exception("Error indexing file %s: %s", file_path.name, e)

    @router.delete("", response_model=ClearDocumentsResponse)
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

        return ClearDocumentsResponse(status="success", message=message)

    return router
