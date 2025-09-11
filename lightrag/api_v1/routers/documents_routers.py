import asyncio
from pathlib import Path
import shutil
import traceback
from typing import Dict, List
from lightrag.api_v1.schema.document_schema import (
    ClearDocumentsResponse,
    DeleteDocByIdResponse,
    DeleteDocRequest,
    DocStatusResponse,
    DocumentsResponse,
    InsertResponse,
    PipelineStatusResponse,
    TrackStatusResponse,
)
from lightrag.api_v1.utils.background import (
    background_delete_documents,
    pipeline_index_file,
)
from lightrag.api_v1.utils.file import sanitize_filename
from lightrag.base import DocProcessingStatus, DocStatus
from lightrag.document_manager import DocumentManager
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

    @router.get("/collections")
    async def list_collections():
        """List all existing collections based on working directory"""
        try:
            collections = await lightrag_manager.list_collections()
            return collections
        except Exception as e:
            logger.exception("Error listing collections: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    from typing import List

    @router.get("", response_model=List[DocumentsResponse])
    async def documents(collection_id: str) -> List[DocumentsResponse]:
        try:
            rag = await lightrag_manager.get_rag_instance(collection_id)

            # Use the initialized doc_status instance (not the class) and await its async get_all()
            documents_raw = await rag.doc_status.get_all()

            doc_list = []
            for doc_id, doc_data in documents_raw.items():
                # Normalize dict to match DocProcessingStatus constructor
                data = doc_data.copy() if isinstance(doc_data, dict) else {}
                data.pop("content", None)
                if "file_path" not in data:
                    data["file_path"] = "no-file-path"
                if "metadata" not in data:
                    data["metadata"] = {}
                if "error_msg" not in data:
                    data["error_msg"] = None

                try:
                    doc_status = DocProcessingStatus(**data)
                except Exception:
                    # Fallback: skip malformed entries
                    logger.exception(f"Malformed doc status for {doc_id}, skipping")
                    continue

                doc_list.append(
                    DocumentsResponse(
                        id=doc_id,
                        collection_id=collection_id,
                        status=doc_status.status,
                        chunks_count=doc_status.chunks_count,
                        chunks_list=doc_status.chunks_list or [],
                        content_summary=doc_status.content_summary,
                        content_length=doc_status.content_length,
                        created_at=format_datetime(doc_status.created_at),
                        updated_at=format_datetime(doc_status.updated_at),
                        file_path=doc_status.file_path,
                        track_id=doc_status.track_id,
                        error_msg=doc_status.error_msg,
                        metadata=doc_status.metadata,
                    )
                )
            return doc_list

        except HTTPException as e:
            raise e
        except Exception as e:
            logger.exception("Error in documents endpoint: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/chunk")
    async def get_document_chunks(
        collection_id: str, doc_id: str, limit: int = 10, offset: int = 0
    ):
        try:
            rag = await lightrag_manager.get_rag_instance(collection_id)
            if rag is None:
                logger.warning(f"Collection {collection_id} not found")
                raise HTTPException(status_code=404, detail="Collection not found")

            chunks = await rag.text_chunks.get_by_doc_id(doc_id)
            return {"doc_id": doc_id, "chunks": chunks}
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.exception("Error in get_document_chunks endpoint: %s", e)
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

    @router.get(
        "/pipeline_status",
        response_model=PipelineStatusResponse,
    )
    async def get_pipeline_status(collection_id: str) -> PipelineStatusResponse:
        """
        Get the current status of the document indexing pipeline.

        This endpoint returns information about the current state of the document processing pipeline,
        including the processing status, progress information, and history messages.

        Returns:
            PipelineStatusResponse: A response object containing:
                - autoscanned (bool): Whether auto-scan has started
                - busy (bool): Whether the pipeline is currently busy
                - job_name (str): Current job name (e.g., indexing files/indexing texts)
                - job_start (str, optional): Job start time as ISO format string
                - docs (int): Total number of documents to be indexed
                - batchs (int): Number of batches for processing documents
                - cur_batch (int): Current processing batch
                - request_pending (bool): Flag for pending request for processing
                - latest_message (str): Latest message from pipeline processing
                - history_messages (List[str], optional): List of history messages (limited to latest 1000 entries,
                  with truncation message if more than 1000 messages exist)

        Raises:
            HTTPException: If an error occurs while retrieving pipeline status (500)
        """
        try:
            from lightrag.kg.shared_storage import (
                get_namespace_data,
                get_all_update_flags_status,
            )

            await lightrag_manager.get_rag_instance(collection_id)

            pipeline_status = await get_namespace_data("pipeline_status")

            # Get update flags status for all namespaces
            update_status = await get_all_update_flags_status()

            # Convert MutableBoolean objects to regular boolean values
            processed_update_status = {}
            for namespace, flags in update_status.items():
                processed_flags = []
                for flag in flags:
                    # Handle both multiprocess and single process cases
                    if hasattr(flag, "value"):
                        processed_flags.append(bool(flag.value))
                    else:
                        processed_flags.append(bool(flag))
                processed_update_status[namespace] = processed_flags

            # Convert to regular dict if it's a Manager.dict
            status_dict = dict(pipeline_status)

            # Add processed update_status to the status dictionary
            status_dict["update_status"] = processed_update_status

            # Convert history_messages to a regular list if it's a Manager.list
            # and limit to latest 1000 entries with truncation message if needed
            if "history_messages" in status_dict:
                history_list = list(status_dict["history_messages"])
                total_count = len(history_list)

                if total_count > 1000:
                    # Calculate truncated message count
                    truncated_count = total_count - 1000

                    # Take only the latest 1000 messages
                    latest_messages = history_list[-1000:]

                    # Add truncation message at the beginning
                    truncation_message = (
                        f"[Truncated history messages: {truncated_count}/{total_count}]"
                    )
                    status_dict["history_messages"] = [
                        truncation_message
                    ] + latest_messages
                else:
                    # No truncation needed, return all messages
                    status_dict["history_messages"] = history_list

            # Ensure job_start is properly formatted as a string with timezone information
            if "job_start" in status_dict and status_dict["job_start"]:
                # Use format_datetime to ensure consistent formatting
                status_dict["job_start"] = format_datetime(status_dict["job_start"])

            return PipelineStatusResponse(**status_dict)
        except Exception as e:
            logger.error(f"Error getting pipeline status: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=str(e))

    @router.get(
        "/track_status",
        response_model=TrackStatusResponse,
    )
    async def get_track_status(
        collection_id: str, track_id: str
    ) -> TrackStatusResponse:
        """
        Get the processing status of documents by tracking ID.

        This endpoint retrieves all documents associated with a specific tracking ID,
        allowing users to monitor the processing progress of their uploaded files or inserted texts.

        Args:
            track_id (str): The tracking ID returned from upload, text, or texts endpoints

        Returns:
            TrackStatusResponse: A response object containing:
                - track_id: The tracking ID
                - documents: List of documents associated with this track_id
                - total_count: Total number of documents for this track_id

        Raises:
            HTTPException: If track_id is invalid (400) or an error occurs (500).
        """
        try:
            # Validate track_id
            if not track_id or not track_id.strip():
                raise HTTPException(status_code=400, detail="Track ID cannot be empty")

            track_id = track_id.strip()

            rag = await lightrag_manager.get_rag_instance(collection_id)

            # Get documents by track_id
            docs_by_track_id = await rag.aget_docs_by_track_id(track_id)

            # Convert to response format
            documents = []
            status_summary = {}

            for doc_id, doc_status in docs_by_track_id.items():
                documents.append(
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

                # Build status summary
                # Handle both DocStatus enum and string cases for robust deserialization
                status_key = str(doc_status.status)
                status_summary[status_key] = status_summary.get(status_key, 0) + 1

            return TrackStatusResponse(
                track_id=track_id,
                documents=documents,
                total_count=len(documents),
                status_summary=status_summary,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting track status for {track_id}: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=str(e))

    @router.delete(
        "/delete_document",
        response_model=DeleteDocByIdResponse,
    )
    async def delete_document(
        collection_id: str,
        delete_request: DeleteDocRequest,
        background_tasks: BackgroundTasks,
    ) -> DeleteDocByIdResponse:
        """
        Delete documents and all their associated data by their IDs using background processing.

        Deletes specific documents and all their associated data, including their status,
        text chunks, vector embeddings, and any related graph data.
        The deletion process runs in the background to avoid blocking the client connection.
        It is disabled when llm cache for entity extraction is disabled.

        This operation is irreversible and will interact with the pipeline status.

        Args:
            delete_request (DeleteDocRequest): The request containing the document IDs and delete_file options.
            background_tasks: FastAPI BackgroundTasks for async processing

        Returns:
            DeleteDocByIdResponse: The result of the deletion operation.
                - status="deletion_started": The document deletion has been initiated in the background.
                - status="busy": The pipeline is busy with another operation.
                - status="not_allowed": Operation not allowed when LLM cache for entity extraction is disabled.

        Raises:
            HTTPException:
              - 500: If an unexpected internal error occurs during initialization.
        """
        doc_ids = delete_request.doc_ids
        rag = await lightrag_manager.get_rag_instance(collection_id)
        doc_manager = DocumentManager(input_dir="./inputs", workspace=collection_id)

        # The rag object is initialized from the server startup args,
        # so we can access its properties here.
        if not rag.enable_llm_cache_for_entity_extract:
            return DeleteDocByIdResponse(
                status="not_allowed",
                message="Operation not allowed when LLM cache for entity extraction is disabled.",
                doc_id=", ".join(delete_request.doc_ids),
            )

        try:
            from lightrag.kg.shared_storage import get_namespace_data

            pipeline_status = await get_namespace_data("pipeline_status")

            # Check if pipeline is busy
            if pipeline_status.get("busy", False):
                return DeleteDocByIdResponse(
                    status="busy",
                    message="Cannot delete documents while pipeline is busy",
                    doc_id=", ".join(doc_ids),
                )

            # Add deletion task to background tasks
            background_tasks.add_task(
                background_delete_documents,
                rag,
                doc_manager,
                doc_ids,
                delete_request.delete_file,
            )

            return DeleteDocByIdResponse(
                status="deletion_started",
                message=f"Document deletion for {len(doc_ids)} documents has been initiated. Processing will continue in background.",
                doc_id=", ".join(doc_ids),
            )

        except Exception as e:
            error_msg = f"Error initiating document deletion for {delete_request.doc_ids}: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=error_msg)

    return router
