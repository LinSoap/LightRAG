import asyncio
from datetime import datetime
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
import json

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

    @router.get("/:collection_id", response_model=DocsStatusesResponse)
    async def documents(collection_id: str) -> DocsStatusesResponse:
        try:
            statuses = (
                DocStatus.PENDING,
                DocStatus.PROCESSING,
                DocStatus.PROCESSED,
                DocStatus.FAILED,
            )

            rag = await lightrag_manager.get_rag_instance(collection_id)
            if rag is None:
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
        except Exception as e:
            # logger.exception("Error in documents endpoint: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/upload/:collection_id", response_model=InsertResponse)
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

    @router.delete("/:collection_id", response_model=ClearDocumentsResponse)
    async def clear_documents(collection_id: str):
        doc_manager = DocumentManager(input_dir="./inputs", workspace=collection_id)

        input_dir = doc_manager.input_dir
        base_dir = doc_manager.workspace
        print(
            input_dir,
        )

        try:
            # Safety check: ensure input_dir is within base_dir to avoid accidental deletions
            input_resolved = input_dir.resolve()
            base_resolved = base_dir.resolve()
            if (
                base_resolved not in input_resolved.parents
                and input_resolved != base_resolved
            ):
                msg = f"Refusing to delete directory outside of base inputs dir: {input_dir}"
                logger.error(msg)
                raise HTTPException(status_code=400, detail=msg)

            if not input_dir.exists():
                logger.info("Input directory '%s' does not exist", input_dir)

            deleted_paths = []

            # Remove input_dir if it exists
            if input_dir.exists():
                await asyncio.to_thread(shutil.rmtree, str(input_dir))
                deleted_paths.append(str(input_dir))

            # Also attempt to remove base_input_dir/collection_id (same as input_dir for most cases,
            # but handle explicitly in case of different layout)
            collection_dir = base_dir / collection_id
            try:
                # Only delete if it's within base_dir and not the base_dir itself
                collection_resolved = collection_dir.resolve()
                base_resolved = base_dir.resolve()
                if (
                    collection_resolved.exists()
                    and collection_resolved != base_resolved
                    and base_resolved in collection_resolved.parents
                ):
                    # If we already deleted input_dir above and it's the same path, skip
                    if str(collection_resolved) not in deleted_paths:
                        await asyncio.to_thread(shutil.rmtree, str(collection_resolved))
                        deleted_paths.append(str(collection_resolved))
            except Exception:
                # ignore resolution errors for collection_dir and continue
                pass

            if not deleted_paths:
                message = f"No directories deleted for collection '{collection_id}'"
                logger.info(message)
                return ClearDocumentsResponse(status="not_found", message=message)

            message = f"Successfully removed directories: {', '.join(deleted_paths)}"
            logger.info(message)
            return ClearDocumentsResponse(status="success", message=message)

        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Error deleting input/workspace directory: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    return router
